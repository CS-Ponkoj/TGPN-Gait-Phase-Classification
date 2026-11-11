import numpy as np
import pytest

from gait_phase.step_event_annotations import (
    count_feet,
    detect_step_events,
    double_support_runs,
    label_step_frames,
    planted_counts,
)


def test_count_feet_merges_small_gaps_and_counts_separate_feet():
    mask = np.zeros((20, 60), dtype=bool)
    mask[17:20, 5:12] = True  # foot 1
    mask[17:20, 13:15] = True  # fragment of foot 1 (gap of 1 column)
    mask[17:20, 40:48] = True  # foot 2
    assert count_feet(mask, ground_row=19, band=3, gap=2) == 2
    lifted = mask.copy()
    lifted[17:20, 40:48] = False
    lifted[5:8, 40:48] = True  # foot 2 in the air
    assert count_feet(lifted, ground_row=19, band=3, gap=2) == 1


def test_planted_counts_ignore_moving_feet():
    stance = (10, 20)
    frames = [
        [stance, (40, 50)],  # swing foot at 40-50, moves 15 px next frame
        [stance, (55, 65)],
        [stance, (56, 66)],  # swing foot has landed (moves 1 px)
        [stance, (56, 66)],
    ]
    counts = planted_counts(frames, max_shift=3)
    assert list(counts) == [1, 2, 2, 2]


def test_double_support_runs():
    counts = np.array([1, 2, 2, 1, np.nan, 2, 1, 2])
    assert double_support_runs(counts) == [(1, 2), (5, 5), (7, 7)]


def synthetic_walk(steps=5, step_len=12, ds=3):
    """Spread peaks at each contact; two feet on the ground for `ds` frames after contact."""
    n = steps * step_len + 6
    t = np.arange(n)
    spreads = 0.3 + 0.1 * np.cos(2 * np.pi * (t - 3) / step_len)
    counts = np.ones(n)
    for k in range(steps + 1):
        start = 3 + k * step_len
        counts[start : start + ds] = 2
    return spreads, counts


def test_detect_step_events_on_synthetic_walk():
    spreads, counts = synthetic_walk()
    steps, median = detect_step_events(spreads, counts)
    assert median == pytest.approx(12)
    assert len(steps) >= 3
    for s in steps:
        assert s["next_contact"] - s["contact"] == 12
        assert s["toe_off"] - s["contact"] == 3
        assert s["toe_off"] < s["crossing"] < s["next_contact"]
        assert s["confidence"] == "medium"


def test_fallback_to_spread_peak_without_double_support():
    spreads, counts = synthetic_walk()
    steps, _ = detect_step_events(spreads, np.ones_like(counts))
    assert steps and all(s["toe_off"] is None and s["confidence"] == "low" for s in steps)


def test_label_step_frames_assigns_three_states():
    steps = [{"contact": 2, "toe_off": 5, "crossing": 9, "next_contact": 14, "confidence": "medium"}]
    state, progress, step_of = label_step_frames(steps, 16)
    assert list(state[:2]) == [-1, -1]
    assert list(state[2:5]) == [0, 0, 0]
    assert list(state[5:9]) == [1, 1, 1, 1]
    assert list(state[9:14]) == [2] * 5
    assert state[14] == -1 and progress[2] == 0
