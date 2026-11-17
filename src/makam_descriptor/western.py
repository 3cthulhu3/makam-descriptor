"""Western baseline: Krumhansl–Kessler (1982) key finding on a 12-class projection.

Deliberately standard. It exists to be compared against, and to show what the
53 -> 12 projection erases.
"""
from __future__ import annotations

import numpy as np

COMMAS = 53
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def project_to_12(abs_pcd53: np.ndarray) -> np.ndarray:
    """Many-to-one projection: each comma class goes to the nearest semitone (C = 0)."""
    out = np.zeros(12)
    for pc, w in enumerate(abs_pcd53):
        out[round(pc * 12 / COMMAS) % 12] += w
    return out


def rounding_error_cents(abs_pcd53: np.ndarray) -> float:
    err = [abs(pc * 1200 / COMMAS - round(pc * 12 / COMMAS) * 100) for pc in range(COMMAS)]
    return float(np.dot(abs_pcd53, err))


def key_find(abs_pcd53: np.ndarray) -> dict:
    h = project_to_12(abs_pcd53)
    err = round(rounding_error_cents(abs_pcd53), 1)
    if np.ptp(h) == 0:   # a flat profile correlates with nothing; say so instead of NaN
        return {"key": None, "correlation": None, "mean_rounding_error_cents": err}
    best = ("", -2.0)
    for tonic in range(12):
        for mode, prof in (("major", KK_MAJOR), ("minor", KK_MINOR)):
            r = float(np.corrcoef(h, np.roll(prof, tonic))[0, 1])
            if r > best[1]:
                best = (f"{NAMES[tonic]} {mode}", r)
    return {"key": best[0], "correlation": round(best[1], 3), "mean_rounding_error_cents": err}
