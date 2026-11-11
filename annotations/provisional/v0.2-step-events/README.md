# v0.2 Step-Event Labels (rule-based, provisional)

These are deterministic rule-based labels, not human or clinical ground truth. Design: [`docs/step_event_labels_v0.2.md`](../../../docs/step_event_labels_v0.2.md). Validation: [`annotations/validation/v1/results/V02_RESULTS.md`](../../validation/v1/results/V02_RESULTS.md). **None of the three pre-registered validation targets was met.**

| State | Meaning |
|---|---|
| `double_support` (0) | Detected contact → detected opposite toe-off |
| `early_single_support` (1) | Toe-off → legs cross (minimum lower-limb spread) |
| `late_single_support` (2) | Legs cross → next contact |

## Files

- `frame_labels.csv.gz`: same columns as v0.1. `phase_index` is 0–2, and `cycle_position` is the progress within the step. Only frames inside complete detected steps are labeled: 72,036 of 100,330 eligible frames.
- `step_events.csv.gz`: one row per step, with the contact, toe-off, crossing and next-contact frames, their source (`ground_band` or the `spread_peak` fallback), and confidence.
- `sequence_qc.csv`: per-sequence step counts, medium-confidence steps, median step length and double-support fraction.
- `provenance.json`, `checksums.sha256`.

Confidence is `medium` when both contacts and the toe-off of a step were detected from planted feet, and `low` otherwise. Regenerate with `scripts/build_step_event_labels.py`.
