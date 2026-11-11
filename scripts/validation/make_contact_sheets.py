"""Render blinded lower-limb contact sheets for annotation.

Each sheet tiles every frame of one sequence, cropped to the lower body, with only the source
frame number printed. A dashed line marks the sequence ground level (95th percentile of the
silhouette's lowest row). No rule labels, intervals, or predictions are drawn.

Sheets contain licensed CASIA imagery: write them outside the repository and never commit them.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

COLUMNS = 8
SCALE = 1.5
CROP_WIDTH = 150


def load(folder: Path, frame: int) -> np.ndarray:
    return np.asarray(Image.open(folder / f"{frame:03d}.png").convert("L")) > 127


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sampling-frame", type=Path, default=Path("annotations/validation/v1/sampling_frame.csv"))
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--only", nargs="*", default=None, help="Optional sequence_ids to render")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with args.sampling_frame.open(newline="") as handle:
        sequences = list(csv.DictReader(handle))
    for seq in sequences:
        if args.only and seq["sequence_id"] not in args.only:
            continue
        number = seq["subject_id"].split(":")[1]
        folder = args.raw_root / "data" / "raw" / "casia_c" / number / number / seq["condition"]
        frames = list(range(int(seq["first_frame"]), int(seq["last_frame"]) + 1))
        masks = [load(folder, f) for f in frames]

        tops, bottoms = [], []
        for m in masks:
            rows = np.flatnonzero(m.any(axis=1))
            if rows.size:
                tops.append(rows[0])
                bottoms.append(rows[-1])
        top = int(np.median(tops)) if tops else 0
        ground = int(np.percentile(bottoms, 95)) if bottoms else masks[0].shape[0] - 1
        band_top = top + int(0.45 * (ground - top))  # roughly hip level down to the ground
        band_bottom = min(masks[0].shape[0], ground + 8)
        band_h = band_bottom - band_top

        tile_w, tile_h = int(CROP_WIDTH * SCALE), int(band_h * SCALE) + 16
        rows_n = (len(frames) + COLUMNS - 1) // COLUMNS
        sheet = Image.new("L", (COLUMNS * tile_w, rows_n * tile_h), 40)
        draw = ImageDraw.Draw(sheet)
        for i, (frame, m) in enumerate(zip(frames, masks)):
            band = m[band_top:band_bottom]
            cols = np.flatnonzero(band.any(axis=0))
            centre = int(cols.mean()) if cols.size else band.shape[1] // 2
            left = max(0, min(band.shape[1] - CROP_WIDTH, centre - CROP_WIDTH // 2))
            crop = Image.fromarray((band[:, left : left + CROP_WIDTH] * 255).astype(np.uint8))
            crop = crop.resize((tile_w, int(band_h * SCALE)), Image.NEAREST)
            x, y = (i % COLUMNS) * tile_w, (i // COLUMNS) * tile_h
            sheet.paste(crop, (x, y + 16))
            gy = y + 16 + int((ground - band_top) * SCALE)
            for gx in range(x, x + tile_w, 6):
                draw.line([(gx, gy), (gx + 2, gy)], fill=140)
            draw.rectangle([x, y, x + tile_w - 1, y + tile_h - 1], outline=90)
            draw.text((x + 4, y + 2), f"{frame}", fill=255)
        name = seq["sequence_id"].replace(":", "_") + ".png"
        sheet.save(args.output_dir / name)
        print(name, len(frames), sheet.size)


if __name__ == "__main__":
    main()
