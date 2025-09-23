import pytest

from namer.disambiguation import Candidate, decide, Decision


DEFAULTS = dict(
    accept_distance=6,
    ambiguous_min=7,
    ambiguous_max=12,
    distance_margin_accept=3,
    majority_accept_fraction=0.7,
)


def test_accept_single_candidate_under_accept_distance():
    cands = [Candidate(guid="A", phash_distance=5)]  # <= accept_distance
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.ACCEPT
    assert guid == "A"


def test_accept_with_distance_margin():
    # best=5, second=9 -> margin 4 >= 3 -> accept best
    cands = [
        Candidate(guid="A", phash_distance=5),
        Candidate(guid="B", phash_distance=9),
        Candidate(guid="C", phash_distance=12),
    ]
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.ACCEPT
    assert guid == "A"


def test_ambiguous_when_no_margin_and_no_majority():
    # best=5, second=6 -> margin 1 < 3, majority fraction: top guid count 1 of 3 -> 0.333 < 0.7 -> ambiguous
    cands = [
        Candidate(guid="A", phash_distance=5),
        Candidate(guid="B", phash_distance=6),
        Candidate(guid="C", phash_distance=6),
    ]
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.AMBIGUOUS
    assert guid == ""


def test_accept_when_no_margin_but_majority_fraction_met():
    # best=5, second=6 -> margin 1 < 3, but majority guid fraction is 0.75 -> accept best
    cands = [
        Candidate(guid="A", phash_distance=5),
        Candidate(guid="A", phash_distance=6),
        Candidate(guid="A", phash_distance=6),
        Candidate(guid="B", phash_distance=6),
    ]
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.ACCEPT
    assert guid == "A"


def test_ambiguous_when_best_in_ambiguous_band():
    # best=9 in [7,12] -> ambiguous
    cands = [Candidate(guid="X", phash_distance=9)]
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.AMBIGUOUS
    assert guid == ""


def test_reject_when_best_beyond_ambiguous_band():
    # best=20 > 12 -> reject
    cands = [Candidate(guid="X", phash_distance=20)]
    guid, decision = decide(cands, **DEFAULTS)
    assert decision == Decision.REJECT
    assert guid == ""
