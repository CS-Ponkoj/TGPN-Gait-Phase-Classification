# Step-Event Labels v0.2: Design and Pre-Registered Validation

Status: **design frozen 2026-11-11, before any v0.2 output was compared with the held-out reference.** Design checks used development subjects only.

## Why v0.2

The v0.1 labels apply stride-phase percentages (0.12 / 0.31 / 0.62) to one step. They repeat P0–P3 every step, and agree with same-foot stride phases only at chance level (weighted kappa 0.098; see `annotations/validation/v1/results/RESULTS.md`). Binary side-view silhouettes can't tell the two legs apart, so stride phases of a specific leg are not observable.

v0.2 instead labels states of the step that the silhouettes can show. It detects them from events, not fixed fractions.

## States

| Index | Label | From → to | Visible cue |
|---|---|---|---|
| 0 | `double_support` | contact → opposite toe-off | Both feet touch the ground |
| 1 | `early_single_support` | opposite toe-off → legs cross | One foot down; the other leg swings from behind |
| 2 | `late_single_support` | legs cross → next contact | One foot down; the swinging leg is ahead, before landing |

## Detection rules (frozen)

For each frame (foreground = nonzero pixels, as in v0.1):

1. **Spread signal and step anchors.** Same lower-limb spread and peak detector as v0.1 (`detect_contact_peaks`, prominence 0.015, separation 7). The peaks anchor steps; *m* = median peak interval.
2. **Ground line.** *L_t* is the lowest foreground row. The ground row is *G_t* = max of *L* over frames *t*−6…*t*+6, which tolerates slow drift in the camera geometry.
3. **Feet on the ground.** The band is rows *G_t*−*b*…*G_t*, with *b* = max(3, round(0.04 × median body height)). Foreground columns in the band form runs. Runs separated by at most *g* = max(2, round(0.04 × median body height)) empty columns are merged. Runs at least 2 px wide count as feet. *n_t* = number of feet.
4. **Contact and toe-off.** A double-support run is consecutive frames with *n_t* ≥ 2. For each spread peak *p*, take the double-support run that intersects *p*−4…*p*+3 and is closest to *p*. Contact = its first frame; opposite toe-off = the frame after its last frame. The run must last 1 to 0.6*m* frames. If no valid run exists, contact falls back to *p*, and the step has no toe-off and is low confidence.
5. **Legs cross.** The frame of minimum smoothed spread strictly between toe-off and the next contact. Without a toe-off, the search window starts at contact + 0.25 × step length.
6. **Steps.** Consecutive contacts with a step length between 0.5*m* and 1.6*m*. Only frames inside complete steps are labeled; edge frames are excluded with a reason.
7. **Confidence.** `medium` when both bounding contacts and the toe-off were detected from the ground band. Otherwise `low`.

## Pre-registered validation (run once on the held-out reference)

Reference: `annotations/validation/v1/results/reference_events.csv`. It is AI-assisted, and `casia_c:001:fn03` is excluded. Matching uses the same one-to-one procedure and 2,000 subject-cluster bootstrap resamples as the v0.1 comparison. Reference frames outside v0.2's labeled region count against v0.2.

| ID | Measure | Target |
|---|---|---|
| E1 (primary) | Contact event F1 within ±1 frame | 95% lower bound ≥ 0.80 (v0.1: 0.587 [0.498, 0.680]) |
| E2 | Opposite toe-off event F1 within ±1 frame | 95% lower bound ≥ 0.70 (v0.1 has no toe-off event) |
| E3 | Double vs single support, Cohen's kappa | Paired v0.2 − v0.1 difference with lower bound > 0 (v0.1: 0.529) |
| E4 (descriptive) | Step period ratio, signed contact offset, coverage of reference events | Reported, no target |

The legs-cross boundary has no reference events, so the split between early and late single support remains **unvalidated**. If E1 or E2 fails, v0.2 is reported as failing that target. Parameters will not be retuned on the held-out reference. Any retuned version must be validated on newly annotated subjects.
