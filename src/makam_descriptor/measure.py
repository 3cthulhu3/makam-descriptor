"""Measurement layer: what a piece actually does, independent of any theory.

Outputs are *measured*: the karar (estimated as the final note, following
Atlı, Bozkurt & Şentürk 2015 for scores) and a duration-weighted distribution
over the 53 comma positions relative to that karar.

Since 0.3 the distribution is also split by direction of departure: a note
"departs downward" if the next note of a different pitch is lower, "upward" if
higher; repeated notes take the direction of the run they belong to, and the
final run departs nowhere. pcd_down + pcd_up <= pcd, all normalised by the
same total duration.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .symbtr import Note

COMMAS = 53


@dataclass(frozen=True, eq=False)
class Measurement:
    karar_koma53: int
    karar_pc: int
    pcd: np.ndarray            # shape (53,), relative to karar, sums to 1
    abs_pcd: np.ndarray        # shape (53,), absolute pitch classes, sums to 1
    total_duration: float
    n_notes: int
    pcd_down: np.ndarray | None = None   # shape (53,), relative to karar, departing downward
    pcd_up: np.ndarray | None = None     # shape (53,), relative to karar, departing upward


class MeasurementError(ValueError):
    pass


def measure(notes: tuple[Note, ...] | list[Note]) -> Measurement:
    if not notes:
        raise MeasurementError("no pitched notes")
    if any(not (n.duration > 0) for n in notes):      # also rejects NaN
        raise MeasurementError("every note needs a positive duration")
    karar = notes[-1].koma53
    karar_pc = karar % COMMAS
    abs_hist = np.zeros(COMMAS)
    for n in notes:
        abs_hist[n.koma53 % COMMAS] += n.duration
    total = abs_hist.sum()
    abs_pcd = abs_hist / total
    rel = np.roll(abs_pcd, -karar_pc)   # rel[i] = weight at karar + i

    down, up = np.zeros(COMMAS), np.zeros(COMMAS)
    nxt = None                            # next pitch different from the current run
    for i in range(len(notes) - 1, -1, -1):
        k = notes[i].koma53
        if i + 1 < len(notes) and notes[i + 1].koma53 != k:
            nxt = notes[i + 1].koma53
        if nxt is not None:
            (down if nxt < k else up)[(k - karar_pc) % COMMAS] += notes[i].duration
    return Measurement(karar, karar_pc, rel, abs_pcd, float(total), len(notes),
                       down / total, up / total)


def windows(notes: list[Note] | tuple[Note, ...], length: float, hop: float):
    """Yield (start, end, notes) windows by cumulative duration (for geçki, Phase 1)."""
    if length <= 0 or hop <= 0:
        raise ValueError("length and hop must be positive")
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
