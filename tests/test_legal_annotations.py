import numpy as np
import numba
import pyreason.scripts.numba_wrapper.numba_types.interval_type as interval
import pyreason.scripts.annotation_functions.annotation_functions as ann


def _make_annotations(bounds_list):
    """
    bounds_list: List of (lower, upper) tuples per clause (one annotation per clause for simplicity)
    Returns: numba.typed.List of clauses, each a numba.typed.List of interval.closed
    """
    annotations = numba.typed.List.empty_list(numba.types.ListType(interval.interval_type))
    for (lo, up) in bounds_list:
        clause = numba.typed.List.empty_list(interval.interval_type)
        clause.append(interval.closed(lo, up))
        annotations.append(clause)
    return annotations


def test_legal_burdens_and_conservative_aggregator():
    # Two clauses: C1 in [0.6,0.8], C2 in [0.4,0.6]; weights = [0.6, 0.4]
    annotations = _make_annotations([(0.6, 0.8), (0.4, 0.6)])
    weights = np.array([0.6, 0.4], dtype=np.float64)

    # Weighted lower avg = 0.6*0.6 + 0.4*0.4 = 0.36 + 0.16 = 0.52
    # Weighted upper avg = 0.6*0.8 + 0.4*0.6 = 0.48 + 0.24 = 0.72

    # Civil 0.51 clamp -> lower should be >= 0.51 (here 0.52), upper approx 0.72
    civil = ann.legal_burden_civil_051(annotations, weights)
    assert civil.lower >= 0.51 - 1e-9
    assert abs(civil.lower - 0.52) < 1e-6
    assert abs(civil.upper - 0.72) < 1e-6

    # Clear & convincing 0.75 clamp -> lower -> 0.75, upper ~0.72 then check_bound caps upper to 1.0
    clear = ann.legal_burden_clear_075(annotations, weights)
    assert abs(clear.lower - 0.75) < 1e-6
    # upper stays same aggregation upper (0.72) but _check_bound min with 1.0 -> still 0.72
    assert abs(clear.upper - 0.72) < 1e-6

    # Criminal 0.90 clamp -> lower -> 0.90, upper ~0.72
    crim = ann.legal_burden_criminal_090(annotations, weights)
    assert abs(crim.lower - 0.90) < 1e-6
    assert abs(crim.upper - 0.72) < 1e-6

    # Conservative min: lower = min(weighted clause sums) = min(0.36, 0.16) = 0.16
    # upper = average of weighted uppers: (0.48 + 0.24)/2 = 0.36
    cons = ann.legal_conservative_min(annotations, weights)
    assert abs(cons.lower - 0.16) < 1e-6
    assert abs(cons.upper - 0.36) < 1e-6