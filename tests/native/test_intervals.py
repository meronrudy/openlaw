import math
import pytest

from core.native.intervals import Interval, closed, intersect


def test_closed_constructor_and_clamp():
    iv = closed(1.2, -0.1)  # invalid becomes [0,1]
    assert iv.lower == 0.0
    assert iv.upper == 1.0

    iv2 = closed(-0.5, 0.4)  # clamp to [0,0.4]
    assert iv2.lower == 0.0
    assert iv2.upper == 0.4


def test_interval_equality_and_hash():
    a = closed(0.2, 0.8)
    b = closed(0.2, 0.8)
    c = closed(0.3, 0.9)
    assert a == b
    assert a != c
    s = {a, b, c}
    assert len(s) == 2


def test_intersection_basic():
    a = closed(0.2, 0.9)
    b = closed(0.5, 1.0)
    c = a.intersection(b)
    assert c.lower == 0.5
    assert c.upper == 0.9

    # functional helper
    d = intersect(a, b)
    assert d.lower == 0.5 and d.upper == 0.9


def test_intersection_disjoint_yields_top():
    a = closed(0.0, 0.3)
    b = closed(0.4, 0.7)
    c = a.intersection(b)
    # per parity rules, invalid -> [0,1]
    assert c.lower == 0.0 and c.upper == 1.0


def test_reset_and_prev_snapshot():
    a = closed(0.2, 0.6)
    assert a.prev_lower == 0.2 and a.prev_upper == 0.6
    a.set_lower_upper(0.3, 0.7)
    assert a.lower == 0.3 and a.upper == 0.7
    # prev snapshot remains at creation until reset
    assert a.prev_lower == 0.2 and a.prev_upper == 0.6

    a.reset()
    assert a.lower == 0.0 and a.upper == 1.0
    assert a.prev_lower == 0.3 and a.prev_upper == 0.7


def test_static_flag_and_change_detection():
    a = closed(0.4, 0.9)
    assert not a.is_static()
    a.set_static(True)
    assert a.is_static()

    # has_changed compares current to prev snapshot
    a.set_lower_upper(0.5, 0.9)
    assert a.has_changed() is True