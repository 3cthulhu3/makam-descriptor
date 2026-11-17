"""Consistency layer: compares the measured piece against the postulated theory.

Two resolutions, on purpose:
  * identification at EXACT comma positions, on the dizi alone (the one-comma
    gap between rast and mahur *is* the difference between them);
  * abstention with ONE comma of slack, on the dizi plus the variants the
    theory declares (a piece is "outside the theory" only if it leaves
    everything the theory says about every applicable makam, even then).

Naming (0.3): only the makam whose dizi fits best may be named. Coverage
decides *whether* a makam may be named, never *which*: if the best-fitting
makam is not covered by what the theory says about it, while another makam
is, the tool names neither and reports both (`naming_conflict`). In 0.2 the
covered makam was named instead, so variants declared for one makam (acem in
rast) could take pieces from its neighbour (mâhur), which declares none.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .measure import COMMAS, Measurement
from .theory import Makam, Theory

_EPS = 1e-9   # float sums of durations; never let rounding decide a threshold or a tie


@dataclass(frozen=True)
class Params:
    abstain_threshold: float = 0.90   # fixed before the Phase 0 run; not tuned
    abstain_tolerance: int = 1        # commas
    candidate_margin: float = 0.05    # candidates: exact fit within this of the best
    variants_in_abstention: bool = True   # False restores the v0.1 rule (dizi only)
    name_best_fit_only: bool = True       # False restores the v0.2 naming rule


def share_on(pcd: np.ndarray, degrees: frozenset[int], tolerance: int = 0) -> float:
    mask = np.zeros(COMMAS, dtype=bool)
    for d in degrees:
        for t in range(-tolerance, tolerance + 1):
            mask[(d + t) % COMMAS] = True
    return float(pcd[mask].sum())


def guclu_emphasis(pcd: np.ndarray, makam: Makam) -> float | None:
    """Weight on the güçlü relative to the mean weight on the other non-karar degrees.

    None when it cannot be measured on an octave-folded distribution: the güçlü
    is the octave of the karar (mâhur), or the piece never touches the other
    degrees.
    """
    if makam.guclu_rel == 0:
        return None
    others = [d for d in makam.degrees if d not in (0, makam.guclu_rel)]
    base = float(np.mean([pcd[d] for d in others])) if others else 0.0
    return float(pcd[makam.guclu_rel] / base) if base > 0 else None


@dataclass(frozen=True)
class Fit:
    makam: str
    exact: float                 # share on the dizi, exact comma positions (ranking)
    tolerant: float              # share within the tolerance of the dizi
    coverage: float              # the same, dizi + declared variants (abstention)
    variants: dict[str, float]   # exact share on dizi + that one variant
    guclu_emphasis: float | None


def _top(fits: list[Fit]) -> str | None:
    """Best exact fit, or None when the best is shared (file order must not decide)."""
    if not fits or (len(fits) > 1 and fits[0].exact - fits[1].exact <= _EPS):
        return None
    return fits[0].makam


def compare(m: Measurement, theory: Theory, params: Params = Params()) -> dict:
    applicable = theory.by_karar(m.karar_pc)
    tol = params.abstain_tolerance
    fits = sorted(
        (Fit(mk.key,
             share_on(m.pcd, mk.degrees),
             share_on(m.pcd, mk.degrees, tol),
             share_on(m.pcd, mk.degrees_with_all_variants if params.variants_in_abstention else mk.degrees, tol),
             {v.name: share_on(m.pcd, mk.degrees_with(v.name)) for v in mk.variants},
             guclu_emphasis(m.pcd, mk))
         for mk in applicable),
        key=lambda f: f.exact, reverse=True)

    # A makam may be named only if what the theory says about *it* covers the piece.
    accepted = [f for f in fits if f.coverage >= params.abstain_threshold - _EPS]
    best_coverage = max((f.coverage for f in fits), default=0.0)

    reasons: list[str] = []
    if not applicable:
        reasons.append("estimated karar matches no makam in the theory layer")
    elif not accepted:
        what = "scale or declared variant" if params.variants_in_abstention else "scale"
        reasons.append(
            f"only {best_coverage:.0%} of the piece lies within {tol} comma of any applicable "
            f"{what} (threshold {params.abstain_threshold:.0%})")

    def within_margin(fs: list[Fit]) -> list[str]:
        return [f.makam for f in fs if f.exact >= fs[0].exact - params.candidate_margin]

    accepted_names = {f.makam for f in accepted}
    conflict = False
    if not accepted:
        top, candidates = None, []
    elif params.name_best_fit_only and fits[0].makam not in accepted_names:
        # The best dizi fit is not covered by its own theory; another makam is.
        conflict = True
        best_group = {f.makam for f in fits if f.exact >= fits[0].exact - _EPS}
        top = None
        candidates = [f.makam for f in fits if f.makam in best_group or f.makam in accepted_names]
    else:
        top = _top(accepted)
        candidates = within_margin(accepted)
    top_fit = next((f for f in fits if f.makam == top), None)

    return {
        "fits": fits,
        # What the tool asserts: nothing when it abstains, no single makam on a tie or a conflict.
        "candidates": candidates,
        "top": top,
        "tie": bool(accepted) and not conflict and top is None,
        "naming_conflict": conflict,
        "accepted_via_variants": top_fit is not None and top_fit.tolerant < params.abstain_threshold - _EPS,
        # What the ranking says regardless of abstention (for evaluation only).
        "ranked_candidates": within_margin(fits),
        "ranked_top": _top(fits),
        "in_theory_score": best_coverage,      # threshold-free score used for AUROC
        "out_of_theory_share": round(1 - best_coverage, 3) if applicable else 1.0,
        "abstain": bool(reasons),
        "reasons": reasons,
    }
