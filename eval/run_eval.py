"""Evaluation on SymbTr scores.

Usage: python eval/run_eval.py /path/to/SymbTr/txt [--json results.json]

Four questions, each with its own measure (proposal, Section 6):
  1. identification: top-1, candidate-set coverage and size (known makams)
  2. abstention: rate inside / outside the theory, AUROC of the in-theory score,
     plus leave-one-makam-out (remove each makam, check its pieces are flagged)
  3. calibration: (Phase 1)
  4. agent benefit: (Phase 3)
Plus the Western baseline per makam.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

from makam_descriptor.consistency import Params, compare
from makam_descriptor.measure import MeasurementError, measure
from makam_descriptor.symbtr import read_symbtr_txt
from makam_descriptor.theory import load_theory
from makam_descriptor.western import key_find

# Two definitions of the "unknown" set, because the result depends on it.
#  - "proposal": the six makams behind the proposal's Section 4 figures
#    (reconstructed: their counts reproduce n = 456 and 257 with known karar).
#    All six differ from every known makam in their dizi.
#  - "frequency": the nine most frequent SymbTr makams outside the theory layer,
#    with no selection. Includes muhayyer and beyati, whose dizi coincide with
#    hüseyni and uşşak at this resolution: they differ in seyir, not in pitch set.
UNKNOWN_SETS = {
    "proposal": ["huzzam", "segah", "hicazkar", "kurdilihicazkar", "saba", "karcigar"],
    "frequency": ["huzzam", "segah", "hicazkar", "kurdilihicazkar", "muhayyer", "saba",
                  "acemasiran", "beyati", "karcigar"],
}


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(score_pos > score_neg) + 0.5 P(tie) — Mann–Whitney form, threshold-free."""
    p, n = np.asarray(pos), np.asarray(neg)
    gt = (p[:, None] > n[None, :]).sum()
    eq = (p[:, None] == n[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(p) * len(n)))


def load(txt_dir: Path, makams: list[str]):
    out = []
    for mk in makams:
        for f in sorted(txt_dir.glob(f"{mk}--*.txt")):
            s = read_symbtr_txt(f)
            try:
                out.append((mk, s.name, measure(s.notes)))
            except MeasurementError:
                pass
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("txt_dir", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--unknown", choices=list(UNKNOWN_SETS), default="proposal")
    a = ap.parse_args(argv)
    UNKNOWN = UNKNOWN_SETS[a.unknown]

    theory, params = load_theory(), Params()
    known = load(a.txt_dir, list(theory.makams))
    unknown = load(a.txt_dir, UNKNOWN)
    res: dict = {"unknown_set": a.unknown, "params": params.__dict__, "n_known": len(known), "n_unknown": len(unknown)}

    # 1 + Western baseline
    per = collections.defaultdict(lambda: collections.Counter())
    keys = collections.defaultdict(collections.Counter)
    tol_ident = collections.Counter()   # what happens if identification used 1-comma tolerance
    known_scores, unk_scores, kk_known, kk_unk = [], [], [], []
    for mk, _, m in known:
        c = compare(m, theory, params)
        per[mk]["n"] += 1
        per[mk]["top1"] += c["ranked_top"] == mk                 # ranking, regardless of abstention
        per[mk]["in_set"] += mk in c["ranked_candidates"]
        per[mk]["set_size"] += len(c["ranked_candidates"])
        per[mk]["abstain"] += c["abstain"]
        per[mk]["accepted_correct"] += c["top"] == mk            # what the tool actually asserts
        # Identification with 1 comma of tolerance: is the true makam *uniquely* best?
        if c["fits"]:
            tf = {f.makam: f.tolerant for f in c["fits"]}
            others = [v for k, v in tf.items() if k != mk]
            tol_ident[mk] += mk in tf and all(tf[mk] > v + 0.005 for v in others)
        known_scores.append(c["in_theory_score"])
        kf = key_find(m.abs_pcd)
        keys[mk][kf["key"]] += 1
        kk_known.append(kf["correlation"])
    for mk, _, m in unknown:
        c = compare(m, theory, params)
        per[mk]["n"] += 1
        per[mk]["abstain"] += c["abstain"]
        per[mk]["karar_known"] += m.karar_pc in theory.karar_pcs
        per[mk]["abstain_karar_known"] += c["abstain"] and m.karar_pc in theory.karar_pcs
        unk_scores.append((c["in_theory_score"], m.karar_pc in theory.karar_pcs))
        kf = key_find(m.abs_pcd)
        keys[mk][kf["key"]] += 1
        kk_unk.append(kf["correlation"])

    n_k = len(known)
    res["identification"] = {
        "top1": sum(per[m]["top1"] for m in theory.makams) / n_k,
        "in_candidate_set": sum(per[m]["in_set"] for m in theory.makams) / n_k,
        "mean_set_size": sum(per[m]["set_size"] for m in theory.makams) / n_k,
        "abstain_rate_known": sum(per[m]["abstain"] for m in theory.makams) / n_k,
        "accepted_and_correct": sum(per[m]["accepted_correct"] for m in theory.makams) / n_k,
    }
    n_kk = sum(per[m]["karar_known"] for m in UNKNOWN)
    res["abstention"] = {
        "abstain_rate_unknown": sum(per[m]["abstain"] for m in UNKNOWN) / len(unknown),
        "n_unknown_karar_known": n_kk,
        "abstain_rate_unknown_karar_known": sum(per[m]["abstain_karar_known"] for m in UNKNOWN) / max(n_kk, 1),
        "auroc": auroc(known_scores, [s for s, _ in unk_scores]),
        "auroc_karar_known": auroc(known_scores, [s for s, k in unk_scores if k]),
        "auroc_western_correlation": auroc(kk_known, kk_unk),
    }

    # Leave-one-makam-out: remove each makam from the theory; are its pieces flagged?
    lomo = {}
    for mk in theory.makams:
        th = theory.without(mk)
        pieces = [m for k, _, m in known if k == mk]
        flagged = sum(compare(m, th, params)["abstain"] for m in pieces)
        stolen = collections.Counter(compare(m, th, params)["top"] for m in pieces)
        lomo[mk] = {"n": len(pieces), "flagged": flagged / len(pieces),
                    "absorbed_by": {k: v for k, v in stolen.most_common() if k}}
    res["leave_one_makam_out"] = lomo

    res["per_makam"] = {
        mk: {**{k: (v / per[mk]["n"] if k not in ("n", "karar_known") else v) for k, v in per[mk].items()},
             "top1_unique_with_1_comma_tolerance": tol_ident[mk] / per[mk]["n"] if mk in theory.makams else None,
             "western_top": keys[mk].most_common(3)}
        for mk in list(theory.makams) + UNKNOWN
    }

    txt = json.dumps(res, indent=2, ensure_ascii=False, default=float)
    print(txt)
    if a.json:
        a.json.write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
