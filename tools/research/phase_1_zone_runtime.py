from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

VALID_SIDES = {"HIGH", "LOW"}


def median(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("median requires at least one value")
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def select_recent_gaps(gaps: Sequence[float], *, w: int = 5) -> list[float]:
    if not gaps:
        return []
    if len(gaps) >= w:
        return list(gaps[-w:])
    return list(gaps)


def compute_tolerance(gaps: Sequence[float], *, w: int = 5, min_history: int = 1) -> float | None:
    if len(gaps) < min_history:
        return None
    selected = select_recent_gaps(gaps, w=w)
    return median(selected)


@dataclass(frozen=True)
class Phase1Zone:
    side: str
    member_prices: tuple[float, ...]
    center: float
    tolerance: float
    bootstrap_gap: float | None = None
    created_index: int | None = None
    note: str = "Valid Zone created under the frozen Phase 1 membership rule."

    def contains_price(self, incoming_swing_price: float, *, current_tolerance: float | None = None) -> bool:
        effective_tolerance = self.tolerance if current_tolerance is None else current_tolerance
        return abs(float(incoming_swing_price) - float(self.center)) <= float(effective_tolerance)


@dataclass
class Phase1ReplayState:
    w: int = 5
    min_history: int = 1
    history_by_side: dict[str, list[float]] = field(default_factory=lambda: {"HIGH": [], "LOW": []})
    pending_seed_by_side: dict[str, float | None] = field(default_factory=lambda: {"HIGH": None, "LOW": None})
    zone_by_side: dict[str, Phase1Zone | None] = field(default_factory=lambda: {"HIGH": None, "LOW": None})
    events: list[dict[str, Any]] = field(default_factory=list)

    def _normalize_side(self, side: str) -> str:
        side_name = str(side).upper()
        if side_name not in VALID_SIDES:
            raise ValueError(f"Unsupported side '{side}'. Expected HIGH or LOW.")
        return side_name

    def compute_tolerance(self, side: str) -> float | None:
        side_name = self._normalize_side(side)
        return compute_tolerance(self.history_by_side[side_name], w=self.w, min_history=self.min_history)

    def record_gap(self, side: str, gap: float) -> float:
        side_name = self._normalize_side(side)
        normalized_gap = float(gap)
        self.history_by_side[side_name].append(normalized_gap)
        return normalized_gap

    def process_eligible_swing(
        self,
        side: str,
        price: float,
        *,
        observed_index: int | None = None,
        confirmed_index: int | None = None,
        eligible_index: int | None = None,
        is_confirmed: bool = True,
        is_eligible: bool = True,
    ) -> dict[str, Any]:
        side_name = self._normalize_side(side)
        normalized_price = float(price)
        record = {
            "kind": "IGNORED",
            "side": side_name,
            "price": normalized_price,
            "eligible": False,
            "confirmed": bool(is_confirmed),
            "observed_index": observed_index,
            "confirmed_index": confirmed_index,
            "eligible_index": eligible_index,
        }

        if not is_confirmed or not is_eligible:
            self.events.append(record)
            return record

        current_zone = self.zone_by_side[side_name]
        if current_zone is None:
            current_seed = self.pending_seed_by_side[side_name]
            if current_seed is None:
                self.pending_seed_by_side[side_name] = normalized_price
                record = {
                    "kind": "SEED",
                    "side": side_name,
                    "price": normalized_price,
                    "eligible": True,
                    "confirmed": True,
                    "observed_index": observed_index,
                    "confirmed_index": confirmed_index,
                    "eligible_index": eligible_index,
                    "reason": "first_same_direction_seed",
                }
                self.events.append(record)
                return record

            tolerance = self.compute_tolerance(side_name)
            if tolerance is None:
                self.pending_seed_by_side[side_name] = normalized_price
                record = {
                    "kind": "SEED",
                    "side": side_name,
                    "price": normalized_price,
                    "eligible": True,
                    "confirmed": True,
                    "observed_index": observed_index,
                    "confirmed_index": confirmed_index,
                    "eligible_index": eligible_index,
                    "reason": "no_tolerance_available",
                }
                self.events.append(record)
                return record

            member_prices = (float(current_seed), normalized_price)
            center = median(member_prices)
            if abs(normalized_price - center) <= tolerance:
                zone = Phase1Zone(
                    side=side_name,
                    member_prices=member_prices,
                    center=center,
                    tolerance=tolerance,
                    bootstrap_gap=abs(normalized_price - float(current_seed)),
                    created_index=eligible_index,
                    note="Valid Zone created under the frozen Phase 1 rule; bootstrap gap is temporary and excluded from normal gap history.",
                )
                self.zone_by_side[side_name] = zone
                self.pending_seed_by_side[side_name] = None
                record = {
                    "kind": "ZONE_CREATED",
                    "side": side_name,
                    "price": normalized_price,
                    "eligible": True,
                    "confirmed": True,
                    "observed_index": observed_index,
                    "confirmed_index": confirmed_index,
                    "eligible_index": eligible_index,
                    "zone": zone,
                    "bootstrap_gap": zone.bootstrap_gap,
                    "tolerance": tolerance,
                    "reason": "second_same_direction_member_qualified",
                }
                self.events.append(record)
                return record

            self.pending_seed_by_side[side_name] = normalized_price
            record = {
                "kind": "SEED",
                "side": side_name,
                "price": normalized_price,
                "eligible": True,
                "confirmed": True,
                "observed_index": observed_index,
                "confirmed_index": confirmed_index,
                "eligible_index": eligible_index,
                "reason": "second_swing_not_qualified",
            }
            self.events.append(record)
            return record

        tolerance = self.compute_tolerance(side_name)
        if tolerance is None:
            record = {
                "kind": "NO_MEMBERSHIP",
                "side": side_name,
                "price": normalized_price,
                "eligible": True,
                "confirmed": True,
                "observed_index": observed_index,
                "confirmed_index": confirmed_index,
                "eligible_index": eligible_index,
                "zone": current_zone,
                "reason": "no_tolerance_available",
            }
            self.events.append(record)
            return record

        is_member = current_zone.contains_price(normalized_price, current_tolerance=tolerance)
        record = {
            "kind": "MEMBER" if is_member else "NON_MEMBER",
            "side": side_name,
            "price": normalized_price,
            "eligible": True,
            "confirmed": True,
            "observed_index": observed_index,
            "confirmed_index": confirmed_index,
            "eligible_index": eligible_index,
            "zone": current_zone,
            "tolerance": tolerance,
            "is_member": is_member,
        }
        self.events.append(record)
        return record

    def replay_events(self, events: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        outputs: list[dict[str, Any]] = []
        for event in events:
            output = self.process_eligible_swing(
                event["side"],
                event["price"],
                observed_index=event.get("observed_index"),
                confirmed_index=event.get("confirmed_index"),
                eligible_index=event.get("eligible_index"),
                is_confirmed=event.get("is_confirmed", True),
                is_eligible=event.get("is_eligible", True),
            )
            outputs.append(output)
        return outputs


__all__ = [
    "VALID_SIDES",
    "Phase1ReplayState",
    "Phase1Zone",
    "compute_tolerance",
    "median",
    "select_recent_gaps",
]
