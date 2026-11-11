"""Build the v0.2 step-event label release (docs/step_event_labels_v0.2.md).

Example:
    python scripts/build_step_event_labels.py --workspace . \
        --manifest data/manifests/generated/casia_a_c_split.csv \
        --output annotations/provisional/v0.2-step-events
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gait_phase.step_event_annotations import build_step_event_release  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True, help="Root that relative image paths resolve against")
    parser.add_argument("--manifest", type=Path, required=True, help="Split manifest CSV")
    parser.add_argument("--output", type=Path, default=Path("annotations/provisional/v0.2-step-events"))
    parser.add_argument("--version", default="v0.2-step-events")
    args = parser.parse_args()
    manifest = pd.read_csv(args.manifest, dtype=str, keep_default_na=False)
    summary = build_step_event_release(manifest, args.workspace, args.output, args.version, args.manifest)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
