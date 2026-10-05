from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Any


TRIGGER_CANDLE_BY_PATTERN = {
    "ENGULFING": "second_candle",
    "PIN_BAR": "pin_bar_candle",
    "THREE_BAR_CONTINUATION": "third_candle",
    "THREE_BAR_REVERSAL": "third_candle",
    "BREAKOUT": "breakout_confirmation_candle_b",
    "SHRINKING": "opposite_direction_reversal_candle",
}

ALLOWED_DIRECTIONS = {1, -1}


def _normalize_direction(value: int | str) -> int:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"bullish", "long", "+1", "1"}:
            return 1
        if normalized in {"bearish", "short", "-1", "-", "-1.0"}:
            return -1
        raise ValueError(f"unsupported direction value: {value!r}")
    if value in ALLOWED_DIRECTIONS:
        return int(value)
    raise ValueError(f"direction must be +1 or -1; got {value!r}")


@dataclass(frozen=True, slots=True)
class TriggerAttribution:
    pattern_type: str
    direction: int
    trigger_candle: str
    candle_index: int | None = None
    timestamp_utc: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_type", str(self.pattern_type).upper())
        object.__setattr__(self, "direction", _normalize_direction(self.direction))
        if self.trigger_candle not in set(TRIGGER_CANDLE_BY_PATTERN.values()):
            raise ValueError(f"unsupported trigger_candle: {self.trigger_candle!r}")

    @classmethod
    def from_pattern(cls, pattern_type: str, direction: int, *, candle_index: int | None = None, timestamp_utc: str | None = None) -> "TriggerAttribution":
        normalized_type = str(pattern_type).upper()
        if normalized_type not in TRIGGER_CANDLE_BY_PATTERN:
            raise ValueError(f"unsupported pattern_type: {pattern_type!r}")
        return cls(
            pattern_type=normalized_type,
            direction=direction,
            trigger_candle=TRIGGER_CANDLE_BY_PATTERN[normalized_type],
            candle_index=candle_index,
            timestamp_utc=timestamp_utc,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "direction": self.direction,
            "trigger_candle": self.trigger_candle,
            "candle_index": self.candle_index,
            "timestamp_utc": self.timestamp_utc,
        }


@dataclass(frozen=True, slots=True)
class PatternEvent:
    pattern_type: str
    direction: int
    detection_timestamp: str
    candle_start_timestamp: str
    candle_end_timestamp: str
    candle_indices: tuple[int, ...]
    source_candle_references: tuple[str, ...] = ()
    rule_version: str = "phase_5_frozen_v1"
    strength: float | None = None
    quality: float | None = None
    trigger_attribution: TriggerAttribution | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_type", str(self.pattern_type).upper())
        object.__setattr__(self, "direction", _normalize_direction(self.direction))
        object.__setattr__(self, "candle_indices", tuple(int(index) for index in self.candle_indices))
        object.__setattr__(self, "source_candle_references", tuple(str(ref) for ref in self.source_candle_references))
        if self.trigger_attribution is None:
            object.__setattr__(
                self,
                "trigger_attribution",
                TriggerAttribution.from_pattern(
                    self.pattern_type,
                    self.direction,
                    candle_index=self.candle_indices[0] if self.candle_indices else None,
                    timestamp_utc=self.detection_timestamp,
                ),
            )

    @property
    def event_identity(self) -> tuple[str, int, str, str]:
        return (self.pattern_type, self.direction, self.candle_start_timestamp, self.candle_end_timestamp)

    @property
    def pattern_id(self) -> str:
        return "|".join(
            [
                self.pattern_type,
                str(self.direction),
                self.candle_start_timestamp,
                self.candle_end_timestamp,
            ]
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "direction": self.direction,
            "detection_timestamp": self.detection_timestamp,
            "candle_start_timestamp": self.candle_start_timestamp,
            "candle_end_timestamp": self.candle_end_timestamp,
            "candle_indices": list(self.candle_indices),
            "source_candle_references": list(self.source_candle_references),
            "rule_version": self.rule_version,
            "strength": self.strength,
            "quality": self.quality,
            "trigger_attribution": self.trigger_attribution.as_dict() if self.trigger_attribution is not None else None,
        }


def deduplicate_pattern_events(events: Iterable[PatternEvent]) -> list[PatternEvent]:
    seen: set[tuple[str, int, str, str]] = set()
    ordered: list[PatternEvent] = []
    for event in events:
        key = event.event_identity
        if key in seen:
            continue
        seen.add(key)
        ordered.append(event)
    return ordered


@dataclass(frozen=True, slots=True)
class PinBarParameters:
    body_max_ratio: float
    wick_to_body_min_ratio: float
    non_dominant_wick_max_ratio: float

    def as_grid_tuple(self) -> tuple[float, float, float]:
        return (
            float(self.body_max_ratio),
            float(self.wick_to_body_min_ratio),
            float(self.non_dominant_wick_max_ratio),
        )


@dataclass(frozen=True, slots=True)
class BreakoutParameters:
    normalized_consolidation_threshold: float

    def as_grid_tuple(self) -> tuple[float]:
        return (float(self.normalized_consolidation_threshold),)


@dataclass(frozen=True, slots=True)
class CandidateParameters:
    pattern_type: str
    direction: int
    pin_bar: PinBarParameters | None = None
    breakout: BreakoutParameters | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_type", str(self.pattern_type).upper())
        object.__setattr__(self, "direction", _normalize_direction(self.direction))
        if self.pattern_type == "PIN_BAR" and self.pin_bar is None:
            raise ValueError("PIN_BAR candidates require pin_bar parameters")
        if self.pattern_type == "BREAKOUT" and self.breakout is None:
            raise ValueError("BREAKOUT candidates require breakout parameters")

    @property
    def grid_tuple(self) -> tuple[float, ...]:
        if self.pattern_type == "PIN_BAR":
            if self.pin_bar is None:
                raise ValueError("pin_bar is required")
            return self.pin_bar.as_grid_tuple()
        if self.pattern_type == "BREAKOUT":
            if self.breakout is None:
                raise ValueError("breakout is required")
            return self.breakout.as_grid_tuple()
        raise ValueError(f"unsupported pattern_type for candidate parameters: {self.pattern_type!r}")

    @property
    def identity_key(self) -> tuple[str, int, tuple[float, ...]]:
        return (self.pattern_type, self.direction, self.grid_tuple)


@dataclass(frozen=True, slots=True)
class CandidateIndex:
    pattern_type: str
    direction: int
    grid_position: tuple[float, ...]
    ordinal: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_type", str(self.pattern_type).upper())
        object.__setattr__(self, "direction", _normalize_direction(self.direction))
        object.__setattr__(self, "grid_position", tuple(float(value) for value in self.grid_position))

    @classmethod
    def from_parameters(cls, parameters: CandidateParameters, *, ordinal: int | None = None) -> "CandidateIndex":
        return cls(
            pattern_type=parameters.pattern_type,
            direction=parameters.direction,
            grid_position=parameters.grid_tuple,
            ordinal=ordinal,
        )

    @property
    def identity_key(self) -> tuple[str, int, tuple[float, ...]]:
        return (self.pattern_type, self.direction, self.grid_position)

    @property
    def index_key(self) -> tuple[str, int, tuple[float, ...], int | None]:
        return (self.pattern_type, self.direction, self.grid_position, self.ordinal)

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_type": self.pattern_type,
            "direction": self.direction,
            "grid_position": list(self.grid_position),
            "ordinal": self.ordinal,
            "identity_key": list(self.identity_key),
            "index_key": list(self.index_key),
        }


__all__ = [
    "ALLOWED_DIRECTIONS",
    "TRIGGER_CANDLE_BY_PATTERN",
    "TriggerAttribution",
    "PatternEvent",
    "deduplicate_pattern_events",
    "PinBarParameters",
    "BreakoutParameters",
    "CandidateParameters",
    "CandidateIndex",
]
