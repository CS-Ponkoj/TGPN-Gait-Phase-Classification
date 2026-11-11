# v0.2 Step-Event Labels: Pre-Registered Validation Results

Run once on 2026-11-11 with `scripts/validation/compare_v02.py`, committed as `5d18ab8` before it was run. The design and targets are in [`docs/step_event_labels_v0.2.md`](../../../../docs/step_event_labels_v0.2.md): frozen at `1aeb8fc`, with amendment A1 at `b26f848`, both before this comparison. The numbers come from [`v02_comparison.json`](v02_comparison.json).

The reference is the same AI-assisted held-out reference used for v0.1: 121 sequences and 29 subjects, excluding `001:fn03`. Intervals come from 2,000 subject-cluster bootstrap resamples (seed 20261112).

## Verdict: none of the three targets is met

| ID | Measure | v0.2 | Target | Met? | v0.1 for context |
|---|---|---|---|---|---|
| E1 | Contact F1 within ±1 frame | 0.758 [0.674, 0.831] | lower bound ≥ 0.80 | **No** | 0.587 [0.498, 0.680] |
| E2 | Opposite toe-off F1 within ±1 frame | 0.511 [0.416, 0.601] | lower bound ≥ 0.70 | **No** | (no toe-off event) |
| E3 | Double/single support kappa, v0.2 − v0.1 | +0.011 [−0.050, 0.070] | lower bound > 0 | **No** | — |

## Detail

**Contacts** (472 reference, 452 v0.2):

| Tolerance | v0.2 F1 | Matched | v0.1 F1 |
|---|---|---|---|
| exact | 0.314 [0.249, 0.376] | 145 | 0.190 |
| ±1 | 0.758 [0.674, 0.831] | 350 | 0.587 |
| ±2 | 0.918 [0.879, 0.952] | 424 | 0.864 |

The mean signed offset is +0.50 frames (v0.1: +1.01). The point estimates are better at every tolerance. That comparison wasn't pre-registered as a paired test, so the overlapping intervals shouldn't be read as a demonstrated difference.

**Toe-offs** (452 reference, 291 v0.2): F1 0.213 exact, 0.511 at ±1, 0.654 at ±2.
- v0.2 places a toe-off in only 291 steps. Low-confidence steps have none, which hurts recall.
- Where it does place one, it is early by a mean of −0.70 frames.

**Two-state frames** (4,597 frames shared by the reference, v0.2 and v0.1 medium labels):
- Kappa: v0.2 0.541 [0.486, 0.599], v0.1 0.530 [0.496, 0.566].
- Double-support fraction: reference 0.294, v0.2 0.166, v0.1 P0 0.152.

**Descriptive:**
- v0.2 step length divided by reference step length: median 1.00 (IQR 0.93–1.08, n = 333).
- 462 of 472 reference contacts fall inside v0.2 steps.
- 65% of v0.2 steps in these sequences are medium confidence.

## Reading

1. **Contact timing improved, but not enough.** v0.2 contacts are closer to the reference than v0.1 interval starts: offset +0.5 vs +1.0 frames, and F1 0.758 vs 0.587 at ±1. The ±1 target still fails.
2. **Toe-off detection is the weak part.** It is missing for about a third of steps and tends to fire early. The early bias suggests that the planted-foot test counts a heel-rising rear foot as already moving. That's a hypothesis from these results; it hasn't been checked on development data.
3. **v0.2's double support is shorter than the reference's** (17% vs 29%). The reference itself has a known early-contact bias in some subjects, which lengthens its double support. So part of this gap may sit in the reference, not in v0.2. This design can't separate the two.
4. **Coverage dropped.** v0.2 labels 72,036 of 100,330 eligible CASIA C frames (v0.1: 98,013 medium-confidence). Frames outside complete detected steps stay unlabeled.

## What this means for using v0.2

- **What v0.2 does better:** it names states that silhouettes can show, and its step events come from observed foot behavior, not fixed fractions. It does not pass its own pre-registered accuracy targets, so it shouldn't be described as validated.
- **No retuning on this reference.** As pre-registered, v0.2 is not retuned on these results. A v0.3 (for example, toe-off from the rear foot's toe position instead of the whole foot, or a fallback toe-off for low-confidence steps) would need tuning on development data and validation on **newly annotated held-out subjects**. This reference is now used up for v0.2-family tuning.
- **Retraining on v0.2 needs code changes.** It means 3 instead of 4 states, and the label vocabulary, class count and data preparation currently assume v0.1's four states.
