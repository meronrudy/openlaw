import math

from core.native.annotate import precedent_weighted
from core.native.intervals import closed, Interval


def _annotations(*clauses):
    """
    Build annotations structure:
      clauses: list of lists of Interval
    """
    return list(clauses)


def _almost_equal(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def test_precedent_weighted_equal_intervals():
    # Three clauses, each with a single equal interval [0.5, 0.5]
    anns = _annotations([closed(0.5, 0.5)], [closed(0.5, 0.5)], [closed(0.5, 0.5)])
    weights = [1.0, 1.0, 1.0]
    itv: Interval = precedent_weighted(anns, weights)
    assert _almost_equal(float(itv.lower), 0.5)
    assert _almost_equal(float(itv.upper), 0.5)


def test_precedent_weighted_single_controlling():
    # Only controlling has support; persuasive/contrary empty
    anns = _annotations([closed(0.8, 0.9)], [], [])
    weights = [0.6, 0.3, 0.1]
    itv: Interval = precedent_weighted(anns, weights)
    # Semantics: average of weighted sums over total number of intervals (n=1 here)
    expected_lower = 0.8 * weights[0]
    expected_upper = 0.9 * weights[0]
    assert _almost_equal(float(itv.lower), expected_lower)
    assert _almost_equal(float(itv.upper), expected_upper)


def test_precedent_weighted_mixed_supports():
    # Mixed supports across classes
    anns = _annotations(
        [closed(0.7, 0.9)],      # controlling
        [closed(0.5, 0.8)],      # persuasive
        [closed(0.2, 0.3)],      # contrary
    )
    weights = [0.6, 0.3, 0.1]
    itv: Interval = precedent_weighted(anns, weights)
    # One interval per clause => n=3
    wl = 0.7 * 0.6 + 0.5 * 0.3 + 0.2 * 0.1
    wu = 0.9 * 0.6 + 0.8 * 0.3 + 0.3 * 0.1
    expected_lower = wl / 3.0
    expected_upper = wu / 3.0
    assert _almost_equal(float(itv.lower), expected_lower)
    assert _almost_equal(float(itv.upper), expected_upper)