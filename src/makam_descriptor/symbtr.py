"""Reader for SymbTr .txt scores (tab-separated, pitches in 53-comma units).

SymbTr data is CC BY-NC-SA; this module only reads it and ships none of it.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

NOTE_CODE = "9"   # SymbTr "Kod" for an ordinary note; ornaments and control rows are skipped


@dataclass(frozen=True)
class Note:
    koma53: int        # absolute pitch in commas
    duration: float    # in whole notes (Pay / Payda)


@dataclass(frozen=True)
class Score:
    name: str
    makam_label: str | None   # from the file name; a label, not ground truth
    notes: tuple[Note, ...]


def label_from_filename(path: str | Path) -> str | None:
    stem = Path(path).stem
    return stem.split("--")[0] if "--" in stem else None


def read_symbtr_txt(path: str | Path) -> Score:
    notes: list[Note] = []
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("Kod") != NOTE_CODE:
                continue
            try:
                k = int(row["Koma53"])
                dur = int(row["Pay"]) / int(row["Payda"])
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            if k <= 0 or dur <= 0:     # rests are encoded as 0 / -1
                continue
            notes.append(Note(k, dur))
    return Score(Path(path).stem, label_from_filename(path), tuple(notes))
