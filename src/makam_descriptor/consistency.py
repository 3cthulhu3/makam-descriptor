"""Consistency layer: compares the measured piece against the postulated theory.

Two resolutions, on purpose:
  * identification at EXACT comma positions (the one-comma gap between rast
    and mahur *is* the difference between them);
  * abstention with ONE comma of slack (a piece is "outside the theory" only
    if it leaves every applicable scale even then).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .measure import COMMAS, Measurement
from .theory import Makam, Theory


@dataclass(frozen=True)
class Params:
    abstain_threshold: float = 0.90   # fixed before the Phase 0 run; not tuned
    abstain_tolerance: int = 1        # commas
    candidate_margin: float = 0.05    # candidates: exact fit within this of the best


def share_on(pcd: np.ndarray, degrees: frozenset[int], tolerance: int = 0) -> float:
    mask = np.zeros(COMMAS, dtype=bool)
    for d in degrees:
        for t in range(-tolerance, tolerance + 1):
            mask[(d + t) % COMMAS] = True
    return float(pcd[mask].sum())


def guclu_emphasis(pcd: np.ndarray, makam: Makam) -> float:
    """Weight on the güçlü relative to the mean weight on the other non-karar degrees."""
    others = [d for d in makam.degrees if d not in (0, makam.guclu_rel)]
    base = np.mean([pcd[d] for d in others]) if others else 0.0
    return float(pcd[makam.guclu_rel] / base) if base > 0 else float("inf")


@dataclass(frozen=True)
class Fit:
    makam: str
    exact: float
    tolerant: float
    variants: dict[str, float]
    guclu_emphasis: float


def compare(m: Measurement, theory: Theory, params: Params = Params()) -> dict:
    applicable = theory.by_karar(m.karar_pc)
    fits = sorted(
        (Fit(mk.key,
             share_on(m.pcd, mk.degrees),
             share_on(m.pcd, mk.degrees, params.abstain_tolerance),
             {v.name: share_on(m.pcd, mk.degrees_with(v.name)) for v in mk.variants},
             guclu_emphasis(m.pcd, mk))
         for mk in applicable),
        key=lambda f: f.exact, reverse=True)

    reasons: list[str] = []
    if not applicable:
        reasons.append("estimated karar matches no makam in the theory layer")
        best_tolerant = 0.0
    else:
        best_tolerant = max(f.tolerant for f in fits)
        if best_tolerant < params.abstain_threshold:
            reasons.append(
                f"only {best_tolerant:.0%} of the piece lies within {params.abstain_tolerance} "
                f"comma of any applicable scale (threshold {params.abstain_threshold:.0%})")

    candidates = [f.makam for f in fits if f.exact >= fits[0].exact - params.candidate_margin]
    return {
        "fits": fits,
        # What the tool asserts: nothing when it abstains.
        "candidates": [] if reasons else candidates,
        "top": None if reasons or not fits else fits[0].makam,
        # What the ranking says regardless of abstention (for evaluation only).
        "ranked_candidates": candidates,
        "ranked_top": fits[0].makam if fits else None,
        "in_theory_score": best_tolerant,      # threshold-free score used for AUROC
        "out_of_theory_share": round(1 - best_tolerant, 3) if applicable else 1.0,
        "abstain": bool(reasons),
        "reasons": reasons,
    }
