from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence

from phase5_contracts import (
    BreakoutParameters,
    PatternEvent,
    PinBarParameters,
    TriggerAttribution,
    deduplicate_pattern_events,
)

PATTERN_RULE_VERSION = "phase_5_frozen_v1"
EPSILON = 1e-9


@dataclass(frozen=True, slots=True)
class CanonicalCandle:
    index: int
    timestamp_utc: str
    open_time_utc: str
    close_time_utc: str
    open: float
    high: float
    low: float
    close: float

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def range_size(self) -> float:
        return self.high - self.low

    @property
    def body_mid(self) -> float:
        return (self.open + self.close) / 2.0

    @property
    def direction(self) -> int:
        if self.close > self.open:
            return 1
        if self.close < self.open:
            return -1
        return 0

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)


def _is_valid_candle(candle: CanonicalCandle | None) -> bool:
    if candle is None:
        return False
    try:
        o = float(candle.open)
        h = float(candle.high)
        l = float(candle.low)
        c = float(candle.close)
    except (TypeError, ValueError):
        return False
    if not all(math.isfinite(v) for v in (o, h, l, c)):
        return False
    if h < l:
        return False
    if h < max(o, c):
        return False
    if l > min(o, c):
        return False
    return True


def _make_event(
    *,
    pattern_type: str,
    direction: int,
    detection_timestamp: str,
    candle_start_timestamp: str,
    candle_end_timestamp: str,
    candle_indices: Sequence[int],
    source_references: Sequence[str],
    trigger_index: int | None,
    trigger_name: str,
    quality: str | float | None = None,
    strength: str | None = None,
) -> PatternEvent:
    trigger = TriggerAttribution(
        pattern_type=pattern_type,
        direction=direction,
        trigger_candle=trigger_name,
        candle_index=trigger_index,
        timestamp_utc=detection_timestamp,
    )
    return PatternEvent(
        pattern_type=pattern_type,
        direction=direction,
        detection_timestamp=detection_timestamp,
        candle_start_timestamp=candle_start_timestamp,
        candle_end_timestamp=candle_end_timestamp,
        candle_indices=tuple(int(i) for i in candle_indices),
        source_candle_references=tuple(str(ref) for ref in source_references),
        rule_version=PATTERN_RULE_VERSION,
        quality=quality,
        strength=strength,
        trigger_attribution=trigger,
    )


def _sort_events(events: Iterable[PatternEvent]) -> list[PatternEvent]:
    return sorted(
        list(events),
        key=lambda e: (
            e.detection_timestamp,
            min(e.candle_indices) if e.candle_indices else -1,
            e.pattern_type,
            e.direction,
            e.event_identity,
        ),
    )


def _trigger_name_for(pattern_type: str) -> str:
    return {
        "ENGULFING": "second_candle",
        "PIN_BAR": "pin_bar_candle",
        "THREE_BAR_CONTINUATION": "third_candle",
        "THREE_BAR_REVERSAL": "third_candle",
        "BREAKOUT": "breakout_confirmation_candle_b",
        "SHRINKING": "opposite_direction_reversal_candle",
    }.get(pattern_type, "trigger_candle")


def detect_engulfing_events(candles: Sequence[CanonicalCandle | None]) -> list[PatternEvent]:
    events: list[PatternEvent] = []
    for i in range(len(candles) - 1):
        first = candles[i]
        second = candles[i + 1]
        if not _is_valid_candle(first) or not _is_valid_candle(second):
            continue
        if first.direction == 0 or second.direction == 0:
            continue
        if first.direction == second.direction:
            continue
        if first.body_size <= 0 or second.body_size <= 0:
            continue
        if second.body_size <= first.body_size:
            continue
        first_low = min(first.open, first.close)
        first_high = max(first.open, first.close)
        second_low = min(second.open, second.close)
        second_high = max(second.open, second.close)
        if not (second_low <= first_low and second_high >= first_high):
            continue
        events.append(
            _make_event(
                pattern_type="ENGULFING",
                direction=second.direction,
                detection_timestamp=second.close_time_utc or second.timestamp_utc,
                candle_start_timestamp=first.timestamp_utc,
                candle_end_timestamp=second.timestamp_utc,
                candle_indices=(first.index, second.index),
                source_references=(f"candle_{first.index}", f"candle_{second.index}"),
                trigger_index=second.index,
                trigger_name=_trigger_name_for("ENGULFING"),
            )
        )
    return _sort_events(events)


def _pin_bar_matches(candle: CanonicalCandle, params: PinBarParameters) -> bool:
    if candle.body_size <= 0:
        return False
    if candle.range_size <= 0:
        return False
    upper_wick = candle.upper_wick
    lower_wick = candle.lower_wick
    dominant_wick = max(upper_wick, lower_wick)
    non_dominant_wick = min(upper_wick, lower_wick)
    if dominant_wick <= non_dominant_wick:
        return False
    if candle.body_size / candle.range_size > params.body_max_ratio:
        return False
    if dominant_wick / max(candle.body_size, EPSILON) < params.wick_to_body_min_ratio:
        return False
    if non_dominant_wick / candle.range_size > params.non_dominant_wick_max_ratio:
        return False
    body_mid = candle.body_mid
    range_mid = (candle.high + candle.low) / 2.0
    if candle.direction == 1:
        return body_mid >= range_mid
    if candle.direction == -1:
        return body_mid <= range_mid
    return False


def detect_pin_bar_events(candles: Sequence[CanonicalCandle | None], params: PinBarParameters | None = None) -> list[PatternEvent]:
    params = params or PinBarParameters(0.35, 1.5, 0.45)
    events: list[PatternEvent] = []
    for candle in candles:
        if not _is_valid_candle(candle):
            continue
        if candle.direction == 0:
            continue
        if not _pin_bar_matches(candle, params):
            continue
        events.append(
            _make_event(
                pattern_type="PIN_BAR",
                direction=candle.direction,
                detection_timestamp=candle.close_time_utc or candle.timestamp_utc,
                candle_start_timestamp=candle.timestamp_utc,
                candle_end_timestamp=candle.timestamp_utc,
                candle_indices=(candle.index,),
                source_references=(f"candle_{candle.index}",),
                trigger_index=candle.index,
                trigger_name=_trigger_name_for("PIN_BAR"),
            )
        )
    return _sort_events(events)


def detect_three_bar_continuation_events(candles: Sequence[CanonicalCandle | None]) -> list[PatternEvent]:
    events: list[PatternEvent] = []
    for i in range(len(candles) - 2):
        c1, c2, c3 = candles[i], candles[i + 1], candles[i + 2]
        if not all(_is_valid_candle(c) for c in (c1, c2, c3)):
            continue
        if c1.direction == 0 or c2.direction == 0 or c3.direction == 0:
            continue
        if c1.direction == c2.direction:
            continue
        if c1.body_size <= 0 or c2.body_size <= 0:
            continue
        if c2.body_size > 0.5 * c1.body_size:
            continue
        if c3.direction != c1.direction:
            continue
        if c1.direction == 1 and not (c3.close > c2.close):
            continue
        if c1.direction == -1 and not (c3.close < c2.close):
            continue
        events.append(
            _make_event(
                pattern_type="THREE_BAR_CONTINUATION",
                direction=c1.direction,
                detection_timestamp=c3.close_time_utc or c3.timestamp_utc,
                candle_start_timestamp=c1.timestamp_utc,
                candle_end_timestamp=c3.timestamp_utc,
                candle_indices=(c1.index, c2.index, c3.index),
                source_references=(f"candle_{c1.index}", f"candle_{c2.index}", f"candle_{c3.index}"),
                trigger_index=c3.index,
                trigger_name=_trigger_name_for("THREE_BAR_CONTINUATION"),
                quality="large",
            )
        )
    return _sort_events(events)


def detect_three_bar_reversal_events(candles: Sequence[CanonicalCandle | None]) -> list[PatternEvent]:
    events: list[PatternEvent] = []
    for i in range(len(candles) - 2):
        c1, c2, c3 = candles[i], candles[i + 1], candles[i + 2]
        if not all(_is_valid_candle(c) for c in (c1, c2, c3)):
            continue
        if c1.direction == 0 or c2.direction == 0 or c3.direction == 0:
            continue
        if c1.direction != c2.direction:
            continue
        if c2.body_size >= c1.body_size:
            continue
        if c3.direction == c1.direction:
            continue
        strength = "STRONG" if c3.body_size >= c1.body_size else "WEAK"
        direction = -c1.direction
        events.append(
            _make_event(
                pattern_type="THREE_BAR_REVERSAL",
                direction=direction,
                detection_timestamp=c3.close_time_utc or c3.timestamp_utc,
                candle_start_timestamp=c1.timestamp_utc,
                candle_end_timestamp=c3.timestamp_utc,
                candle_indices=(c1.index, c2.index, c3.index),
                source_references=(f"candle_{c1.index}", f"candle_{c2.index}", f"candle_{c3.index}"),
                trigger_index=c3.index,
                trigger_name=_trigger_name_for("THREE_BAR_REVERSAL"),
                strength=strength,
            )
        )
    return _sort_events(events)


def _maximal_valid_prefix_before(candles: Sequence[CanonicalCandle | None], end_index: int) -> tuple[int, list[CanonicalCandle]]:
    start = end_index
    while start > 0 and _is_valid_candle(candles[start - 1]):
        start -= 1
    window = [c for c in candles[start:end_index] if _is_valid_candle(c)]
    return start, window


def detect_breakout_events(candles: Sequence[CanonicalCandle | None], threshold: float | BreakoutParameters | None = None) -> list[PatternEvent]:
    threshold_value = threshold.normalized_consolidation_threshold if isinstance(threshold, BreakoutParameters) else float(threshold or 0.10)
    events: list[PatternEvent] = []
    for i in range(1, len(candles)):
        breakout = candles[i]
        if not _is_valid_candle(breakout):
            continue
        start, window = _maximal_valid_prefix_before(candles, i)
        if len(window) < 3:
            continue
        consolidation = window
        if any(not _is_valid_candle(c) for c in consolidation):
            continue
        upper = max(c.high for c in consolidation)
        lower = min(c.low for c in consolidation)
        norm = (upper - lower) / abs(median(c.close for c in consolidation))
        if not (0.0 < norm < threshold_value):
            continue
        if breakout.direction == 1 and breakout.close > upper:
            direction = 1
        elif breakout.direction == -1 and breakout.close < lower:
            direction = -1
        else:
            continue
        if events and events[-1].candle_start_timestamp == consolidation[0].timestamp_utc:
            continue
        events.append(
            _make_event(
                pattern_type="BREAKOUT",
                direction=direction,
                detection_timestamp=breakout.close_time_utc or breakout.timestamp_utc,
                candle_start_timestamp=consolidation[0].timestamp_utc,
                candle_end_timestamp=breakout.timestamp_utc,
                candle_indices=tuple(c.index for c in consolidation) + (breakout.index,),
                source_references=tuple(f"candle_{c.index}" for c in consolidation) + (f"candle_{breakout.index}",),
                trigger_index=breakout.index,
                trigger_name=_trigger_name_for("BREAKOUT"),
            )
        )
    return _sort_events(events)


def detect_shrinking_events(candles: Sequence[CanonicalCandle | None]) -> list[PatternEvent]:
    events: list[PatternEvent] = []
    for i in range(2, len(candles)):
        reversal = candles[i]
        if not _is_valid_candle(reversal):
            continue
        previous = candles[i - 1]
        if not _is_valid_candle(previous):
            continue
        if reversal.direction == 0 or previous.direction == 0:
            continue
        if previous.direction == reversal.direction:
            continue
        seq = []
        for j in range(i - 1, -1, -1):
            cand = candles[j]
            if not _is_valid_candle(cand):
                break
            if cand.direction != previous.direction:
                break
            seq.append(cand)
        seq = list(reversed(seq))
        if len(seq) < 3:
            continue
        bodies = [c.body_size for c in seq]
        if any(current >= previous_body for previous_body, current in zip(bodies[:-1], bodies[1:])):
            continue
        events.append(
            _make_event(
                pattern_type="SHRINKING",
                direction=previous.direction,
                detection_timestamp=reversal.close_time_utc or reversal.timestamp_utc,
                candle_start_timestamp=seq[0].timestamp_utc,
                candle_end_timestamp=reversal.timestamp_utc,
                candle_indices=tuple(c.index for c in seq) + (reversal.index,),
                source_references=tuple(f"candle_{c.index}" for c in seq) + (f"candle_{reversal.index}",),
                trigger_index=reversal.index,
                trigger_name=_trigger_name_for("SHRINKING"),
            )
        )
    return _sort_events(events)


class PatternEventEngine:
    def __init__(self, *, pin_bar_parameters: PinBarParameters | None = None, breakout_threshold: float | BreakoutParameters | None = None):
        self.pin_bar_parameters = pin_bar_parameters or PinBarParameters(0.35, 1.5, 0.45)
        self.breakout_threshold = breakout_threshold or 0.10

    def detect(self, candles: Sequence[CanonicalCandle | None]) -> list[PatternEvent]:
        events: list[PatternEvent] = []
        events.extend(detect_engulfing_events(candles))
        events.extend(detect_pin_bar_events(candles, self.pin_bar_parameters))
        events.extend(detect_three_bar_continuation_events(candles))
        events.extend(detect_three_bar_reversal_events(candles))
        events.extend(detect_breakout_events(candles, self.breakout_threshold))
        events.extend(detect_shrinking_events(candles))
        deduped = deduplicate_pattern_events(events)
        return _sort_events(deduped)


__all__ = [
    "CanonicalCandle",
    "PatternEventEngine",
    "detect_engulfing_events",
    "detect_pin_bar_events",
    "detect_three_bar_continuation_events",
    "detect_three_bar_reversal_events",
    "detect_breakout_events",
    "detect_shrinking_events",
]
