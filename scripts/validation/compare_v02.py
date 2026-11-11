"""Pre-registered validation of v0.2 step-event labels (docs/step_event_labels_v0.2.md, E1-E4).

Compares v0.2 contact and toe-off events, and double vs single support frames, with the held-out
AI-assisted reference (annotations/validation/v1/results/reference_events.csv). v0.1 is scored on
the same frames for E3. Run once; do not retune v0.2 on these results.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("compare_reference", HERE / "compare_reference.py")
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)

SEED = 20261112


def read_gz(path: Path):
    with gzip.open(path, "rt", newline="") as h:
        return list(csv.DictReader(h))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, default=Path("annotations/validation/v1/results/reference_events.csv"))
    parser.add_argument("--v02", type=Path, default=Path("annotations/provisional/v0.2-step-events"))
    parser.add_argument("--v01", type=Path, default=Path("annotations/provisional/v0.1-ai"))
    parser.add_argument("--output", type=Path, default=Path("annotations/validation/v1/results/v02_comparison.json"))
    args = parser.parse_args()

    ref_rows = list(csv.DictReader(args.reference.open(newline="", encoding="utf-8")))
    ref_rows = [r for r in ref_rows if r["sequence_id"] != cr.CALIBRATION]
    order = cr.ordered_events(ref_rows)
    seqs = set(order)
    subject_of = {s: ":".join(s.split(":")[:2]) for s in seqs}

    v2_events = [e for e in read_gz(args.v02 / "step_events.csv.gz") if e["sequence_id"] in seqs]
    v2_contacts, v2_toe, v2_steps = defaultdict(set), defaultdict(set), defaultdict(list)
    for e in v2_events:
        v2_contacts[e["sequence_id"]].update({int(e["contact_frame"]), int(e["next_contact_frame"])})
        if e["toe_off_frame"]:
            v2_toe[e["sequence_id"]].add(int(float(e["toe_off_frame"])))
        v2_steps[e["sequence_id"]].append((int(e["contact_frame"]), int(e["next_contact_frame"]), e["confidence"]))
    v2_state = {(r["sequence_id"], int(r["frame_index"])): int(r["phase_index"])
                for r in read_gz(args.v02 / "frame_labels.csv.gz") if r["sequence_id"] in seqs}
    v1_state = {(r["sequence_id"], int(r["frame_index"])): int(r["phase_index"])
                for r in read_gz(args.v01 / "frame_labels.csv.gz")
                if r["sequence_id"] in seqs and r["confidence"] == "medium"}

    # ---- E1/E2 event counts per subject
    counts = {k: {t: defaultdict(lambda: [0, 0, 0]) for t in cr.TOLERANCES} for k in ("contact", "toe_off")}
    offsets = {"contact": [], "toe_off": []}
    covered = total_ref_contacts = 0
    for seq, sl in order.items():
        subj = subject_of[seq]
        region = cr.evaluable_mask(sl)
        for kind, ref_type, pred_set in (("contact", "contact", v2_contacts), ("toe_off", "opposite_toe_off", v2_toe)):
            human = [f for f, t, _ in sl if f is not None and t == ref_type]
            pred = sorted(f for f in pred_set.get(seq, ()) if f in region)
            for tol in cr.TOLERANCES:
                m = cr.match_events(human, pred, tol)
                c = counts[kind][tol][subj]
                c[0] += m["matched"]; c[1] += len(human); c[2] += len(pred)
            for hf in human:
                near = [p for p in pred if abs(p - hf) <= 2]
                if near:
                    offsets[kind].append(min(near, key=lambda p: (abs(p - hf), p)) - hf)
        human_contacts = [f for f, t, _ in sl if f is not None and t == "contact"]
        total_ref_contacts += len(human_contacts)
        spans = v2_steps.get(seq, [])
        covered += sum(any(a - 2 <= f <= b + 2 for a, b, _ in spans) for f in human_contacts)

    rng = np.random.default_rng(SEED)

    def event_stat(kind, tol):
        def stat(sample):
            m = h = p = 0
            for s in sample:
                c = counts[kind][tol].get(s)
                if c:
                    m += c[0]; h += c[1]; p += c[2]
            return 2 * m / (h + p) if h + p else float("nan")
        return stat

    results = {"targets": {"E1_contact_f1_tau1_lower": 0.80, "E2_toe_off_f1_tau1_lower": 0.70,
                           "E3_kappa_difference_lower": 0.0}}
    for kind in ("contact", "toe_off"):
        entry = {}
        for tol in cr.TOLERANCES:
            subjects = [s for s in counts[kind][tol] if counts[kind][tol][s][1]]
            tot = np.sum(list(counts[kind][tol].values()), axis=0)
            entry[f"tolerance_{tol}"] = {"f1": cr.bootstrap(subjects, event_stat(kind, tol), rng),
                                         "matched": int(tot[0]), "reference_events": int(tot[1]),
                                         "predicted_events": int(tot[2])}
        o = offsets[kind]
        entry["signed_offset_nearest_within_2"] = {
            "mean": float(np.mean(o)) if o else None,
            "counts": {str(k): int(v) for k, v in zip(*np.unique(o, return_counts=True))} if o else {}}
        results[f"{kind}_events"] = entry

    # ---- E3 two-state on common frames
    pairs = defaultdict(list)
    for seq, sl in order.items():
        for f, lab in cr.two_state_labels(sl).items():
            key = (seq, f)
            if key in v2_state and key in v1_state:
                h = 0 if lab == "DS" else 1
                pairs[subject_of[seq]].append((h, 0 if v2_state[key] == 0 else 1, 0 if v1_state[key] == 0 else 1))
    subjects = [s for s in pairs if pairs[s]]
    flat = lambda smp, i: [p[i] for s in smp for p in pairs[s]]
    k2 = lambda smp: cr.kappa(flat(smp, 0), flat(smp, 1), 2)
    k1 = lambda smp: cr.kappa(flat(smp, 0), flat(smp, 2), 2)
    results["two_state"] = {
        "frames": sum(len(v) for v in pairs.values()),
        "v02_kappa": cr.bootstrap(subjects, k2, rng),
        "v01_kappa_same_frames": cr.bootstrap(subjects, k1, rng),
        "v02_minus_v01": cr.bootstrap(subjects, lambda smp: k2(smp) - k1(smp), rng),
        "reference_double_support_fraction": float(np.mean(np.equal(flat(subjects, 0), 0))),
        "v02_double_support_fraction": float(np.mean(np.equal(flat(subjects, 1), 0))),
        "v01_p0_fraction": float(np.mean(np.equal(flat(subjects, 2), 0)))}

    # ---- E4 descriptive
    ratios = []
    for seq, sl in order.items():
        hc = [(i, f) for i, (f, t, st) in enumerate(sl) if f is not None and t == "contact"]
        for (i, a), (j, b) in zip(hc, hc[1:]):
            if any(sl[k][2] == "unresolvable" for k in range(i + 1, j)):
                continue
            mid = (a + b) / 2
            for x, y, _ in v2_steps.get(seq, []):
                if x <= mid < y:
                    ratios.append((y - x) / (b - a))
                    break
    r = np.asarray(ratios)
    results["descriptive"] = {
        "step_ratio": {"n": int(r.size), "median": float(np.median(r)), "q25": float(np.quantile(r, .25)),
                       "q75": float(np.quantile(r, .75))} if r.size else None,
        "reference_contacts_inside_v02_steps": {"covered": covered, "total": total_ref_contacts},
        "v02_medium_step_fraction": float(np.mean([c == "medium" for v in v2_steps.values() for _, _, c in v])),
    }
    e1 = results["contact_events"]["tolerance_1"]["f1"]["lower"]
    e2 = results["toe_off_events"]["tolerance_1"]["f1"]["lower"]
    e3 = results["two_state"]["v02_minus_v01"]["lower"]
    results["verdict"] = {"E1_met": bool(e1 >= 0.80), "E2_met": bool(e2 >= 0.70), "E3_met": bool(e3 > 0)}
    args.output.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
