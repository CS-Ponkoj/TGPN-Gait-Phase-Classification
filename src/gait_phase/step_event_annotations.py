"""Deterministic v0.2 step-event labels for CASIA C silhouettes.

Design and pre-registered validation: docs/step_event_labels_v0.2.md. Each frame inside a complete
step gets one of three observable step states (double support, early single support, late single
support), derived from detected contact, opposite toe-off, and leg-crossing events rather than
fixed fractions of an interval.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image

from .auto_annotations import (
    FRAME_LABEL_COLUMNS,
    _sha256,
    _write_gzip_csv,
    detect_contact_peaks,
    lower_limb_spread,
    smooth_signal,
)

STEP_STATES = ("double_support", "early_single_support", "late_single_support")
EVENT_COLUMNS = (
    "dataset",
    "subject_id",
    "sequence_id",
    "step_id",
    "contact_frame",
    "toe_off_frame",
    "crossing_frame",
    "next_contact_frame",
    "contact_source",
    "next_contact_source",
    "confidence",
    "annotation_source",
    "annotation_version",
)
ANNOTATION_SOURCE = "rule_step_events_ground_band"
GROUND_WINDOW = 6
BAND_FRACTION = 0.06  # amendment A1: band widened; planted test separates swing feet
GAP_FRACTION = 0.04
PLANTED_OVERLAP = 0.5  # amendment A1
SHIFT_FRACTION = 0.03  # amendment A1: planted foot centre moves <= 3% of body height per frame
MIN_FOOT_WIDTH = 2
PEAK_WINDOW = (-4, 3)
MAX_DS_FRACTION = 0.6
STEP_LIMITS = (0.5, 1.6)


@dataclass
class FrameFeatures:
    spread: float
    lowest_row: float
    body_height: float
    mask: np.ndarray | None  # binary foreground mask


def frame_features(path: str | Path) -> FrameFeatures:
    """Read one silhouette and return the features v0.2 needs."""
    with Image.open(path) as source:
        mask = np.asarray(source.convert("L")) > 0
    spread = lower_limb_spread(path)
    ys = np.flatnonzero(mask.any(axis=1))
    if len(ys) == 0 or mask.sum() < 20:
        return FrameFeatures(spread, float("nan"), float("nan"), None)
    all_y = np.nonzero(mask)[0]
    y1, y99 = np.percentile(all_y, [1, 99])
    return FrameFeatures(spread, float(ys[-1]), float(y99 - y1 + 1), mask)


def foot_runs(mask: np.ndarray, ground_row: int, band: int, gap: int) -> list[tuple[int, int]]:
    """Separated foreground column runs (inclusive x-intervals) inside the ground band."""
    top = max(0, ground_row - band)
    rows = mask[top : ground_row + 1]
    if rows.size == 0:
        return []
    runs: list[list[int]] = []
    for x in np.flatnonzero(rows.any(axis=0)):
        if runs and x - runs[-1][1] - 1 <= gap:
            runs[-1][1] = int(x)
        else:
            runs.append([int(x), int(x)])
    return [(s, e) for s, e in runs if e - s + 1 >= MIN_FOOT_WIDTH]


def count_feet(mask: np.ndarray, ground_row: int, band: int, gap: int) -> int:
    """Number of separated foreground column runs touching the ground band."""
    return len(foot_runs(mask, ground_row, band, gap))


def _overlap_fraction(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = min(a[1], b[1]) - max(a[0], b[0]) + 1
    return max(0, inter) / min(a[1] - a[0] + 1, b[1] - b[0] + 1)


def planted_counts(runs_per_frame: list[list[tuple[int, int]] | None], max_shift: float) -> np.ndarray:
    """Count stationary feet. A ground-band run is planted when its best-overlapping run in the next
    frame (the previous frame for the last frame) overlaps it by at least half of the smaller width
    and its center moves by at most `max_shift` pixels."""
    n = len(runs_per_frame)
    counts = np.full(n, np.nan)
    for t, runs in enumerate(runs_per_frame):
        if runs is None:
            continue
        other_index = t + 1 if t + 1 < n else t - 1
        other = runs_per_frame[other_index] if 0 <= other_index < n else None
        if other is None:
            continue
        planted = 0
        for r in runs:
            if not other:
                continue
            best = max(other, key=lambda o: _overlap_fraction(r, o))
            shift = abs((best[0] + best[1]) / 2 - (r[0] + r[1]) / 2)
            if _overlap_fraction(r, best) >= PLANTED_OVERLAP and shift <= max_shift:
                planted += 1
        counts[t] = planted
    return counts


def feet_on_ground(masks: list[np.ndarray | None], lowest: np.ndarray, heights: np.ndarray) -> np.ndarray:
    """Per-frame count of planted (stationary) feet in a rolling ground band (NaN when unavailable)."""
    n = len(masks)
    median_height = float(np.nanmedian(heights)) if np.isfinite(heights).any() else 100.0
    band = max(3, int(round(BAND_FRACTION * median_height)))
    gap = max(2, int(round(GAP_FRACTION * median_height)))
    runs_per_frame: list[list[tuple[int, int]] | None] = []
    for t in range(n):
        window = lowest[max(0, t - GROUND_WINDOW) : t + GROUND_WINDOW + 1]
        if masks[t] is None or not np.isfinite(window).any():
            runs_per_frame.append(None)
            continue
        runs_per_frame.append(foot_runs(masks[t], int(np.nanmax(window)), band, gap))
    return planted_counts(runs_per_frame, max(2.0, SHIFT_FRACTION * median_height))


def double_support_runs(counts: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) positions of consecutive frames with two or more feet down."""
    runs: list[tuple[int, int]] = []
    start = None
    for i, value in enumerate(counts):
        flag = bool(np.isfinite(value) and value >= 2)
        if flag and start is None:
            start = i
        if not flag and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(counts) - 1))
    return runs


def detect_step_events(spreads: np.ndarray, counts: np.ndarray) -> tuple[list[dict[str, Any]], float]:
    """Return per-step events (positions within the sequence) and the median step length."""
    peaks = detect_contact_peaks(spreads)
    if len(peaks) < 2:
        return [], float("nan")
    median_step = float(np.median(np.diff(peaks)))
    runs = double_support_runs(counts)
    anchors = []
    for p in peaks:
        lo, hi = p + PEAK_WINDOW[0], p + PEAK_WINDOW[1]
        best = None
        for start, end in runs:
            if end < lo or start > hi:
                continue
            length = end - start + 1
            if not 1 <= length <= MAX_DS_FRACTION * median_step:
                continue
            distance = 0 if start <= p <= end else min(abs(start - p), abs(end - p))
            if best is None or distance < best[0]:
                best = (distance, start, end)
        if best is not None:
            anchors.append({"contact": best[1], "toe_off": best[2] + 1, "source": "ground_band"})
        else:
            anchors.append({"contact": p, "toe_off": None, "source": "spread_peak"})
    # keep contacts strictly increasing
    cleaned: list[dict[str, Any]] = []
    for a in anchors:
        if not cleaned or a["contact"] > cleaned[-1]["contact"]:
            cleaned.append(a)
    smooth = smooth_signal(spreads)
    steps = []
    for a, b in zip(cleaned, cleaned[1:]):
        length = b["contact"] - a["contact"]
        if not STEP_LIMITS[0] * median_step <= length <= STEP_LIMITS[1] * median_step:
            continue
        toe_off = a["toe_off"] if a["toe_off"] is not None and a["toe_off"] < b["contact"] - 1 else None
        search_start = toe_off + 1 if toe_off is not None else a["contact"] + int(round(0.25 * length))
        window = range(search_start, b["contact"])
        if len(window) == 0:
            continue
        crossing = min(window, key=lambda i: (smooth[i], i))
        steps.append(
            {
                "contact": a["contact"],
                "toe_off": toe_off,
                "crossing": crossing,
                "next_contact": b["contact"],
                "contact_source": a["source"],
                "next_contact_source": b["source"],
                "confidence": "medium"
                if a["source"] == "ground_band" and b["source"] == "ground_band" and toe_off is not None
                else "low",
            }
        )
    return steps, median_step


def label_step_frames(steps: list[dict[str, Any]], n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """State index (-1 = unlabeled), progress within step, and step number per position."""
    state = np.full(n, -1)
    progress = np.full(n, np.nan)
    step_of = np.full(n, -1)
    for k, s in enumerate(steps):
        c, x, nxt = s["contact"], s["crossing"], s["next_contact"]
        t = s["toe_off"] if s["toe_off"] is not None else c + max(1, int(round(0.2 * (nxt - c))))
        t = min(max(t, c + 1), x)
        for i in range(c, nxt):
            state[i] = 0 if i < t else (1 if i < x else 2)
            progress[i] = (i - c) / (nxt - c)
            step_of[i] = k
    return state, progress, step_of


def annotate_sequence(sequence: pd.DataFrame, workspace: Path, version: str):
    ordered = sequence.copy()
    ordered["numeric_frame_index"] = pd.to_numeric(ordered["frame_index"], errors="raise")
    ordered = ordered.sort_values(["numeric_frame_index", "relative_path"]).reset_index(drop=True)
    frames = ordered["numeric_frame_index"].to_numpy(dtype=int)
    if len(frames) != int(frames.max() - frames.min() + 1):
        raise ValueError(f"Sequence is not frame-contiguous: {ordered['sequence_id'].iloc[0]}")
    feats = [frame_features(workspace / rel) for rel in ordered["relative_path"]]
    spreads = np.array([f.spread for f in feats], dtype=float)
    lowest = np.array([f.lowest_row for f in feats], dtype=float)
    heights = np.array([f.body_height for f in feats], dtype=float)
    counts = feet_on_ground([f.mask for f in feats], lowest, heights)
    steps, median_step = detect_step_events(spreads, counts)
    state, progress, step_of = label_step_frames(steps, len(ordered))

    labels = []
    for i, row in ordered.iterrows():
        if state[i] < 0:
            continue
        labels.append(
            {
                **{column: row[column] for column in FRAME_LABEL_COLUMNS[:9]},
                "phase_label": STEP_STATES[state[i]],
                "phase_index": int(state[i]),
                "cycle_position": round(float(progress[i]), 6),
                "confidence": steps[step_of[i]]["confidence"],
                "annotation_source": ANNOTATION_SOURCE,
                "annotation_version": version,
            }
        )
    events = [
        {
            "dataset": ordered["dataset"].iloc[0],
            "subject_id": ordered["subject_id"].iloc[0],
            "sequence_id": ordered["sequence_id"].iloc[0],
            "step_id": f"step_{k + 1:03d}",
            "contact_frame": int(frames[s["contact"]]),
            "toe_off_frame": int(frames[s["toe_off"]]) if s["toe_off"] is not None else None,
            "crossing_frame": int(frames[s["crossing"]]),
            "next_contact_frame": int(frames[s["next_contact"]]),
            "contact_source": s["contact_source"],
            "next_contact_source": s["next_contact_source"],
            "confidence": s["confidence"],
            "annotation_source": ANNOTATION_SOURCE,
            "annotation_version": version,
        }
        for k, s in enumerate(steps)
    ]
    qc = {
        "dataset": ordered["dataset"].iloc[0],
        "subject_id": ordered["subject_id"].iloc[0],
        "sequence_id": ordered["sequence_id"].iloc[0],
        "condition": ordered["condition"].iloc[0],
        "split": ordered["split"].iloc[0],
        "fold": ordered["fold"].iloc[0],
        "frame_count": int(len(ordered)),
        "steps": len(steps),
        "medium_steps": sum(s["confidence"] == "medium" for s in steps),
        "median_step_frames": round(median_step, 4) if np.isfinite(median_step) else None,
        "labeled_frames": int((state >= 0).sum()),
        "double_support_fraction": round(float((state == 0).sum() / max(1, (state >= 0).sum())), 4),
        "missing_feature_frames": int(np.isnan(spreads).sum()),
    }
    return (pd.DataFrame(labels, columns=FRAME_LABEL_COLUMNS), pd.DataFrame(events, columns=EVENT_COLUMNS), qc)


def build_step_event_release(manifest: pd.DataFrame, workspace: str | Path, output: str | Path,
                             version: str, source_manifest: str | Path) -> dict[str, object]:
    workspace, output = Path(workspace), Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Annotation output already exists and is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    eligible = set(manifest.loc[manifest["dataset"].eq("casia_c") & manifest["exclusion_reason"].fillna("").eq(""),
                                "sample_id"])
    casia_c = manifest[manifest["dataset"].eq("casia_c")]
    label_parts, event_parts, qc_rows = [], [], []
    for _, sequence in casia_c.groupby("sequence_id", sort=True):
        labels, events, qc = annotate_sequence(sequence, workspace, version)
        label_parts.append(labels[labels["sample_id"].isin(eligible)])
        event_parts.append(events)
        qc["eligible_labeled_frames"] = int(labels["sample_id"].isin(eligible).sum())
        qc_rows.append(qc)
    labels = pd.concat(label_parts, ignore_index=True)
    events = pd.concat(event_parts, ignore_index=True)
    qc = pd.DataFrame(qc_rows)
    _write_gzip_csv(labels, output / "frame_labels.csv.gz")
    _write_gzip_csv(events, output / "step_events.csv.gz")
    qc.to_csv(output / "sequence_qc.csv", index=False)
    summary = {
        "annotation_version": version,
        "status": "RULE_BASED_PROVISIONAL_NOT_GROUND_TRUTH",
        "design": "docs/step_event_labels_v0.2.md",
        "states": list(STEP_STATES),
        "labeled_frames": int(len(labels)),
        "eligible_casia_c_frames": int(len(eligible)),
        "unlabeled_eligible_frames": int(len(eligible) - len(labels)),
        "sequences_with_steps": int(labels["sequence_id"].nunique()),
        "steps": int(len(events)),
        "confidence_counts": labels["confidence"].value_counts().sort_index().astype(int).to_dict(),
        "state_counts": labels["phase_label"].value_counts().sort_index().astype(int).to_dict(),
        "split_counts": labels["split"].value_counts().sort_index().astype(int).to_dict(),
        "source_manifest_sha256": _sha256(Path(source_manifest)),
    }
    (output / "provenance.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    artifacts = sorted(p for p in output.iterdir() if p.is_file() and p.name != "checksums.sha256")
    (output / "checksums.sha256").write_text("".join(f"{_sha256(p)}  {p.name}\n" for p in artifacts), encoding="utf-8")
    return summary
