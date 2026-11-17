"""Theory layer: makam definitions as data.

Everything here is *postulated*: it encodes what a theoretical system says a
makam is. Nothing is fitted to data. Scales are composed from cins
(tetrachords/pentachords) exactly as the theory composes them, and validated
on load (intervals sum to one octave, all perde names resolve).
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from importlib import resources
from pathlib import Path

from .symbtr import DEFAULT_PITCH_COLUMN, PITCH_COLUMNS

COMMAS = 53
SEYIR_VALUES = ("ascending", "descending", "both", "unknown")


@dataclass(frozen=True)
class Variant:
    name: str
    add: frozenset[int]          # extra degrees, relative to karar
    note: str


@dataclass(frozen=True)
class Makam:
    key: str
    display: str
    karar_perde: str
    karar_pc: int                # pitch class of the karar, mod 53
    intervals: tuple[int, ...]   # successive intervals from karar, sum = 53
    degrees: frozenset[int]      # scale degrees relative to karar, mod 53
    guclu_perde: str
    guclu_rel: int               # güçlü relative to karar, mod 53
    seyir: str
    source: str
    reviewers: tuple[str, ...]
    variants: tuple[Variant, ...] = field(default_factory=tuple)

    def degrees_with(self, *variant_names: str) -> frozenset[int]:
        out = set(self.degrees)
        for v in self.variants:
            if v.name in variant_names:
                out |= v.add
        return frozenset(out)

    @property
    def degrees_with_all_variants(self) -> frozenset[int]:
        return self.degrees_with(*(v.name for v in self.variants))


@dataclass(frozen=True, eq=False)
class Theory:
    system: str
    perde: dict[str, dict]
    makams: dict[str, Makam]
    symbtr_column: str = DEFAULT_PITCH_COLUMN   # the SymbTr pitch column written in this system

    def by_karar(self, karar_pc: int) -> list[Makam]:
        return [m for m in self.makams.values() if m.karar_pc == karar_pc % COMMAS]

    @property
    def karar_pcs(self) -> set[int]:
        return {m.karar_pc for m in self.makams.values()}

    def perde_name(self, pc: int) -> str | None:
        for name, p in self.perde.items():
            if p["pc"] == pc % COMMAS:
                return p.get("display", name)
        return None

    def without(self, *keys: str) -> "Theory":
        """Theory with some makams removed (for leave-one-makam-out tests)."""
        return replace(self, makams={k: m for k, m in self.makams.items() if k not in keys})


class TheoryError(ValueError):
    pass


def _rel(pc: int, karar_pc: int) -> int:
    return (pc - karar_pc) % COMMAS


def _need(table: dict, key: str, where: str):
    if not isinstance(table, dict) or key not in table:
        raise TheoryError(f"{where}: missing '{key}'")
    return table[key]


def load_theory(path: str | Path | None = None) -> Theory:
    if path is None:
        raw = resources.files("makam_descriptor.data").joinpath("theory_aeu.toml").read_bytes()
        text = raw.decode("utf-8")
    else:
        text = Path(path).read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise TheoryError(f"theory file is not valid TOML: {e}") from e

    meta = _need(data, "meta", "theory file")
    system = _need(meta, "system", "[meta]")
    n = meta.get("comma_per_octave", COMMAS)
    if n != COMMAS:
        raise TheoryError(f"only 53-comma theories are supported, got {n}")
    column = meta.get("symbtr_column", DEFAULT_PITCH_COLUMN)
    if column not in PITCH_COLUMNS:
        raise TheoryError(f"[meta] symbtr_column must be one of {PITCH_COLUMNS}, got {column!r}")
    perde = _need(data, "perde", "theory file")
    cins = _need(data, "cins", "theory file")
    entries = _need(data, "makam", "theory file")

    for name, p in perde.items():
        pc = _need(p, "pc", f"perde '{name}'")
        if not isinstance(pc, int) or isinstance(pc, bool) or not 0 <= pc < COMMAS:
            raise TheoryError(f"perde '{name}': pc must be an integer in 0..{COMMAS - 1}, got {pc!r}")
    for name, c in cins.items():
        iv = _need(c, "intervals", f"cins '{name}'")
        if not iv or any(not isinstance(i, int) or isinstance(i, bool) or i <= 0 for i in iv):
            raise TheoryError(f"cins '{name}': intervals must be positive integers, got {iv!r}")

    def pc_of(name: str, where: str) -> int:
        if name not in perde:
            raise TheoryError(f"{where}: unknown perde '{name}'")
        return perde[name]["pc"]

    makams: dict[str, Makam] = {}
    for key, e in entries.items():
        karar_pc = pc_of(_need(e, "karar", key), key)
        intervals: list[int] = []
        for c in _need(e, "dizi", key):
            if c not in cins:
                raise TheoryError(f"{key}: unknown cins '{c}'")
            intervals += cins[c]["intervals"]
        if sum(intervals) != COMMAS:
            raise TheoryError(f"{key}: dizi spans {sum(intervals)} commas, expected {COMMAS}")
        degrees, acc = {0}, 0
        for i in intervals[:-1]:
            acc += i
            degrees.add(acc)
        variants = tuple(
            Variant(_need(v, "name", f"{key} variant"),
                    frozenset(_rel(pc_of(p, key), karar_pc) for p in _need(v, "add", f"{key} variant")),
                    v.get("note", ""))
            for v in e.get("variants", [])
        )
        if len({v.name for v in variants}) != len(variants):
            raise TheoryError(f"{key}: duplicate variant name")
        guclu = _need(e, "guclu", key)
        guclu_rel = _rel(pc_of(guclu, key), karar_pc)
        if guclu_rel not in degrees:
            raise TheoryError(f"{key}: güçlü '{guclu}' is not a scale degree")
        seyir = e.get("seyir", "unknown")
        if seyir not in SEYIR_VALUES:
            raise TheoryError(f"{key}: seyir must be one of {SEYIR_VALUES}, got {seyir!r}")
        makams[key] = Makam(
            key=key, display=e.get("display", key), karar_perde=e["karar"], karar_pc=karar_pc,
            intervals=tuple(intervals), degrees=frozenset(degrees), guclu_perde=guclu,
            guclu_rel=guclu_rel, seyir=seyir, source=_need(e, "source", key),
            reviewers=tuple(e.get("reviewers", [])), variants=variants,
        )
    return Theory(system, perde, makams, column)
