"""Reader for SymbTr .txt scores (tab-separated).

SymbTr data is CC BY-NC-SA; this module only reads it and ships none of it.

Two things about the format matter for everything downstream:

* SymbTr carries every pitch twice. ``KomaAE`` is the pitch as notated in the
  Arel-Ezgi-Uzdilek system; ``Koma53`` is SymbTr's 53-TET notation, which
  follows performance practice and differs from AEU by a comma in a large share
  of the notes (uşşak's segâh, hüseynî's eviç, hüzzam's hisâr, ...). A theory
  must be compared with the column written in its own system; the theory file
  names that column and ``describe()`` uses it.
* ``Kod`` 9 is a plain note, but ornamented notes are ordinary sounding notes
  under other codes (tremolo 7, note-with-after-grace 10, silent grace 11,
  trill 12, mordents 23/24/43/44, glissando 4, small note 1, ...). They are
  counted. Grace notes proper (8, 17) borrow their time from a neighbour and
  are not; control rows (usul, phrase and print marks) carry no pitch.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

PITCH_COLUMNS = ("KomaAE", "Koma53")
DEFAULT_PITCH_COLUMN = "KomaAE"

GRACE_CODES = frozenset({"8", "17"})
CONTROL_CODES = frozenset(
    {"14", "18", "19", "20", "21", "35", "36", "37", "38", "39", "40", "41", "42",
     "48", "49", "50", "51", "52", "53", "54", "55"})
_REQUIRED = ("Kod", "Pay", "Payda")


class SymbTrFormatError(ValueError):
    """The file is not a SymbTr .txt score (missing header columns)."""


@dataclass(frozen=True)
class Note:
    koma53: int        # absolute pitch in commas (1/53 octave), in the column that was read
    duration: float    # in whole notes (Pay / Payda)


@dataclass(frozen=True)
class Score:
    name: str
    makam_label: str | None   # from the file name; a label, not ground truth
    notes: tuple[Note, ...]
    pitch_column: str = DEFAULT_PITCH_COLUMN
    skipped_rows: int = 0     # rows that should have been notes but could not be parsed


def label_from_filename(path: str | Path) -> str | None:
    stem = Path(path).stem
    return stem.split("--")[0] if "--" in stem else None


def read_symbtr_txt(path: str | Path, pitch_column: str = DEFAULT_PITCH_COLUMN) -> Score:
    if pitch_column not in PITCH_COLUMNS:
        raise ValueError(f"pitch_column must be one of {PITCH_COLUMNS}, got {pitch_column!r}")
    notes: list[Note] = []
    skipped = 0
    # utf-8-sig: tolerate a BOM. QUOTE_NONE: a quote character in the lyrics
    # column must not make the csv module swallow the rows that follow it.
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
        header = reader.fieldnames or []
        missing = [c for c in (*_REQUIRED, pitch_column) if c not in header]
        if missing:
            raise SymbTrFormatError(
                f"{Path(path).name}: not a SymbTr .txt score, missing column(s) {', '.join(missing)}")
        for row in reader:
            kod = (row.get("Kod") or "").strip()
            if kod in GRACE_CODES or kod in CONTROL_CODES:
                continue
            try:
                k = int(row[pitch_column])
                pay, payda = float(row["Pay"]), float(row["Payda"])
            except (TypeError, ValueError):
                skipped += 1
                continue
            if k <= 0 or pay <= 0 or payda <= 0:     # rests are encoded as -1; marks have no duration
                continue
            notes.append(Note(k, pay / payda))
    return Score(Path(path).stem, label_from_filename(path), tuple(notes), pitch_column, skipped)
