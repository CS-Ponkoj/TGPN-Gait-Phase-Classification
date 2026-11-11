"""Draw the held-out validation sampling frame (docs/annotation_validation_plan.md, section 5.1).

One retained sequence per condition family per held-out subject, chosen with a fixed seed.
Reads only sequence-level QC metadata (split, condition, confidence, frame count); it never
reads per-frame rule labels, rule intervals, or model predictions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
from pathlib import Path

FAMILIES = ("fn", "fs", "fq", "fb")
SEED = 20261111


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qc", type=Path, default=Path("annotations/provisional/v0.1-ai/sequence_qc.csv"))
    parser.add_argument("--raw-root", type=Path, required=True, help="Folder containing data/raw/casia_c")
    parser.add_argument("--output", type=Path, default=Path("annotations/validation/v1/sampling_frame.csv"))
    args = parser.parse_args()

    with args.qc.open(newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["split"] == "test" and r["confidence"] == "medium"]

    by_key: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        by_key.setdefault((row["subject_id"], row["condition"][:2]), []).append(row)

    rng = random.Random(SEED)
    chosen = []
    for subject in sorted({r["subject_id"] for r in rows}):
        for family in FAMILIES:
            candidates = sorted(by_key.get((subject, family), []), key=lambda r: r["sequence_id"])
            if not candidates:
                continue
            pick = rng.choice(candidates)
            number = subject.split(":")[1]
            folder = args.raw_root / "data" / "raw" / "casia_c" / number / number / pick["condition"]
            frames = sorted(int(p.stem) for p in folder.glob("*.png"))
            chosen.append(
                {
                    "subject_id": subject,
                    "sequence_id": pick["sequence_id"],
                    "family": family,
                    "condition": pick["condition"],
                    "first_frame": frames[0],
                    "last_frame": frames[-1],
                    "frame_count": len(frames),
                    "contiguous": int(frames[-1] - frames[0] + 1 == len(frames)),
                    "candidates_in_family": len(candidates),
                }
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(chosen[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(chosen)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"{len(chosen)} sequences, seed {SEED}, sha256 {digest}")


if __name__ == "__main__":
    main()
