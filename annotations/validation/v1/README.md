# Validation v1: AI-proposed annotations, pending author review

Created 2026-11-11. Plan: [`docs/annotation_validation_plan.md`](../../../docs/annotation_validation_plan.md). Guide: [`ANNOTATION_GUIDE.md`](ANNOTATION_GUIDE.md) (version v1-ai-1).

## Status: NOT a reference standard yet

| Field | Value |
|---|---|
| Provenance | AI-proposed (`annotator_id = claude_ai_v1`). Claude subagents annotated the silhouette contact sheets visually, in 5 batches, using one shared guide. |
| AI second-pass review | **Done** (`ai_review.csv`, `claude_ai_review_v1`). The findings and the author's checklist are in [`REVIEW_FINDINGS.md`](REVIEW_FINDINGS.md). |
| Human review | The author approved the AI review decisions in chat on 2026-11-11, without recording item-level `author_review.csv` rows. |
| Comparison | Done. See [`results/RESULTS.md`](results/RESULTS.md). |
| Independent annotators / expert | None. This departs from plan section 6: a single AI annotator, no human calibration round, and the author's review takes the place of the expert. |
| Blinding | Annotators saw only the blinded contact sheets and the guide. They were told not to open rule labels, rule intervals, pilot labels or predictions. |
| Training or primary-evaluation eligible | No. Use only for descriptive or exploratory analysis until the review is complete, and describe it as AI-assisted wherever it is reported. |

## Population

`sampling_frame.csv` holds 123 held-out sequences: 31 subjects × {fn, fq, fb}, plus `fs` for 30 subjects. One subject has no retained slow sequence. It was drawn with seed 20261111 by `scripts/validation/make_sampling_frame.py`, which reads only sequence-level QC metadata.

- sampling_frame.csv SHA-256: `9779ce49cd41db12ddad691b8203db453f8e3f811f23f5c02a3fbbbee2e7ac40`

## Contents

| File | What it holds |
|---|---|
| `track_s_events.csv` | Step events: `contact` and `opposite_toe_off`, each either `annotated` with a frame or `unresolvable` with a window in `notes` |
| `track_f_boundaries.csv` | Same-foot strides in the five-boundary protocol schema, `annotated` or `excluded` |
| `sequence_review.csv` | One row per sequence: walking direction, counts, quality notes |
| `contact_sheets/`, `review_sheets/` | Rendered images. Local only and gitignored, because they contain licensed CASIA imagery. |

## Coverage

| | fn | fs | fq | fb | Total |
|---|---|---|---|---|---|
| Track S annotated | 231 | 258 | 202 | 229 | 920 |
| Track S unresolvable | 43 | 51 | 31 | 28 | 153 |

- Track S confidence: 430 medium, 490 low, 0 high. 28 of the 31 subjects have at least one annotated event.
- Track F: 227 strides annotated (213 low, 14 medium confidence) and 83 excluded.
- Medians of the annotated timing:
  - Contact-to-contact: 13 (fn), 15 (fs), 12 (fq) and 13 (fb) frames.
  - Double support: 3–4 frames.

## Known limitations (read before reviewing)

1. **Track F terminal stance is a placeholder.** No annotator could see heel rise at this resolution. Almost every `terminal_stance_frame` is the guide's fallback, the next contact (k+1). So Track F is largely Track S events reassembled by alternation. Don't treat its P2 boundary as observed.
2. **Batches differ in how cautious they were.** Unresolvable rates by batch: 0.00, 0.29, 0.16, 0.15, 0.12. Batch 0 (the first 25 sequences, subjects 001, 020, 021, 026, 028, 029 and part of 033) marked nothing unresolvable, so it probably over-annotated. Review it most strictly.
3. **Some events were placed by timing, not visible feet.** This happened for wide-trouser subjects such as 090. Such events can copy the gait's periodicity, which is the same structure the label rule uses.
4. **The crops follow the body.** The sheets centre each frame on the silhouette, so a foot stopping relative to the ground can't be seen directly. Contact was judged from limb configuration and the dashed ground line. That line sits a few pixels below the feet in some sequences.
5. **The calibration sequence is not independent.** `casia_c:001:fn03` was given to the annotators as a worked example. Its events reproduce that example exactly. Exclude it from any agreement analysis.
6. **Some subjects couldn't be annotated.** Subjects 053 and 066 (feet missing, long coat) have no annotated events. Segmentation artifacts (inverted blocks, empty frames) affect 110, 115, 124 and 152.

## Review priorities

Sequences where annotated events are unusually far apart or don't alternate. Usually an unresolvable event sits between them, but check:

`091:fn02, 091:fq00, 091:fb00, 095:fn02, 095:fs01, 095:fq01, 095:fb00, 108:fs01, 108:fb00, 110:fs00, 115:fs01, 115:fq00, 115:fb00, 124:fn03, 136:fs00, 142:fn02, 142:fs00, 142:fb00, 152:fn01, 152:fs00, 152:fb00`

## How to review

1. Regenerate the sheets if they're missing:
   ```powershell
   .\.venv\Scripts\python.exe -I scripts/validation/make_contact_sheets.py --raw-root . --output-dir annotations/validation/v1/contact_sheets
   .\.venv\Scripts\python.exe -I scripts/validation/make_review_sheets.py --sheets annotations/validation/v1/contact_sheets --output-dir annotations/validation/v1/review_sheets
   ```
2. In `review_sheets/`, green boxes mark `contact` and orange boxes mark `opposite_toe_off`. The letter after the event (H/M/L) is its confidence. Unresolvable windows and Track F strides are listed under each sheet.
3. Don't edit the AI rows. Record corrections as new rows with your own `annotator_id` and a review date, following the protocol's rule of never replacing an original annotation. Then re-run `scripts/validation/merge_annotations.py`-style checks.
4. Don't compare against rule labels or TGPN predictions until the review is complete and recorded. Otherwise the review is no longer blind.
