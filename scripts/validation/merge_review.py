"""Merge per-batch AI review decisions into annotations/validation/v1/ai_review.csv and validate.

Checks that each existing event and stride has exactly one review row, that the vocabularies are
valid, and that correct/add rows carry a proposed frame. Prints decision counts and a per-sequence
attention list (sequences with any correct/flag/reject/add, ranked by count).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

HEADER = "sequence_id,item_type,item_id,decision,original_frame,proposed_frame,reason,reviewer_id".split(",")
DECISIONS = {"accept", "correct", "flag", "reject", "add"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_dirs", nargs="+", type=Path)
    parser.add_argument("--validation-dir", type=Path, default=Path("annotations/validation/v1"))
    args = parser.parse_args()
    v = args.validation_dir

    rows, errors = [], []
    for d in args.review_dirs:
        with (d / "ai_review.csv").open(newline="", encoding="utf-8-sig") as h:
            reader = csv.DictReader(h)
            if reader.fieldnames != HEADER:
                errors.append(f"{d}: header {reader.fieldnames}")
                continue
            rows += list(reader)

    with (v / "track_s_events.csv").open(newline="") as h:
        events = {(e["sequence_id"], e["event_id"]) for e in csv.DictReader(h)}
    with (v / "track_f_boundaries.csv").open(newline="") as h:
        strides = {(s["sequence_id"], s["cycle_id"]) for s in csv.DictReader(h)}
    with (v / "sampling_frame.csv").open(newline="") as h:
        order = [r["sequence_id"] for r in csv.DictReader(h)]

    seen = Counter()
    for r in rows:
        key = (r["sequence_id"], r["item_id"])
        if r["decision"] not in DECISIONS:
            errors.append(f"{key}: bad decision {r['decision']}")
        if r["decision"] in {"correct", "add"} and not r["proposed_frame"].strip():
            errors.append(f"{key}: {r['decision']} without proposed_frame")
        if r["item_type"] == "event" and r["decision"] != "add":
            if key not in events:
                errors.append(f"{key}: review of unknown event")
            seen[("event",) + key] += 1
        elif r["item_type"] == "stride":
            if key not in strides:
                errors.append(f"{key}: review of unknown stride")
            seen[("stride",) + key] += 1
        elif r["item_type"] not in {"event", "sequence"}:
            errors.append(f"{key}: bad item_type {r['item_type']}")
    calibration = "casia_c:001:fn03"
    for key in events:
        if key[0] != calibration and seen[("event",) + key] != 1:
            errors.append(f"event {key}: {seen[('event',) + key]} review rows")
    for key in strides:
        if key[0] != calibration and seen[("stride",) + key] != 1:
            errors.append(f"stride {key}: {seen[('stride',) + key]} review rows")
    if errors:
        print("\n".join(errors[:60]))
        print(f"{len(errors)} errors")
        sys.exit(1)

    rows.sort(key=lambda r: (order.index(r["sequence_id"]), r["item_type"], r["item_id"]))
    with (v / "ai_review.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.DictWriter(h, fieldnames=HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print("Decisions by item type:")
    for t in ("event", "stride", "sequence"):
        print(f"  {t}:", dict(Counter(r["decision"] for r in rows if r["item_type"] == t)))
    attention = defaultdict(Counter)
    for r in rows:
        if r["decision"] != "accept":
            attention[r["sequence_id"]][r["decision"]] += 1
    ranked = sorted(attention.items(), key=lambda kv: -sum(kv[1].values()))
    print(f"Sequences with any non-accept decision: {len(ranked)} of {len(order)}")
    for seq, c in ranked:
        print(f"  {seq}: {dict(c)}")


if __name__ == "__main__":
    main()
