# Validation v1 Review Protocol (AI second pass)

A reviewer who did not annotate the batch checks every AI-proposed annotation against the silhouettes. The review's job is to catch errors and to point the author to the items that need a human eye. Its decisions don't replace the author's review.

## Inputs

- Review sheets: `annotations/validation/v1/review_sheets/<sequence>.png`. Green boxes mark `contact`, orange boxes `opposite_toe_off`, and H/M/L is the confidence. The footer lists unresolvable windows and Track F strides.
- Clean sheets, without overlays: `annotations/validation/v1/contact_sheets/<sequence>.png`. Look at these first when judging a frame, so the boxes don't anchor you.
- `track_s_events.csv`, `track_f_boundaries.csv`, `sequence_review.csv` and `ANNOTATION_GUIDE.md` in the same folder.

Blinding: don't open rule labels (`annotations/provisional/`), pilot labels (`annotations/reviewed/`), anything under `artifacts/`, or any predictions file.

## What to check per sequence

1. Walking direction.
2. Every annotated event. Is the frame within ±1 of where you would put it? Does the event type fit the image: front foot landing for `contact`, rear foot leaving the ground for `opposite_toe_off`?
3. Every unresolvable event. Could it in fact be placed, or is its window wrong?
4. Missing events: a clear contact or toe-off inside the evaluable range ([first+2, last−2]) that has no row at all.
5. Each Track F stride. Are its contact and toe-off frames consistent with the Track S events? Is the same foot plausibly kept through alternation?

## Decisions

| decision | When |
|---|---|
| `accept` | You agree within ±1 frame |
| `correct` | You are confident the frame is off by 2 or more, or the event type is wrong. Give `proposed_frame`. |
| `flag` | You are unsure, or it needs a human eye. Explain why. |
| `reject` | The event or stride shouldn't exist: it isn't defensible, or it was placed by timing alone |
| `add` | A clearly visible event is missing. Give `proposed_frame` and the event type in `reason`. |

## Output

`ai_review.csv`, with this header:

`sequence_id,item_type,item_id,decision,original_frame,proposed_frame,reason,reviewer_id`

- `item_type`: `event`, `stride` or `sequence`
- `item_id`: the `event_id`, the `cycle_id`, or `-` for the sequence
- One row per existing event and stride. Add a `sequence` row only to flag a sequence-wide problem. Add rows for missing events with item_id `new01`, `new02`, …
- `reviewer_id`: `claude_ai_review_v1`

Be calibrated. Accepting is fine when the annotation is right. Flag honestly when the silhouettes don't allow a ±1-frame judgment.
