from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Tuple


class Decision(str, Enum):
    ACCEPT = 'accept'
    AMBIGUOUS = 'ambiguous'
    REJECT = 'reject'


@dataclass(frozen=True)
class Candidate:
    """
    Represents a single match candidate produced by search.

    Attributes
    - guid: unique identifier of the candidate (e.g., scene ID)
    - phash_distance: Hamming distance from the query perceptual hash (lower is better)
    """

    guid: str
    phash_distance: int


def _majority_fraction(candidates: Iterable[Candidate]) -> Tuple[str, float]:
    """
    Compute the majority fraction for the most frequent GUID among candidates.

    Returns a tuple (top_guid, fraction) where fraction in [0,1].
    If candidates is empty, returns ("", 0.0).
    """
    counts: dict[str, int] = {}
    total = 0
    for c in candidates:
        counts[c.guid] = counts.get(c.guid, 0) + 1
        total += 1
    if total == 0:
        return '', 0.0
    top_guid, top_count = max(counts.items(), key=lambda kv: kv[1])
    return top_guid, top_count / total


def decide(
    candidates: List[Candidate],
    *,
    accept_distance: int,
    ambiguous_min: int,
    ambiguous_max: int,
    distance_margin_accept: int,
    majority_accept_fraction: float,
) -> Tuple[str, Decision]:
    """
    Make a disambiguation decision from PHASH-based candidates.

    This function is pure and does not perform any I/O.

    Decision policy (simplified and provider-agnostic):
    1) If there are no candidates -> REJECT
    2) Sort candidates by phash_distance asc
    3) If best_distance <= accept_distance:
         - If only one candidate -> ACCEPT
         - Else if (second_distance - best_distance) >= distance_margin_accept -> ACCEPT
         - Else compute majority fraction of GUIDs; if >= majority_accept_fraction -> ACCEPT
         - Otherwise -> AMBIGUOUS
    4) Else if best_distance in [ambiguous_min, ambiguous_max] -> AMBIGUOUS
    5) Else -> REJECT

    Returns (guid, Decision). For non-ACCEPT cases, guid will be "".
    """
    if not candidates:
        return '', Decision.REJECT

    ordered = sorted(candidates, key=lambda c: c.phash_distance)
    best = ordered[0]

    if best.phash_distance <= accept_distance:
        if len(ordered) == 1:
            return best.guid, Decision.ACCEPT
        second = ordered[1]
        if (second.phash_distance - best.phash_distance) >= distance_margin_accept:
            return best.guid, Decision.ACCEPT
        # Not enough distance margin, check majority
        top_guid, frac = _majority_fraction(ordered)
        if top_guid == best.guid and frac >= majority_accept_fraction:
            return best.guid, Decision.ACCEPT
        return '', Decision.AMBIGUOUS

    if ambiguous_min <= best.phash_distance <= ambiguous_max:
        return '', Decision.AMBIGUOUS

    return '', Decision.REJECT
