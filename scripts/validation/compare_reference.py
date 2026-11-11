"""Compare the v0.1-ai rule labels and saved TGPN held-out predictions with the validation reference.

Implements docs/annotation_validation_plan.md section 7 on the AI-proposed, AI-reviewed,
author-approved reference in annotations/validation/v1.

Reference construction (precedence: author > AI review > original annotation):
  * events: `correct` moves the frame, `reject` makes the event unresolvable, `add` inserts a
    low-confidence annotated event; `accept` and `flag` keep the original row.
  * strides: `reject` excludes the stride; stride frames that equal a corrected event's original
    frame move with it; strides that stop strictly increasing are excluded.
  * casia_c:001:fn03 (calibration example) is excluded.

Outputs JSON/CSV under annotations/validation/v1/results/.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

CALIBRATION = "casia_c:001:fn03"
STATES = ["initial_contact_loading", "mid_stance", "terminal_stance_preswing", "swing"]
SEED = 20261111
ITERATIONS = 2000
TOLERANCES = (0, 1, 2)


# ---------------------------------------------------------------- matching (existing event analysis)
def match_events(truth, predicted, tolerance):
    """Ordered DP: maximum cardinality, then minimum total distance."""
    truth, predicted = sorted(truth), sorted(predicted)
    table = [[(0, 0, ()) for _ in range(len(predicted) + 1)] for _ in range(len(truth) + 1)]
    for i, true in enumerate(truth, 1):
        for j, pred in enumerate(predicted, 1):
            candidates = [table[i - 1][j], table[i][j - 1]]
            distance = abs(true - pred)
            if distance <= tolerance:
                count, cost, pairs = table[i - 1][j - 1]
                candidates.append((count + 1, cost + distance, pairs + ((i - 1, j - 1),)))
            table[i][j] = min(candidates, key=lambda item: (-item[0], item[1], item[2]))
    count, cost, pairs = table[-1][-1]
    return {"matched": count, "errors": [abs(truth[i] - predicted[j]) for i, j in pairs]}


# ---------------------------------------------------------------- reference
def build_reference(vdir: Path):
    rows = lambda name: list(csv.DictReader((vdir / name).open(newline="", encoding="utf-8-sig")))
    events = [dict(e) for e in rows("track_s_events.csv") if e["sequence_id"] != CALIBRATION]
    strides = [dict(s) for s in rows("track_f_boundaries.csv") if s["sequence_id"] != CALIBRATION]
    reviews = rows("ai_review.csv")
    author = vdir / "author_review.csv"
    if author.exists():  # author rows override AI review rows for the same item
        merged = {(r["sequence_id"], r["item_type"], r["item_id"]): r for r in reviews}
        for r in rows("author_review.csv"):
            merged[(r["sequence_id"], r["item_type"], r["item_id"])] = r
        reviews = list(merged.values())

    ev_index = {(e["sequence_id"], e["event_id"]): e for e in events}
    moved = defaultdict(dict)  # sequence -> {original frame: new frame}
    for r in reviews:
        if r["sequence_id"] == CALIBRATION:
            continue
        key = (r["sequence_id"], r["item_id"])
        if r["item_type"] == "event" and r["decision"] == "correct":
            e = ev_index[key]
            moved[r["sequence_id"]][int(e["frame"])] = int(r["proposed_frame"])
            e["frame"] = r["proposed_frame"]
        elif r["item_type"] == "event" and r["decision"] == "reject":
            e = ev_index[key]
            e.update(status="unresolvable", notes=f"rejected in review; was {e['frame']}", frame="")
        elif r["item_type"] == "event" and r["decision"] == "add":
            kind = "opposite_toe_off" if r["reason"].lower().startswith("opposite_toe_off") else "contact"
            subject = ":".join(r["sequence_id"].split(":")[:2])
            events.append({"dataset": "casia_c", "subject_id": subject, "sequence_id": r["sequence_id"],
                           "event_id": r["item_id"], "event_type": kind, "frame": r["proposed_frame"],
                           "status": "annotated", "confidence": "low", "annotator_id": r["reviewer_id"],
                           "notes": "added in review"})
        elif r["item_type"] == "stride" and r["decision"] == "reject":
            for s in strides:
                if (s["sequence_id"], s["cycle_id"]) == key:
                    s["status"] = "excluded"

    cols = ["initial_contact_frame", "mid_stance_frame", "terminal_stance_frame", "swing_frame",
            "next_initial_contact_frame"]
    for s in strides:
        if s["status"] != "annotated":
            continue
        shift = moved.get(s["sequence_id"], {})
        values = [shift.get(int(s[c]), int(s[c])) for c in cols]
        if any(a >= b for a, b in zip(values, values[1:])):
            s["status"] = "excluded"
            continue
        for c, v in zip(cols, values):
            s[c] = str(v)
    events.sort(key=lambda e: (e["sequence_id"], int(e["frame"]) if e["frame"] else 10**6, e["event_id"]))
    return events, strides


def ordered_events(events):
    """Per sequence: list of (frame or None, type, status) in temporal order.

    Unresolvable events have no frame; they are placed by their original event_id order
    relative to annotated events (event ids are assigned in frame order)."""
    by = defaultdict(list)
    for e in events:
        by[e["sequence_id"]].append(e)
    out = {}
    for seq, es in by.items():
        orig = sorted([e for e in es if not e["event_id"].startswith("new")], key=lambda e: e["event_id"])
        added = [e for e in es if e["event_id"].startswith("new")]
        seqlist = [(int(e["frame"]) if e["status"] == "annotated" else None, e["event_type"], e["status"])
                   for e in orig]
        for e in added:  # insert added events by frame among annotated neighbours
            f = int(e["frame"])
            pos = len(seqlist)
            for i, (g, _, st) in enumerate(seqlist):
                if g is not None and g > f:
                    pos = i
                    break
            seqlist.insert(pos, (f, e["event_type"], "annotated"))
        out[seq] = seqlist
    return out


def evaluable_mask(seqlist, margin=2):
    """Frames where the reference is complete: from first to last annotated event (+-margin),
    minus the open interior of any gap that contains an unresolvable event."""
    annotated = [(i, f) for i, (f, _, _) in enumerate(seqlist) if f is not None]
    if not annotated:
        return set()
    frames = set(range(annotated[0][1] - margin, annotated[-1][1] + margin + 1))
    for (i, a), (j, b) in zip(annotated, annotated[1:]):
        if any(seqlist[k][2] == "unresolvable" for k in range(i + 1, j)):
            frames -= set(range(a + 1, b))
    # leading/trailing unresolvable events shrink the margin side
    if any(st == "unresolvable" for _, _, st in seqlist[: annotated[0][0]]):
        frames -= set(range(annotated[0][1] - margin, annotated[0][1]))
    if any(st == "unresolvable" for _, _, st in seqlist[annotated[-1][0] + 1:]):
        frames -= set(range(annotated[-1][1] + 1, annotated[-1][1] + margin + 1))
    return frames


def two_state_labels(seqlist):
    """Frame -> 'DS' (contact..toe-off) or 'SS' (toe-off..contact) between consecutive annotated
    events with no unresolvable event in between."""
    labels = {}
    for i in range(len(seqlist) - 1):
        (a, ta, sa), (b, tb, sb) = seqlist[i], seqlist[i + 1]
        if a is None or b is None or ta == tb:
            continue
        for f in range(a, b):
            labels[f] = "DS" if ta == "contact" else "SS"
    return labels


def stride_labels(strides):
    out = defaultdict(dict)
    for s in strides:
        if s["status"] != "annotated":
            continue
        b = [int(s[c]) for c in ("initial_contact_frame", "mid_stance_frame", "terminal_stance_frame",
                                 "swing_frame", "next_initial_contact_frame")]
        for k in range(4):
            for f in range(b[k], b[k + 1]):
                out[s["sequence_id"]][f] = k
    return out


# ---------------------------------------------------------------- metrics
def kappa(a, b, k, weights=None):
    a, b = np.asarray(a), np.asarray(b)
    if a.size == 0:
        return float("nan")
    cm = np.zeros((k, k))
    np.add.at(cm, (a, b), 1)
    cm /= cm.sum()
    exp = np.outer(cm.sum(1), cm.sum(0))
    i, j = np.indices((k, k))
    w = np.abs(i - j) / (k - 1) if weights == "linear" else (i != j).astype(float)
    denom = (w * exp).sum()
    return float(1 - (w * cm).sum() / denom) if denom else float("nan")


def macro_f1(a, b, k):
    a, b = np.asarray(a), np.asarray(b)
    scores = []
    for c in range(k):
        tp = np.sum((a == c) & (b == c))
        denom = np.sum(a == c) + np.sum(b == c)
        scores.append(2 * tp / denom if denom else 0.0)
    return float(np.mean(scores))


def bootstrap(subjects, statistic, rng):
    subjects = sorted(subjects)
    estimate = statistic(subjects)
    draws = []
    for _ in range(ITERATIONS):
        sample = list(rng.choice(subjects, len(subjects), replace=True))
        draws.append(statistic(sample))
    draws = np.asarray(draws, dtype=float)
    draws = draws[~np.isnan(draws)]
    return {"estimate": estimate, "lower": float(np.quantile(draws, 0.025)),
            "upper": float(np.quantile(draws, 0.975)), "subjects": len(subjects)}


# ---------------------------------------------------------------- loading model/rule outputs
def load_rule(path_labels: Path, path_cycles: Path, sequences: set[str]):
    labels = {}
    with gzip.open(path_labels, "rt", newline="") as h:
        for r in csv.DictReader(h):
            if r["sequence_id"] in sequences and r["confidence"] == "medium":
                labels[(r["sequence_id"], int(r["frame_index"]))] = STATES.index(r["phase_label"])
    starts = defaultdict(set)
    intervals = defaultdict(list)
    with gzip.open(path_cycles, "rt", newline="") as h:
        for r in csv.DictReader(h):
            if r["sequence_id"] in sequences:
                a, b = int(r["contact_start_frame"]), int(r["next_contact_frame"])
                starts[r["sequence_id"]].update((a, b))
                intervals[r["sequence_id"]].append((a, b))
    return labels, starts, intervals


def load_predictions(path: Path, sequences: set[str]):
    preds = {}
    with path.open(newline="") as h:
        for r in csv.DictReader(h):
            if r["sequence_id"] in sequences:
                preds[(r["sequence_id"], int(r["frame_index"]))] = STATES.index(r["y_pred"])
    return preds


def p0_entries(states: dict[int, int]):
    """Frames where a contiguous labelling enters state 0 from another state."""
    return [f for f in sorted(states) if states[f] == 0 and (f - 1) in states and states[f - 1] != 0]


# ---------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-dir", type=Path, default=Path("annotations/validation/v1"))
    parser.add_argument("--rule-dir", type=Path, default=Path("annotations/provisional/v0.1-ai"))
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    vdir = args.validation_dir
    out = vdir / "results"
    out.mkdir(exist_ok=True)

    events, strides = build_reference(vdir)
    for name, data in (("reference_events.csv", events), ("reference_strides.csv", strides)):
        with (out / name).open("w", newline="", encoding="utf-8") as h:
            w = csv.DictWriter(h, fieldnames=list(data[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(data)

    seqs = {e["sequence_id"] for e in events} | {s["sequence_id"] for s in strides}
    subject_of = {s: ":".join(s.split(":")[:2]) for s in seqs}
    rule_lab, rule_starts, rule_int = load_rule(args.rule_dir / "frame_labels.csv.gz",
                                                args.rule_dir / "cycle_boundaries.csv.gz", seqs)
    preds = load_predictions(args.predictions, seqs)
    order = ordered_events(events)

    # ---- per-subject event counts for Track S contact matching
    ev_counts = {src: {tol: defaultdict(lambda: [0, 0, 0, []]) for tol in TOLERANCES} for src in ("rule", "tgpn")}
    ds_pairs = {src: defaultdict(list) for src in ("rule", "tgpn")}
    ratios_step = []
    for seq, sl in order.items():
        subj = subject_of[seq]
        region = evaluable_mask(sl)
        human = [f for f, t, st in sl if f is not None and t == "contact"]
        rule_c = [f for f in rule_starts.get(seq, ()) if f in region]
        tg_states = {f: s for (q, f), s in preds.items() if q == seq}
        tgpn_c = [f for f in p0_entries(tg_states) if f in region]
        for src, pred in (("rule", rule_c), ("tgpn", tgpn_c)):
            for tol in TOLERANCES:
                m = match_events(human, pred, tol)
                c = ev_counts[src][tol][subj]
                c[0] += m["matched"]; c[1] += len(human); c[2] += len(pred); c[3] += m["errors"]
        two = two_state_labels(sl)
        for f, lab in two.items():
            h = 0 if lab == "DS" else 1
            if (seq, f) in rule_lab and (seq, f) in preds:
                ds_pairs["rule"][subj].append((h, 0 if rule_lab[(seq, f)] == 0 else 1))
                ds_pairs["tgpn"][subj].append((h, 0 if preds[(seq, f)] == 0 else 1))
        annotated_contacts = [(i, f) for i, (f, t, st) in enumerate(sl) if f is not None and t == "contact"]
        for (i, a), (j, b) in zip(annotated_contacts, annotated_contacts[1:]):
            if any(sl[k][2] == "unresolvable" for k in range(i + 1, j)):
                continue
            mid = (a + b) / 2
            for x, y in rule_int.get(seq, []):
                if x <= mid < y:
                    ratios_step.append({"subject": subj, "sequence_id": seq, "human_step": b - a,
                                        "rule_interval": y - x, "ratio": (y - x) / (b - a)})
                    break

    # ---- Track F four-state
    f_lab = stride_labels(strides)
    f_pairs = {src: defaultdict(list) for src in ("rule", "tgpn")}
    ratios_stride = []
    for seq, frames in f_lab.items():
        subj = subject_of[seq]
        for f, h in frames.items():
            if (seq, f) in rule_lab and (seq, f) in preds:
                f_pairs["rule"][subj].append((h, rule_lab[(seq, f)]))
                f_pairs["tgpn"][subj].append((h, preds[(seq, f)]))
    for s in strides:
        if s["status"] == "annotated":
            a, b = int(s["initial_contact_frame"]), int(s["next_initial_contact_frame"])
            inside = [y - x for x, y in rule_int.get(s["sequence_id"], []) if a <= x and y <= b]
            if inside:
                ratios_stride.append(float(np.mean(inside)) / (b - a))

    rng = np.random.default_rng(SEED)
    results = {"reference": {
        "sequences": len(seqs),
        "subjects_with_contacts": len({subject_of[s] for s, sl in order.items()
                                       if any(f is not None and t == "contact" for f, t, _ in sl)}),
        "annotated_events": sum(e["status"] == "annotated" for e in events),
        "unresolvable_events": sum(e["status"] == "unresolvable" for e in events),
        "annotated_strides": sum(s["status"] == "annotated" for s in strides),
        "excluded_strides": sum(s["status"] == "excluded" for s in strides)},
        "track_s_contact_events": {}, "track_s_two_state": {}, "track_f_four_state": {}, "period": {}}

    def event_stat(src, tol):
        def stat(sample):
            m = h = p = 0
            for s in sample:
                c = ev_counts[src][tol].get(s)
                if c:
                    m += c[0]; h += c[1]; p += c[2]
            return 2 * m / (h + p) if h + p else float("nan")
        return stat

    for tol in TOLERANCES:
        subjects = [s for s in ev_counts["rule"][tol] if ev_counts["rule"][tol][s][1]]
        entry = {}
        for src in ("rule", "tgpn"):
            tot = np.sum([v[:3] for v in ev_counts[src][tol].values()], axis=0)
            errs = [e for v in ev_counts[src][tol].values() for e in v[3]]
            entry[src] = {"f1": bootstrap(subjects, event_stat(src, tol), rng),
                          "matched": int(tot[0]), "reference_events": int(tot[1]),
                          "predicted_events": int(tot[2]),
                          "matched_mae_frames": float(np.mean(errs)) if errs else None,
                          "signed_note": "unsigned"}
        entry["tgpn_minus_rule"] = bootstrap(
            subjects, lambda s, t=tol: event_stat("tgpn", t)(s) - event_stat("rule", t)(s), rng)
        results["track_s_contact_events"][f"tolerance_{tol}"] = entry

    # signed offsets (predicted - human) for matched pairs at tolerance 2, to show bias
    for src in ("rule", "tgpn"):
        offsets = []
        for seq, sl in order.items():
            region = evaluable_mask(sl)
            human = sorted(f for f, t, st in sl if f is not None and t == "contact")
            if src == "rule":
                pred = sorted(f for f in rule_starts.get(seq, ()) if f in region)
            else:
                tg = {f: s for (q, f), s in preds.items() if q == seq}
                pred = sorted(f for f in p0_entries(tg) if f in region)
            for hf in human:
                near = [p for p in pred if abs(p - hf) <= 2]
                if near:
                    offsets.append(min(near, key=lambda p: (abs(p - hf), p)) - hf)
        results["track_s_contact_events"][f"{src}_signed_offset_nearest_within_2"] = {
            "mean": float(np.mean(offsets)) if offsets else None,
            "counts": {str(k): int(v) for k, v in zip(*np.unique(offsets, return_counts=True))}}

    for src in ("rule", "tgpn"):
        pairs = ds_pairs[src]
        subjects = [s for s in pairs if pairs[s]]
        flat = lambda sample, i: [p[i] for s in sample for p in pairs[s]]
        results["track_s_two_state"][src] = {
            "frames": sum(len(v) for v in pairs.values()),
            "kappa": bootstrap(subjects, lambda smp: kappa(flat(smp, 0), flat(smp, 1), 2), rng),
            "agreement": float(np.mean(np.equal(flat(subjects, 0), flat(subjects, 1)))),
            "human_double_support_fraction": float(np.mean(np.equal(flat(subjects, 0), 0))),
            "predicted_double_support_fraction": float(np.mean(np.equal(flat(subjects, 1), 0)))}

    for src in ("rule", "tgpn"):
        pairs = f_pairs[src]
        subjects = [s for s in pairs if pairs[s]]
        flat = lambda sample, i: [p[i] for s in sample for p in pairs[s]]
        def subject_macro(sample):
            return float(np.mean([macro_f1([p[0] for p in pairs[s]], [p[1] for p in pairs[s]], 4) for s in sample]))
        cm = np.zeros((4, 4), dtype=int)
        np.add.at(cm, (flat(subjects, 0), flat(subjects, 1)), 1)
        results["track_f_four_state"][src] = {
            "frames": int(cm.sum()),
            "subject_macro_f1": bootstrap(subjects, subject_macro, rng),
            "weighted_kappa_linear": bootstrap(subjects, lambda smp: kappa(flat(smp, 0), flat(smp, 1), 4, "linear"), rng),
            "frame_agreement": float(np.trace(cm) / cm.sum()),
            "confusion_rows_reference_cols_predicted": cm.tolist()}

    # paired TGPN - rule differences for the frame-level kappas (same frames, same subjects)
    def flat_pairs(pairs, sample, i):
        return [p[i] for s in sample for p in pairs[s]]

    two_subjects = [s for s in ds_pairs["rule"] if ds_pairs["rule"][s]]
    results["track_s_two_state"]["tgpn_minus_rule_kappa"] = bootstrap(two_subjects, lambda smp: (
        kappa(flat_pairs(ds_pairs["tgpn"], smp, 0), flat_pairs(ds_pairs["tgpn"], smp, 1), 2)
        - kappa(flat_pairs(ds_pairs["rule"], smp, 0), flat_pairs(ds_pairs["rule"], smp, 1), 2)), rng)
    four_subjects = [s for s in f_pairs["rule"] if f_pairs["rule"][s]]
    results["track_f_four_state"]["tgpn_minus_rule_weighted_kappa"] = bootstrap(four_subjects, lambda smp: (
        kappa(flat_pairs(f_pairs["tgpn"], smp, 0), flat_pairs(f_pairs["tgpn"], smp, 1), 4, "linear")
        - kappa(flat_pairs(f_pairs["rule"], smp, 0), flat_pairs(f_pairs["rule"], smp, 1), 4, "linear")), rng)

    r = np.array([x["ratio"] for x in ratios_step])
    results["period"] = {
        "rule_interval_over_human_step": {"n": int(r.size), "median": float(np.median(r)),
                                          "q25": float(np.quantile(r, .25)), "q75": float(np.quantile(r, .75))},
        "mean_rule_interval_over_human_stride": {"n": len(ratios_stride), "median": float(np.median(ratios_stride)),
                                                 "q25": float(np.quantile(ratios_stride, .25)),
                                                 "q75": float(np.quantile(ratios_stride, .75))}}

    (out / "comparison.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
