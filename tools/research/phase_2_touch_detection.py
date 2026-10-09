from __future__ import annotations

"""Phase 2 helper for the narrow, human-approved bootstrap and post-Zone touch semantics.

This module intentionally covers only the repository-approved Phase 2 boundary:
- first valid Zone creation from seed + first subsequent same-direction swing
- temporary bootstrap gap T_boot for that single formation event
- post-Zone touch classification using the frozen Phase 1 membership predicate

There is no broader lifecycle, repeated-touch, or bar-based touch logic here.
"""

from dataclasses import dataclass
from typing import Any

from tools.research.phase_1_zone_runtime import Phase1Zone


@dataclass(frozen=True)
class Phase2Zone:
    seed_price: float
    member_prices: tuple[float, float]
    center: float
    bootstrap_gap: float
    current_swing_excluded_from_history: bool = True
    note: str = (
        "Approved Phase 2 bootstrap formation semantics: the first post-seed swing creates the first valid Zone; "
        "bootstrap gap is temporary and excluded from normal gap history."
    )


def _median(values: tuple[float, float]) -> float:
    return (values[0] + values[1]) / 2.0


def _frozen_membership_predicate(current_zone_center: float, incoming_swing_price: float, current_tolerance: float) -> bool:
    """Exact frozen Phase 1 membership predicate approved for a valid Zone.

This delegates to the authoritative Phase 1 runtime object so the Phase 2 helper
uses the same causal membership behavior rather than a duplicated copy.
    """
    if incoming_swing_price is None:
        return False
    runtime_zone = Phase1Zone(
        side="HIGH",
        member_prices=(float(current_zone_center), float(current_zone_center)),
        center=float(current_zone_center),
        tolerance=float(current_tolerance),
    )
    return runtime_zone.contains_price(float(incoming_swing_price))


def create_first_zone(seed_price: float, current_swing_price: float) -> Phase2Zone:
    seed = float(seed_price)
    swing = float(current_swing_price)
    return Phase2Zone(
        seed_price=seed,
        member_prices=(seed, swing),
        center=_median((seed, swing)),
        bootstrap_gap=abs(swing - seed),
        current_swing_excluded_from_history=True,
        note=(
            "Bootstrap formation event: the first post-seed swing becomes the second member and creates the first valid Zone; "
            "T_boot is temporary and not inserted into normal gap history G."
        ),
    )


def is_zone_touch(zone: Phase2Zone, incoming_price: float | None, current_tolerance: float) -> bool:
    """Return True only when the exact frozen Phase 1 membership predicate is satisfied."""
    return _frozen_membership_predicate(zone.center, float(incoming_price), current_tolerance)


def classify_phase_2_event(
    *,
    seed_price: float,
    current_swing_price: float | None = None,
    zone: Phase2Zone | None = None,
    incoming_price: float | None = None,
    current_tolerance: float = 0.0,
) -> dict[str, Any]:
    if zone is None:
        event = create_first_zone(seed_price, current_swing_price)
        return {
            "kind": "FORMATION",
            "is_touch": False,
            "seed_price": event.seed_price,
            "current_swing_price": event.member_prices[1],
            "bootstrap_gap": event.bootstrap_gap,
            "zone": event,
            "note": event.note,
            "current_swing_excluded_from_history": event.current_swing_excluded_from_history,
        }

    if is_zone_touch(zone, incoming_price, current_tolerance):
        return {
            "kind": "TOUCH",
            "is_touch": True,
            "incoming_price": incoming_price,
            "current_tolerance": current_tolerance,
            "zone": zone,
            "note": "Once a valid Zone exists, Existing Zone Membership under the frozen Phase 1 membership predicate is the Zone Touch.",
        }

    return {
        "kind": "NON_TOUCH",
        "is_touch": False,
        "incoming_price": incoming_price,
        "current_tolerance": current_tolerance,
        "zone": zone,
        "note": "Not a Zone Touch under the approved post-Zone membership predicate.",
    }


__all__ = [
    "Phase2Zone",
    "create_first_zone",
    "is_zone_touch",
    "classify_phase_2_event",
]
