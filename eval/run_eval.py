"""Evaluation on SymbTr scores.

Usage: python eval/run_eval.py /path/to/SymbTr/txt [--split dev|test|all]
           [--unknown frequency|proposal] [--pitch-column KomaAE|Koma53]
           [--no-variants] [--no-direction] [--v02-naming] [--json results.json]

Data protocol (since 0.3): SymbTr is split by composer into dev (~70 %) and
test (~30 %) by a hash rule fixed in eval/make_split.py, before any result on
it was seen. Develop on dev (the default). Look at test once per release.

Four questions, each with its own measure (proposal, Section 6):
  1. identification: top-1, candidate-set coverage and size (known makams);
     for an agent the key figures are accepted_and_wrong and its unflagged part
  2. abstention: rate inside / outside the theory, AUROC of the in-theory score,
     plus leave-one-makam-out (remove each makam, check its pieces are flagged)
  3. calibration: (Phase 1)
  4. agent benefit: (Phase 3)
Plus the Western baseline per makam.

The flags undo, one at a time, the analytic choices made after the v0.1 run:
--pitch-column Koma53 (0.1 reader), --no-variants (0.1 abstention rule),
--no-direction (0.2 variant rule), --v02-naming (0.2 naming rule).
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

# Always evaluate the code in this checkout, never whatever version is installed.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import makam_descriptor  # noqa: E402
from makam_descriptor.consistency import Params, compare
from makam_descriptor.measure import MeasurementError, measure
from makam_descriptor.symbtr import PITCH_COLUMNS, SymbTrFormatError, read_symbtr_txt
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


def auroc(pos: list[float], neg: list[float]) -> float | None:
    """P(score_pos > score_neg) + 0.5 P(tie) — Mann–Whitney form, threshold-free."""
    if not pos or not neg:
        return None
    # Quantise: scores are float sums of durations, and a fully covered piece can come out
    # as 1.0 or 1 - 2e-16 depending on summation order. Ties must not depend on that.
    p, n = np.round(np.asarray(pos, dtype=float), 9), np.round(np.asarray(neg, dtype=float), 9)
    gt = (p[:, None] > n[None, :]).sum()
    eq = (p[:, None] == n[None, :]).sum()
    return float((gt + 0.5 * eq) / (len(p) * len(n)))


def rate(num: float, den: float) -> float | None:
    return num / den if den else None


def load(txt_dir: Path, makams: list[str], column: str, dropped: list[str], keep: set[str] | None):
    out = []
    for mk in makams:
        for f in sorted(txt_dir.glob(f"{mk}--*.txt")):
            if keep is not None and f.stem not in keep:
                continue
            try:
                s = read_symbtr_txt(f, column)
                out.append((mk, s.name, measure(s.notes)))
            except (MeasurementError, SymbTrFormatError) as e:
                dropped.append(f"{f.name}: {e}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("txt_dir", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--unknown", choices=list(UNKNOWN_SETS), default="frequency",
                    help="default: frequency (unselected); 'proposal' reproduces the selected set")
    ap.add_argument("--split", choices=["dev", "test", "all"], default="dev",
                    help="default: dev. Look at test once per release, never while developing")
    ap.add_argument("--split-manifest", type=Path,
                    default=Path(__file__).resolve().parent / "split_v1.json")
    ap.add_argument("--pitch-column", choices=PITCH_COLUMNS,
                    help="default: the column the theory names (KomaAE for AEU)")
    ap.add_argument("--no-variants", action="store_true",
                    help="v0.1 abstention rule: judge against the dizi only, ignore declared variants")
    ap.add_argument("--no-direction", action="store_true",
                    help="v0.2 variant rule: a variant counts in any melodic direction")
    ap.add_argument("--v02-naming", action="store_true",
                    help="v0.2 naming rule: name the best exact fit among covered makams")
    a = ap.parse_args(argv)
    UNKNOWN = UNKNOWN_SETS[a.unknown]

    theory = load_theory()
    params = Params(variants_in_abstention=not a.no_variants,
                    variant_direction=not a.no_direction,
                    name_best_fit_only=not a.v02_naming)
    column = a.pitch_column or theory.symbtr_column
    if not a.txt_dir.is_dir():
        sys.exit(f"not a directory: {a.txt_dir}")
    dropped: list[str] = []
    keep = None
    if a.split != "all":
        manifest = json.loads(a.split_manifest.read_text(encoding="utf-8"))
        keep = set(manifest[a.split])
        listed = keep | set(manifest["dev" if a.split == "test" else "test"])
        unlisted = sorted(p.stem for p in a.txt_dir.glob("*.txt") if p.stem not in listed)
        if unlisted:
            dropped += [f"{n}: not in split manifest" for n in unlisted]
    known = load(a.txt_dir, list(theory.makams), column, dropped, keep)
    unknown = load(a.txt_dir, UNKNOWN, column, dropped, keep)
    if not known or not unknown:
        sys.exit(f"no SymbTr scores of the evaluated makams under {a.txt_dir} "
                 "(expected files like 'rast--sarki--....txt'; point this at SymbTr/txt)")
    res: dict = {"package_version": makam_descriptor.__version__, "split": a.split, "unknown_set": a.unknown,
                 "pitch_column": column, "params": dataclasses.asdict(params),
                 "n_known": len(known), "n_unknown": len(unknown), "dropped_files": dropped}

    # 1 + Western baseline
    per = collections.defaultdict(lambda: collections.Counter())
    keys = collections.defaultdict(collections.Counter)
    tol_ident = collections.Counter()   # what happens if identification used 1-comma tolerance
    known_scores, unk_scores, kk_known, kk_unk = [], [], [], []
    for mk, _, m in known:
        c = compare(m, theory, params)
        per[mk]["n"] += 1
        per[mk]["karar_as_theory"] += m.karar_pc == theory.makams[mk].karar_pc
        per[mk]["top1"] += c["ranked_top"] == mk                 # ranking, regardless of abstention
        per[mk]["tied_top"] += bool(c["fits"]) and c["ranked_top"] is None
        per[mk]["in_set"] += mk in c["ranked_candidates"]
        per[mk]["set_size"] += len(c["ranked_candidates"])
        per[mk]["abstain"] += c["abstain"]
        per[mk]["accepted_correct"] += c["top"] == mk            # what the tool actually asserts
        per[mk]["accepted_wrong"] += c["top"] not in (None, mk)
        # wrong name with a single candidate: the agent gets no ambiguity signal at all
        per[mk]["accepted_wrong_unflagged"] += c["top"] not in (None, mk) and len(c["candidates"]) == 1
        per[mk]["naming_conflict"] += c.get("naming_conflict", False)
        per[mk]["accepted_via_variants"] += c["accepted_via_variants"]
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
        kk = m.karar_pc in theory.karar_pcs
        per[mk]["n"] += 1
        per[mk]["abstain"] += c["abstain"]
        per[mk]["karar_known"] += kk
        per[mk]["abstain_karar_known"] += c["abstain"] and kk
        if not c["abstain"]:
            per[mk]["named_" + (c["top"] or ("conflict" if c.get("naming_conflict") else "tie"))] += 1
        unk_scores.append((c["in_theory_score"], kk))
        kf = key_find(m.abs_pcd)
        keys[mk][kf["key"]] += 1
        kk_unk.append(kf["correlation"])

    n_k = len(known)
    tot = lambda field: sum(per[m][field] for m in theory.makams)  # noqa: E731
    res["identification"] = {
        "top1": tot("top1") / n_k,
        "tied_top": tot("tied_top") / n_k,
        "in_candidate_set": tot("in_set") / n_k,
        "mean_set_size": tot("set_size") / n_k,
        "karar_as_theory": tot("karar_as_theory") / n_k,
        "abstain_rate_known": tot("abstain") / n_k,
        "accepted_and_correct": tot("accepted_correct") / n_k,
        "accepted_and_wrong": tot("accepted_wrong") / n_k,
        "accepted_and_wrong_unflagged": tot("accepted_wrong_unflagged") / n_k,
        "naming_conflict": tot("naming_conflict") / n_k,
        "accepted_via_variants": tot("accepted_via_variants") / n_k,
    }
    n_kk = sum(per[m]["karar_known"] for m in UNKNOWN)
    res["abstention"] = {
        "abstain_rate_unknown": sum(per[m]["abstain"] for m in UNKNOWN) / len(unknown),
        "n_unknown_karar_known": n_kk,
        "abstain_rate_unknown_karar_known": rate(sum(per[m]["abstain_karar_known"] for m in UNKNOWN), n_kk),
        "auroc": auroc(known_scores, [s for s, _ in unk_scores]),
        "auroc_karar_known": auroc(known_scores, [s for s, k in unk_scores if k]),
        # Not a like-for-like baseline: a key-profile correlation was never meant as a
        # novelty score. It shows what a Western tool offers for this question, no more.
        "auroc_western_correlation": auroc(kk_known, kk_unk),
    }

    # Leave-one-makam-out: remove each makam from the theory; are its pieces flagged?
    lomo = {}
    for mk in theory.makams:
        th = theory.without(mk)
        cs = [compare(m, th, params) for k, _, m in known if k == mk]
        if not cs:
            continue
        stolen = collections.Counter(c["top"] or ("conflict" if c.get("naming_conflict") else "tie")
                                     for c in cs if not c["abstain"])
        lomo[mk] = {"n": len(cs), "flagged": sum(c["abstain"] for c in cs) / len(cs),
                    "absorbed_by": dict(stolen.most_common())}
    res["leave_one_makam_out"] = lomo

    per_makam = {}
    for mk in theory.makams:
        c, n = per[mk], per[mk]["n"]
        if not n:
            continue
        per_makam[mk] = {
            "n": n,
            **{k: c[k] / n for k in ("karar_as_theory", "top1", "tied_top", "in_set", "set_size", "abstain",
                                     "accepted_correct", "accepted_wrong", "accepted_wrong_unflagged",
                                     "naming_conflict", "accepted_via_variants")},
            "top1_unique_with_1_comma_tolerance": tol_ident[mk] / n,
            "western_top": keys[mk].most_common(3),
        }
    for mk in UNKNOWN:
        c, n = per[mk], per[mk]["n"]
        if not n:
            continue
        per_makam[mk] = {
            "n": n, "abstain": c["abstain"] / n,
            "n_karar_known": c["karar_known"],
            # of the pieces whose karar the theory knows, the share that is flagged
            "abstain_given_karar_known": rate(c["abstain_karar_known"], c["karar_known"]),
            "named_as": {k[len("named_"):]: v for k, v in c.most_common() if k.startswith("named_")},
            "western_top": keys[mk].most_common(3),
        }
    res["per_makam"] = per_makam

    txt = json.dumps(res, indent=2, ensure_ascii=False, default=float, allow_nan=False)
    print(txt)
    if a.json:
        a.json.write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
