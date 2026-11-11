# Validation v1 Annotation Guide (AI pass)

Version: v1-ai-1. Used for the AI-proposed annotation pass described in `README.md`.

## What you see

One contact sheet per sequence, rendered by `scripts/validation/make_contact_sheets.py`:

- Every source frame, in order, cropped from roughly hip level to the ground.
- The source frame number, top left of each tile.
- A dashed line at the sequence's ground level (95th percentile of the silhouette's lowest row).

The sheets show no rule labels, rule intervals or model predictions. While annotating, do not open anything under `annotations/provisional/`, `annotations/reviewed/` or `artifacts/`, or any predictions file.

Figure out the walking direction first. Toes point the way the subject walks.

## Track S: step events (no foot identity needed)

Record every event whose frame you can place within about ±1 frame:

- **contact**: the first frame where the leading (front) foot reaches the ground line at the end of its forward swing. After this frame the front foot stops moving forward relative to the ground.
- **opposite_toe_off**: the first frame where the trailing (rear) foot's lowest point is clearly above the ground line, meaning its toe has left the ground.

In normal walking they alternate: contact → opposite_toe_off → contact → … A step usually lasts 10–20 frames, and double support (contact → opposite_toe_off) is usually 2–6 frames.

If the sequence clearly contains an event but the silhouette can't place it (fragmented or missing foot, feet merged, the foot at the sheet's edge, the subject entering or leaving), record it as `unresolvable`. Give the best window you can in `notes`, for example `window 63-66`. Never guess a frame.

Don't record events in the first or last 2 frames, because the context before or after is missing.

Confidence:
- `high`: unambiguous, ±0 to 1 frame
- `medium`: placeable within ±1 to 2 frames
- `low`: placeable, but only within ±2 to 3 frames

## Track F: same-foot strides (docs/annotation_protocol.md)

A stride follows one reference foot from its contact to its next contact. It is two steps long. With side-view silhouettes, cross-step foot identity comes from alternation: the foot that makes contact k makes contact k+2 again. Use alternation only if every contact and opposite_toe_off between those two contacts is resolved, not `unresolvable`.

For each stride, record five frames:
1. `initial_contact_frame`: contact k, made by the reference foot.
2. `mid_stance_frame`: the opposite toe-off right after contact k. The reference foot is now the only support.
3. `terminal_stance_frame`: the first frame of sustained heel rise of the reference foot, while it is behind the body. If heel rise can't be seen, use the frame of contact k+1, when the other foot lands, and set confidence to `low`.
4. `swing_frame`: the reference foot's toe-off. This is the opposite_toe_off right after contact k+1.
5. `next_initial_contact_frame`: contact k+2.

The frames must strictly increase. Record a stride as excluded, with a reason, when you can't defend any of the five frames. Typical reasons: an unresolved event inside the stride, a fragmented lower limb, or legs merged so that heel rise is indefensible.

## Output

Write three CSVs, with the header exactly as given:

`track_s_events.csv`
`dataset,subject_id,sequence_id,event_id,event_type,frame,status,confidence,annotator_id,notes`
- `event_id`: e01, e02, … in frame order
- `event_type`: `contact` or `opposite_toe_off`
- `status`: `annotated` or `unresolvable`. Leave `frame` empty when the status is `unresolvable`.

`track_f_boundaries.csv`
`dataset,subject_id,sequence_id,cycle_id,initial_contact_frame,mid_stance_frame,terminal_stance_frame,swing_frame,next_initial_contact_frame,status,annotator_id,confidence,notes`
- `status`: `annotated` or `excluded`. Leave the frames empty for excluded strides, except those you can defend.

`sequence_review.csv`
`sequence_id,walking_direction,frames_reviewed,track_s_annotated,track_s_unresolvable,track_f_annotated,track_f_excluded,quality_notes`

Fill `annotator_id` with the annotator's identifier (`claude_ai_v1`) and `dataset` with `casia_c`.
