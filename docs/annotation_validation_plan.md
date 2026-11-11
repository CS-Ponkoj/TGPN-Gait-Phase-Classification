# Independent Annotation Validation Plan

Status: **AI-proposed held-out annotations done (2026-11-11), pending author review.** Drafted 2026-11-10. The executed pass departs from section 6: a single AI annotator, with the author reviewing in place of independent annotators and an expert. See [`annotations/validation/v1/README.md`](../annotations/validation/v1/README.md).

This plan describes new annotation work. No result below except the pilot check in section 2 exists yet, and that check is not independent evidence (see its caveats).

## 1. Purpose

Current evidence only shows that models agree with the labels made by a deterministic silhouette rule (`v0.1-ai`). It does not show whether those labels match real gait events. This study gives a human reference that does not come from the rule. Against that reference it measures:

1. how closely the rule's labels and boundaries match human-observed gait events, and
2. how closely the saved TGPN held-out predictions match those same events.

The study needs no retraining and no new inference. The rule's output (`annotations/provisional/v0.1-ai/`) and the final run's predictions (`artifacts/runs/20260909T080845Z-tgpn-6f11c288/predictions.csv`) are already fixed.

## 2. What the existing pilot already suggests

The pilot snapshot `annotations/reviewed/pilot_v3_user_confirmed_v1/` has 19 candidate cycles from 15 development sequences:

| Decision | Cycles | Main reason recorded |
|---|---|---|
| Excluded | 9 | Fragmented or detached shins and feet, so foot support can't be defended |
| On hold | 6 | Legs merge at crossover, so the same foot can't be followed |
| Accepted, low confidence | 4 (111 frames) | AI-assisted proposal confirmed in chat, not independently annotated |

Two observations from the 4 accepted cycles shape this plan:

- **The rule's interval is a step, not a stride.** Each accepted same-foot cycle lasts 25–34 frames. It spans exactly two consecutive rule intervals (`step_###` rows in `cycle_boundaries.csv.gz`), which last 12–18 frames each. For example, in `casia_c:044:fs01` the stride runs 57→91 and the rule's steps are 57→75 and 75→91. So the rule labels P0–P3 twice per stride, while the protocol's four phases happen once per stride.
- **On those 111 frames, the rule's labels match the same-foot labels for only 34 frames (30.6%).** The four classes are fairly balanced, so chance agreement would be around 25%.

Caveats: four cycles, all low confidence, AI-assisted, not independently annotated. Their start and end frames also equal the rule's boundaries exactly, which points to anchoring on the rule (the pilot notes themselves warn against copying Pass A). Treat this as a reason to run the study, not as a result to report.

## 3. Questions and pre-specified hypotheses

| ID | Question | Reference used |
|---|---|---|
| V1 | Do the rule's interval boundaries land on human-observed step events? | Track S |
| V2 | Do the rule's P0–P3 states match same-foot stride phases? | Track F |
| V3 | How do the saved TGPN predictions compare with the rule against the same human reference? | Tracks S and F |
| V4 | How often can a human annotate these silhouettes at all, and does it vary by condition? | Annotation yield |

Expected direction, based on section 2: high agreement on V1, near-chance agreement on V2. The study is designed to give an informative answer whichever way it comes out.

## 4. Two reference tracks

The pilot showed that following the same foot across a stride usually fails on these silhouettes. A single stride-level track would therefore produce little data. The plan uses two tracks, and every candidate sequence goes through both.

### Track S: step events (no foot identity needed)

For each complete step, annotators mark two events:

- **Contact (C):** the first frame where the leading foot touches the ground.
- **Opposite toe-off (T):** the first frame where the trailing foot leaves the ground.

The frames from C up to T are double support. The frames from T up to the next C are single support. Annotators never need to say which foot is which across steps. Every event can be marked `unresolvable` instead of guessed.

Comparison with the rule: its interval starts are compared with C events. Its states are compared through a mapping fixed in advance (section 7.2).

### Track F: same-foot stride phases (existing protocol)

Use `docs/annotation_protocol.md` without changes: five ordered boundaries per stride, `high`, `medium` or `low` confidence, and exclusion when the same foot can't be followed. This track is only attempted on sequences where the annotator judges the reference foot trackable. Low yield is expected and will be reported (V4).

## 5. Sampling

### 5.1 Held-out evaluation set

- **Population:** the 31 held-out subjects. The final TGPN run already has predictions for them, and no model will be fitted or selected after this point.
- **Draw:** for each subject, one sequence per condition family (`fn`, `fs`, `fq`, `fb`). That gives 124 sequences. `fn` has four sequences per subject; pick one with a fixed seed. Use only sequences that have retained (`medium`) rule labels. Record the draw in `annotations/validation/v1/sampling_frame.csv`, and record its SHA-256 before anyone opens a frame.
- **Size:** held-out sequences have median lengths of 51 (`fq`) to 87 (`fs`) frames, and the rule's median step is 12–15 frames. That gives about 3–6 steps and 1–3 strides per sequence. Expected candidates:
  - Track S: about 500 steps.
  - Track F: about 200–250 strides. At the pilot's yield (4 of 19, about 21%), that leaves roughly 40–50 accepted strides. Track F is therefore a secondary analysis.
- **Fallback:** if Track S yield after exclusions falls below 15 subjects with at least one usable step in every family, report the family results as descriptive only.

### 5.2 Development calibration set (never used for evaluation)

- The 19 pilot cycles, re-annotated from scratch. Annotators must not see the AI proposals or the rule's labels.
- Plus 20 strides from 10 other development subjects, spread across all four families.

## 6. People and procedure

| Role | Who | Responsibility |
|---|---|---|
| Annotator A | _TBD by author_ | Independent Track S and Track F labels |
| Annotator B | _TBD by author_ | Independent Track S and Track F labels |
| Gait-domain expert | _TBD by author_ | Adjudicates disagreements and low-confidence items, and approves the frozen guide |
| Analyst | Author | Runs the frozen analysis script and never edits labels |

The person who designed the rule or TGPN should not serve as Annotator A or B.

### 6.1 Blinding and anchoring controls

- The annotation tool shows only the raw silhouette frames (`data/raw/casia_c/...`) and source frame numbers.
- Annotators never see rule labels, rule intervals, TGPN predictions, pilot proposals, or each other's work.
- Present sequences in a shuffled order that mixes subjects and families.
- No AI-proposed boundaries anywhere in the primary set. The pilot showed that proposals carry over into the "confirmed" labels.

### 6.2 Steps

1. **Freeze the analysis before anyone looks.** Commit this plan, the sampling frame and its hash, and `scripts/validation_analysis.py` (section 7) with tests on synthetic data. Tag the commit `validation-v1-prereg`.
2. **Calibrate on development data.** Both annotators label the calibration set. Gates: Track F weighted kappa ≥ 0.80 (the protocol's existing gate), and Track S inter-annotator event F1 ≥ 0.90 within ±1 frame (proposed here). If a gate fails, revise the guide's visual rules, raise the guide version, and repeat on fresh calibration strides. Never reuse the held-out set for calibration.
3. **Freeze the guide.** Record the guide version and hash in `annotations/validation/v1/README.md`.
4. **Annotate the held-out set.** Annotators A and B work independently on all 124 sequences in both tracks.
5. **Adjudicate.** The expert reviews every disagreement larger than 1 frame and every `low` or `unresolvable` item. Keep both original rows and add a versioned adjudication row, following the protocol's existing adjudication rules.
6. **Analyze.** Run the frozen script once on the adjudicated labels, the rule's labels and `predictions.csv`. Report every pre-specified output, whatever the outcome.

## 7. Analysis (frozen before held-out annotation)

### 7.1 Agreement between the two annotators (reported first)

- Track S: event F1 at 0, ±1 and ±2 frames, and matched mean absolute error (MAE) in frames.
- Track F: weighted kappa, raw frame agreement, and mean boundary error. Existing code: `gait-phase annotation-report ... --fps <rate>`. Confirm the CASIA C frame rate from the dataset documentation before converting frames to milliseconds.

### 7.2 Rule and TGPN against the adjudicated reference

| Track | Metric | Rule | TGPN |
|---|---|---|---|
| S | Event F1 at 0/±1/±2 frames: rule interval starts vs human C events | ✓ | ✓, using state transitions into P0 |
| S | Matched MAE (frames) | ✓ | ✓ |
| S | Two-state agreement (double vs single support) with Cohen's kappa. Mapping fixed in advance: P0 → double support, P1–P3 → single support | ✓ | ✓ |
| S | Rule interval length ÷ human step length (expected ≈ 1) | ✓ | — |
| F | Four-state subject-macro F1 and weighted kappa, mapping P0–P3 directly onto the protocol's phases | ✓ | ✓ |
| F | Same as above after folding each stride into its two rule steps (tests whether the rule is tracking steps) | ✓ | ✓ |
| F | Rule interval length ÷ human stride length (expected ≈ 0.5) | ✓ | — |
| Both | Paired difference, TGPN minus rule, on each metric | — | ✓ |

- **Event matching:** reuse the existing one-to-one event matcher (maximum matches, then minimum total distance) unchanged, so the event results are comparable with the existing boundary-event analysis.
- **Uncertainty:** 95% intervals from 2,000 subject-cluster bootstrap resamples. Use the same subject-macro convention as the existing analysis. Add a per-family breakdown, reported as descriptive only.
- **Coverage:** report how many candidate steps and strides are annotated, excluded or unresolvable, by family. Report the rule's own confidence for excluded items, so readers can judge selection bias. Agreement is computed only on annotated items, and any report must say so.

### 7.3 Decision rules (pre-specified)

The rules use the lower end of each 95% interval. The thresholds are proposals, to be confirmed with the expert before step 1 of section 6.2.

| Outcome | Condition | Interpretation |
|---|---|---|
| **Rule tracks steps** | Track S rule event F1 at ±1 frame has lower bound ≥ 0.80 | P0–P3 are step-phase states with validated step-event timing. TGPN's held-out results gain a meaning beyond agreeing with the rule. |
| **Rule doesn't track stride phases** | Track F rule weighted kappa has upper bound < 0.40 | Silhouette-spread labels run at step period and can't represent same-foot stance and swing. The anatomical phase names (P0 "initial contact/loading" and so on) should be treated as historical names only. |
| **Rule tracks stride phases** | Track F rule weighted kappa has lower bound ≥ 0.60 | Unexpected given the pilot. Semantic support for the four states. |
| **Inconclusive** | Anything else | Report the intervals as they are, and keep the "operational targets" framing. |
| **TGPN vs rule** | Paired TGPN−rule interval excludes 0 on a Track S metric | A measured difference against the human reference, in either direction. If TGPN is better, it is the first evidence that the model adds something beyond running the rule. |

## 8. Outputs and file layout

```
annotations/validation/v1/
  README.md                  guide version, roles, dates, hashes
  sampling_frame.csv         124 held-out sequences + seed (hashed before annotation)
  calibration/               development-only labels and agreement reports
  track_s_events.csv         one row per event per annotator
  track_f_boundaries.csv     annotations/templates/boundaries.csv schema
  adjudication.csv           versioned adjudication rows
  results/                   frozen-script outputs (JSON + CSV)
scripts/validation_analysis.py
tests/test_validation_analysis.py
```

Proposed Track S row format: `dataset, subject_id, sequence_id, step_id, contact_frame, opposite_toe_off_frame, next_contact_frame, annotator_id, confidence, unresolvable_events, notes`.

## 9. Effort estimate (rough, to be checked during calibration)

| Item | Estimate |
|---|---|
| Annotation per annotator: about 124 sequences × both tracks | 25–40 hours, assuming 3–5 minutes per stride including Track S |
| Calibration rounds | 4–8 hours per annotator per round |
| Expert adjudication | 6–12 hours |
| Analysis script, tests and pre-registration | 1–2 days |

Calibration timing replaces these guesses before the held-out work is scheduled.

## 10. Risks

| Risk | Mitigation |
|---|---|
| Track F yield too low to analyze | Track S is the primary analysis. Report Track F yield as a finding in its own right (V4). |
| Annotators don't reach agreement because the silhouettes are fragmented | Report the inter-annotator ceiling. It also caps any model or rule claim. |
| Annotators anchor on the rule's periodic structure | Blinding (section 6.1). Compare inter-annotator agreement with rule agreement. Keep the 19-cycle pilot comparison as a sensitivity check. |
| Clean, annotatable frames are easier for the rule and the model | Coverage reporting (section 7.2), plus agreement split by the rule's confidence |
| Temptation to retune the rule or TGPN after seeing the results | Any retuned rule or model must be evaluated on newly annotated subjects, never on this set again |
| Dataset licence limits sharing labels | Release annotations only as frame indices and IDs, after checking the CASIA terms |

## 11. Decisions needed from the author

1. Names of Annotators A and B and the gait-domain expert, and confirmation that they are independent of the rule's design.
2. Whether Track F is in scope, or whether to run Track S only. Track S only is cheaper and still addresses the main reviewer objection.
3. Confirmation of the decision thresholds in section 7.3 with the expert.
4. The target venue and its deadline, which set how much calibration time is available.
