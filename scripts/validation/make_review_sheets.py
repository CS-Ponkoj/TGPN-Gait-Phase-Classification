"""Render review sheets: the blinded contact sheets with the AI-proposed annotations drawn on.

Contact frames are boxed green, opposite toe-offs orange, unresolvable windows are noted in the
tile header, and Track F stride boundaries are listed in a footer. Rule labels and model
predictions are NOT drawn, so the reviewer judges the AI annotations against the silhouettes only.

Sheets contain licensed CASIA imagery: write them outside the repository and never commit them.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

COLUMNS = 8
COLOURS = {"contact": (60, 200, 90), "opposite_toe_off": (255, 150, 40)}
SHORT = {"contact": "C", "opposite_toe_off": "T"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-dir", type=Path, default=Path("annotations/validation/v1"))
    parser.add_argument("--sheets", type=Path, required=True, help="Folder from make_contact_sheets.py")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with (args.validation_dir / "sampling_frame.csv").open(newline="") as h:
        frame = list(csv.DictReader(h))
    events, strides, reviews = defaultdict(list), defaultdict(list), {}
    with (args.validation_dir / "track_s_events.csv").open(newline="") as h:
        for e in csv.DictReader(h):
            events[e["sequence_id"]].append(e)
    with (args.validation_dir / "track_f_boundaries.csv").open(newline="") as h:
        for s in csv.DictReader(h):
            strides[s["sequence_id"]].append(s)
    with (args.validation_dir / "sequence_review.csv").open(newline="") as h:
        for r in csv.DictReader(h):
            reviews[r["sequence_id"]] = r

    for seq in frame:
        sid = seq["sequence_id"]
        name = sid.replace(":", "_") + ".png"
        base = Image.open(args.sheets / name).convert("RGB")
        n = int(seq["frame_count"])
        rows = (n + COLUMNS - 1) // COLUMNS
        tile_w, tile_h = base.width // COLUMNS, base.height // rows
        footer = [f"{sid}  direction={reviews[sid]['walking_direction']}  notes: {reviews[sid]['quality_notes']}"[:230]]
        unresolved = [
            f"{SHORT[e['event_type']]}? {e['event_id']} {e['notes']}"[:110]
            for e in events[sid] if e["status"] == "unresolvable"
        ]
        if unresolved:
            footer.append("Unresolvable: " + " | ".join(unresolved)[:230])
        for s in strides[sid]:
            if s["status"] == "annotated":
                vals = [s[c] for c in ("initial_contact_frame", "mid_stance_frame", "terminal_stance_frame",
                                       "swing_frame", "next_initial_contact_frame")]
                footer.append(f"Track F {s['cycle_id']} ({s['confidence']}): IC {vals[0]}  MS {vals[1]}  "
                              f"TS {vals[2]}  SW {vals[3]}  next IC {vals[4]}")
            else:
                footer.append(f"Track F {s['cycle_id']} EXCLUDED: {s['notes']}"[:230])
        out = Image.new("RGB", (base.width, base.height + 18 * len(footer) + 8), (25, 25, 25))
        out.paste(base, (0, 0))
        draw = ImageDraw.Draw(out)
        first = int(seq["first_frame"])
        for e in events[sid]:
            if e["status"] != "annotated":
                continue
            i = int(e["frame"]) - first
            x, y = (i % COLUMNS) * tile_w, (i // COLUMNS) * tile_h
            colour = COLOURS[e["event_type"]]
            for k in range(3):
                draw.rectangle([x + k, y + k, x + tile_w - 1 - k, y + tile_h - 1 - k], outline=colour)
            draw.text((x + tile_w - 70, y + 2), f"{SHORT[e['event_type']]} {e['confidence'][0].upper()}", fill=colour)
        for j, line in enumerate(footer):
            draw.text((6, base.height + 4 + 18 * j), line, fill=(230, 230, 230))
        out.save(args.output_dir / name)
    print(f"{len(frame)} review sheets written to {args.output_dir}")


if __name__ == "__main__":
    main()
