"""Merge per-batch annotation CSVs into annotations/validation/v1 and validate them.

Checks: exact headers, every sampled sequence reviewed exactly once, event frames inside the
sequence (excluding the first/last two frames), unique event ids, strictly increasing
Track F frames, and allowed vocabularies. Prints a coverage summary. Exits nonzero on errors.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

S_HEADER = "dataset,subject_id,sequence_id,event_id,event_type,frame,status,confidence,annotator_id,notes".split(",")
F_HEADER = (
    "dataset,subject_id,sequence_id,cycle_id,initial_contact_frame,mid_stance_frame,terminal_stance_frame,"
    "swing_frame,next_initial_contact_frame,status,annotator_id,confidence,notes"
).split(",")
R_HEADER = (
    "sequence_id,walking_direction,frames_reviewed,track_s_annotated,track_s_unresolvable,"
    "track_f_annotated,track_f_excluded,quality_notes"
).split(",")
F_FRAMES = F_HEADER[4:9]


def read(path: Path, header: list[str], errors: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != header:
            errors.append(f"{path}: header {reader.fieldnames} != {header}")
            return []
        return list(reader)


def write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_dirs", nargs="+", type=Path)
    parser.add_argument("--sampling-frame", type=Path, default=Path("annotations/validation/v1/sampling_frame.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("annotations/validation/v1"))
    args = parser.parse_args()

    with args.sampling_frame.open(newline="") as handle:
        frame = {r["sequence_id"]: r for r in csv.DictReader(handle)}
    errors: list[str] = []
    events, strides, reviews = [], [], []
    for d in args.batch_dirs:
        events += read(d / "track_s_events.csv", S_HEADER, errors)
        strides += read(d / "track_f_boundaries.csv", F_HEADER, errors)
        reviews += read(d / "sequence_review.csv", R_HEADER, errors)

    counts = Counter(r["sequence_id"] for r in reviews)
    for seq in frame:
        if counts[seq] != 1:
            errors.append(f"{seq}: reviewed {counts[seq]} times")
    for seq in counts:
        if seq not in frame:
            errors.append(f"{seq}: not in sampling frame")

    seen = set()
    for e in events:
        seq = frame.get(e["sequence_id"])
        key = (e["sequence_id"], e["event_id"])
        if seq is None:
            errors.append(f"event for unknown sequence {key}")
            continue
        if key in seen:
            errors.append(f"duplicate event id {key}")
        seen.add(key)
        if e["event_type"] not in {"contact", "opposite_toe_off"}:
            errors.append(f"{key}: bad event_type {e['event_type']}")
        if e["status"] == "annotated":
            lo, hi = int(seq["first_frame"]) + 2, int(seq["last_frame"]) - 2
            if not e["frame"] or not lo <= int(e["frame"]) <= hi:
                errors.append(f"{key}: frame {e['frame']!r} outside [{lo}, {hi}]")
            if e["confidence"] not in {"high", "medium", "low"}:
                errors.append(f"{key}: bad confidence {e['confidence']}")
        elif e["status"] == "unresolvable":
            if e["frame"]:
                errors.append(f"{key}: unresolvable event has a frame")
        else:
            errors.append(f"{key}: bad status {e['status']}")

    for s in strides:
        key = (s["sequence_id"], s["cycle_id"])
        if s["sequence_id"] not in frame:
            errors.append(f"stride for unknown sequence {key}")
        if s["status"] == "annotated":
            values = [s[c] for c in F_FRAMES]
            if not all(values):
                errors.append(f"{key}: annotated stride missing frames")
            elif any(int(a) >= int(b) for a, b in zip(values, values[1:])):
                errors.append(f"{key}: frames not strictly increasing {values}")
        elif s["status"] != "excluded":
            errors.append(f"{key}: bad status {s['status']}")

    if errors:
        print("\n".join(errors[:50]))
        print(f"{len(errors)} errors")
        sys.exit(1)

    order = list(frame)
    events.sort(key=lambda e: (order.index(e["sequence_id"]), e["event_id"]))
    strides.sort(key=lambda s: (order.index(s["sequence_id"]), s["cycle_id"]))
    reviews.sort(key=lambda r: order.index(r["sequence_id"]))
    write(args.output_dir / "track_s_events.csv", S_HEADER, events)
    write(args.output_dir / "track_f_boundaries.csv", F_HEADER, strides)
    write(args.output_dir / "sequence_review.csv", R_HEADER, reviews)

    fam = {k: v["family"] for k, v in frame.items()}
    print("Track S by family (annotated / unresolvable):")
    for f in ("fn", "fs", "fq", "fb"):
        a = sum(1 for e in events if fam[e["sequence_id"]] == f and e["status"] == "annotated")
        u = sum(1 for e in events if fam[e["sequence_id"]] == f and e["status"] == "unresolvable")
        print(f"  {f}: {a} / {u}")
    print("Track S confidence:", dict(Counter(e["confidence"] for e in events if e["status"] == "annotated")))
    print("Track F:", dict(Counter(s["status"] for s in strides)),
          "confidence", dict(Counter(s["confidence"] for s in strides if s["status"] == "annotated")))
    print("Subjects with >=1 annotated event:", len({e["subject_id"] for e in events if e["status"] == "annotated"}))


if __name__ == "__main__":
    main()
