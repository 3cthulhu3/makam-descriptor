"""Measurement layer: what a piece actually does, independent of any theory.

Outputs are *measured*: the karar (estimated as the final note, following
Atlı, Bozkurt & Şentürk 2015 for scores) and a duration-weighted distribution
over the 53 comma positions relative to that karar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .symbtr import Note

COMMAS = 53


@dataclass(frozen=True)
class Measurement:
    karar_koma53: int
    karar_pc: int
    pcd: np.ndarray            # shape (53,), relative to karar, sums to 1
    abs_pcd: np.ndarray        # shape (53,), absolute pitch classes, sums to 1
    total_duration: float
    n_notes: int


class MeasurementError(ValueError):
    pass


def measure(notes: tuple[Note, ...] | list[Note]) -> Measurement:
    if not notes:
        raise MeasurementError("no pitched notes")
    karar = notes[-1].koma53
    karar_pc = karar % COMMAS
    abs_hist = np.zeros(COMMAS)
    for n in notes:
        abs_hist[n.koma53 % COMMAS] += n.duration
    total = abs_hist.sum()
    abs_pcd = abs_hist / total
    rel = np.roll(abs_pcd, -karar_pc)   # rel[i] = weight at karar + i
    return Measurement(karar, karar_pc, rel, abs_pcd, float(total), len(notes))


def windows(notes: list[Note] | tuple[Note, ...], length: float, hop: float):
    """Yield (start, end, notes) windows by cumulative duration (for geçki, Phase 1)."""
    t, onsets = 0.0, []
    for n in notes:
        onsets.append(t)
        t += n.duration
    start = 0.0
    while start < t:
        sel = [n for n, o in zip(notes, onsets) if start <= o < start + length]
        if sel:
            yield start, min(start + length, t), sel
        start += hop
