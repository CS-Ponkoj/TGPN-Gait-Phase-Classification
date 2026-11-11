# Validation v1 Results: rule and TGPN against the annotation reference

Run 2026-11-11 with `scripts/validation/compare_reference.py`. The numbers come from [`comparison.json`](comparison.json). The plan is [`docs/annotation_validation_plan.md`](../../../../docs/annotation_validation_plan.md), section 7.

## What the reference is

- **Provenance:** AI-proposed annotations (`claude_ai_v1`), corrected by an AI second-pass review (`claude_ai_review_v1`). On 2026-11-11 the author approved the review decisions in chat, without recording item-level rows.
- **Not independent.** It is not an independent human reference, and every result below inherits that limit.
- **Construction:**
  - Original annotations, with 15 corrected contacts, 13 added events, 1 rejected event and 1 rejected stride.
  - Strides whose corrected events broke the frame order are excluded.
  - Calibration sequence `001:fn03` is excluded.
- **Size:** 121 sequences with at least one event or stride, 29 subjects with contacts, 924 annotated events, 154 unresolvable events, and 224 annotated strides (84 excluded).
- **Exported files:** [`reference_events.csv`](reference_events.csv) and [`reference_strides.csv`](reference_strides.csv).
- **What was compared:** the rule's `v0.1-ai` medium-confidence labels and interval starts, and the saved final TGPN held-out predictions (`20260909T080845Z-tgpn-6f11c288`). There was no retraining and no new inference.
- **Uncertainty:** 95% intervals come from 2,000 subject-cluster bootstrap resamples (seed 20261111).

## V1. Do the rule's interval starts land on step contacts? (Track S)

| Tolerance | Rule event F1 | TGPN event F1 (entries into P0) | TGPN − rule |
|---|---|---|---|
| exact | 0.190 [0.126, 0.257] | 0.190 [0.125, 0.257] | −0.000 [−0.025, 0.023] |
| ±1 frame | **0.587 [0.498, 0.680]** | 0.595 [0.496, 0.690] | 0.007 [−0.026, 0.039] |
| ±2 frames | **0.864 [0.811, 0.911]** | 0.862 [0.801, 0.914] | −0.002 [−0.023, 0.020] |

- 472 reference contacts; the rule has 454 interval starts and TGPN has 456 entries into P0 within the evaluable frames.
- **There is a systematic offset.** For the nearest predicted event within ±2 frames (predicted minus reference), the rule's offsets are: −2: 1, −1: 16, 0: 88, +1: 168, +2: 127. The mean is +1.0 frame. TGPN's are almost identical, with a mean of +1.03.
- **Period:** the rule's interval length divided by the reference step length has a median of **1.00** (IQR 1.00–1.07, n = 337). Its mean interval length divided by the reference stride has a median of **0.50** (IQR 0.48–0.52, n = 216).

**Reading.** The rule's intervals are exactly one step long, and they start 1–2 frames after the reference contact. The pre-specified test was a lower bound of at least 0.80 on event F1 at ±1 frame. It is **not met** (lower bound 0.498), so V1 is **inconclusive under the plan's rule**. At ±2 frames, the lower bound is 0.811.

The offset has two possible causes that this design can't tell apart:
- the spread maximum really occurs just after heel contact, or
- the reference contacts are still slightly early.

The review found that some subjects' contacts were placed early, and corrected the clearest cases by +2.

## V1b. Double support vs single support (Track S, two states)

| | Cohen's kappa | Frame agreement | Double-support fraction (predicted / reference) |
|---|---|---|---|
| Rule (P0 → double support) | 0.529 [0.499, 0.558] | 0.817 | 0.174 / 0.330 |
| TGPN (P0 → double support) | 0.552 [0.517, 0.587] | 0.825 | 0.180 / 0.330 |

5,002 frames. P0 covers about half as many frames as the reference double support. That's expected: P0 is the first 12% of the step interval, and the reference double support (contact to opposite toe-off, a median of 3–4 frames) is about 33%.

## V2. Do P0–P3 match same-foot stride phases? (Track F)

| | Subject-macro F1 | Weighted kappa (linear) | Frame agreement |
|---|---|---|---|
| Rule | 0.271 [0.263, 0.279] | **0.098 [0.086, 0.110]** | 0.272 |
| TGPN | 0.277 [0.267, 0.286] | 0.102 [0.088, 0.116] | 0.279 |

The comparison covers 4,380 frames from 28 subjects. Rule confusion matrix (rows: reference P0–P3; columns: rule P0–P3):

```
P0  414  156    5  291
P1   36  446  932  722
P2  190   54    0  129
P3   23  228  421  333
```

**Reading.** The pre-specified test was "upper bound of the rule's weighted kappa below 0.40". It is **met**: the upper bound is 0.110. Agreement is close to chance (four balanced classes give 0.25). The period result explains why: the rule runs P0→P3 once per step, and the stride phases run once per two steps.

Caveat: the reference's P2 start (terminal stance) is a placeholder, the next contact, because heel rise couldn't be seen. That moves frames between the reference's P1 and P2. It can't account for near-chance agreement across all four states, since the period mismatch alone produces that.

## V3. TGPN compared with the rule

Paired TGPN-minus-rule differences:

| Metric | Difference [95% CI] |
|---|---|
| Event F1, ±1 frame | 0.007 [−0.026, 0.039] |
| Event F1, ±2 frames | −0.002 [−0.023, 0.020] |
| Two-state kappa | **0.023 [0.007, 0.043]** |
| Four-state weighted kappa | 0.004 [−0.002, 0.011] |

**TGPN reproduces the rule's event timing and stride agreement.** The one exception is the two-state (double vs single support) kappa, where TGPN is slightly higher, and the interval excludes 0. That difference is small next to the gap to the reference (about 0.53–0.55 kappa). This corrects an earlier version of this file, which said every interval included 0 when only the event intervals had been computed.

## Decisions under plan section 7.3

| Outcome | Result |
|---|---|
| Rule tracks steps (±1 F1 lower bound ≥ 0.80) | Not met (0.498). The rule is step-periodic (ratio 1.00) and within ±2 frames (F1 0.864), with a +1-frame mean lag. |
| Rule doesn't track stride phases (kappa upper bound < 0.40) | **Met** (0.110) |
| Rule tracks stride phases (kappa lower bound ≥ 0.60) | Not met |
| TGPN vs rule differs | Only on two-state kappa, +0.023 [0.007, 0.043]. The event F1 and stride kappa intervals include 0. |

The plan marked these thresholds as proposals to confirm with an expert. They were applied as written, without that confirmation.

## Interpretation

1. **P0–P3 are not same-foot stride phases.** Against same-foot stride phases, the rule and TGPN are at chance (weighted kappa about 0.10). The labels repeat every step, not every stride, so they are best described as step-interval states.
2. **The rule's intervals do correspond to steps.** The period matches exactly, and boundaries fall within about 2 frames of contact, with a consistent lag of about 1 frame.
3. **TGPN's held-out score mainly measures agreement with the rule.** Against this reference it matches the rule on event timing and stride agreement, and is only slightly higher on double-support agreement.
4. **Evidence level.** The reference is AI-annotated, AI-reviewed and author-approved, not an independent human reference. The period and chance-level stride results are large effects and should survive that limitation. The ±1-frame timing result is sensitive to a 1–2 frame annotation bias, so it should not be over-interpreted.
