import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "compare_reference", Path(__file__).resolve().parents[1] / "scripts" / "validation" / "compare_reference.py"
)
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)


def test_match_events_one_to_one():
    m = cr.match_events([10, 20], [11, 12, 21], 1)
    assert m["matched"] == 2
    assert sorted(m["errors"]) == [1, 1]
    assert cr.match_events([10], [12], 1)["matched"] == 0


def test_evaluable_mask_drops_gap_with_unresolvable():
    sl = [(10, "contact", "annotated"), (None, "opposite_toe_off", "unresolvable"),
          (20, "contact", "annotated"), (24, "opposite_toe_off", "annotated")]
    mask = cr.evaluable_mask(sl, margin=2)
    assert 8 in mask and 10 in mask and 26 in mask
    assert not any(f in mask for f in range(11, 20))
    assert all(f in mask for f in range(20, 25))


def test_two_state_labels_skip_unresolved_gaps():
    sl = [(10, "contact", "annotated"), (14, "opposite_toe_off", "annotated"),
          (None, "contact", "unresolvable"), (30, "opposite_toe_off", "annotated")]
    labels = cr.two_state_labels(sl)
    assert labels == {f: "DS" for f in range(10, 14)}


def test_kappa_and_macro_f1():
    assert cr.kappa([0, 1, 0, 1], [0, 1, 0, 1], 2) == pytest.approx(1.0)
    assert cr.kappa([0, 0, 1, 1], [0, 1, 0, 1], 2) == pytest.approx(0.0)
    assert cr.macro_f1([0, 1, 2, 3], [0, 1, 2, 3], 4) == pytest.approx(1.0)


def test_p0_entries():
    states = {1: 3, 2: 0, 3: 0, 4: 1, 6: 0}
    assert cr.p0_entries(states) == [2]
