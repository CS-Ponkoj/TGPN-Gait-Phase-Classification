# AI Review Findings: what the author should check

Review pass `claude_ai_review_v1`, 2026-11-11. Five reviewer agents worked on this; none reviewed a batch it had annotated. They followed [`REVIEW_PROTOCOL.md`](REVIEW_PROTOCOL.md) and stayed blind to rule labels and TGPN predictions. Decisions are in [`ai_review.csv`](ai_review.csv). The original annotation rows are unchanged.

## Overall

| | accept | flag | correct | add | reject |
|---|---|---|---|---|---|
| Events (1,089 reviewed incl. unresolvable) | 973 | 76 | 15 | 13 | 1 |
| Strides (308) | 268 | 39 | — | — | 1 |
| Sequence-level notes | — | 24 | — | — | — |

- **61 of 123 sequences** have no flag, correction, addition or rejection.
- **Toe-offs held up well.** No reviewer corrected a toe-off.
- **Coverage gaps:** two reviewers (batches 1 and 2) checked each event against the clean sheets but opened only 2 and 7 of the overlay sheets.

## 1. The one systematic problem: contact timing

All 15 corrections move a contact **later**: 13 by 2 frames, 2 by 3. Flag reasons say "late" 21 times and "early" 12 times, so the error doesn't run in one direction everywhere. It clusters by subject:

| Pattern | Sequences |
|---|---|
| Contact placed at "legs just separated" instead of "front foot stops moving forward", ~2 frames early | 028:fn00 (all 5 corrected), 051:fs00, 051:fq00, 051:fb01, 051:fn01, and probably 034:fb01 |
| Contacts 1–2 frames early because flared trousers hide the heel | 029:fs00, 029:fn01 |
| Contacts 2–3 frames late | 102:fs00, with 102:fb00 mixed |

**Why it matters:** the planned comparison counts the rule's boundaries as matching when they are within ±1 frame of a human contact. A consistent 2-frame shift would change that result by itself. **Please decide on one contact definition and check it on 3 or 4 of these sequences.** The guide's definition is "front foot reaches the ground at the end of its forward swing and stops moving forward". If you confirm that definition, the corrections above stand, and the same check should be applied to the other sequences of these subjects.

## 2. Must check (about 15 sequences, roughly 30–45 minutes)

| Sequence | Issue |
|---|---|
| 028:fn00 | All 5 contacts corrected +2. Confirm the definition here first. |
| 051:fs00, 051:fq00, 051:fb01, 051:fn01 | Contacts 2–3 early. In 051:fb01, contact 74 is rejected because the foot is clipped at the frame edge; stride c03 is rejected with it. |
| 029:fs00, 029:fn01 | Flared trousers. Most contacts flagged as 1–2 early. |
| 102:fs00, 102:fb00 | Contacts possibly 2–3 late (fs00), and mixed (fb00). |
| 073:fs00, 073:fq00, 073:fb01, 073:fn03 | The annotator wrote that only one shoe was segmented, but both shoes are visible later in each sequence. 9 events were added at low confidence; please confirm or reject them. |
| 108:fs01 | In the 88→111 gap, the toe-off window 88–91 looks too early (92–95). |
| 034:fb01 | All 4 contacts possibly 1–2 early. |

## 3. Quick confirmations (5–10 minutes)

- **Additions on clean frames:** 063:fn01 contact 40, 034:fn03 contact 53, 107:fq01 contact 61, 108:fb00 contact 74.
- **Subject 053 (four sequences):** the reviewer agrees that toe-offs can't be placed. Some contacts might be placeable at low confidence from the toe tip. Decide whether to leave 053 out entirely, which is the simpler choice.
- **Missing unresolvable rows at the sequence start:** 108:fn02, 108:fq01 and 108:fb00 each have an early trailing toe-off (frames 11–14) with no row. Adding `unresolvable` rows is enough.
- **124:fn03:** a possible contact at 69–70, right at the end of the evaluable range.

## 4. No action needed

- **Corruption extents:** 110:fn00, 110:fs00, 110:fq01, 110:fb00, 115:fn00 and 124:fs00. The quality notes understate how far the corrupted frames run, but no annotated event sits on them, except possibly the edge cases in 110:fn00 (toe-off e02 at frame 27) and 110:fb00 and 124:fs00 (contacts on the first clean frame). Glance at those three.
- The remaining single flags are ±1-frame uncertainty on fragmented or ground-merged feet: 091, 095, 129, 131, 136, 142, 143, 152, 090 and others. They're listed in `ai_review.csv`, and leaving them as they are is reasonable.
- **001:fn03:** the calibration example. It's excluded from analysis by design.

## How to record your check

Add rows to `ai_review.csv`-style file `author_review.csv`, with the same header and `reviewer_id` set to your ID. Write one row per item you looked at: `accept` agrees with the AI review decision, and `correct` gives your frame. You don't need rows for items you didn't open. The comparison against the rule and TGPN will use this order: your decision, then the AI-review correction, then the original annotation.
