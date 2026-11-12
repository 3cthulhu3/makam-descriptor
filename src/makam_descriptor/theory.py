"""Theory layer: makam definitions as data.

Everything here is *postulated*: it encodes what a theoretical system says a
makam is. Nothing is fitted to data. Scales are composed from cins
(tetrachords/pentachords) exactly as the theory composes them, and validated
on load (intervals sum to one octave, all perde names resolve).
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

COMMAS = 53


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


@dataclass(frozen=True)
class Theory:
    system: str
    perde: dict[str, dict]
    makams: dict[str, Makam]

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
        return Theory(self.system, self.perde,
                      {k: m for k, m in self.makams.items() if k not in keys})


class TheoryError(ValueError):
    pass


def _rel(pc: int, karar_pc: int) -> int:
    return (pc - karar_pc) % COMMAS


def load_theory(path: str | Path | None = None) -> Theory:
    if path is None:
        raw = resources.files("makam_descriptor.data").joinpath("theory_aeu.toml").read_bytes()
        data = tomllib.loads(raw.decode("utf-8"))
    else:
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))

    n = data["meta"].get("comma_per_octave", COMMAS)
    if n != COMMAS:
        raise TheoryError(f"only 53-comma theories are supported, got {n}")
    perde, cins = data["perde"], data["cins"]

    def pc_of(name: str, where: str) -> int:
        if name not in perde:
            raise TheoryError(f"{where}: unknown perde '{name}'")
        return perde[name]["pc"]

    makams: dict[str, Makam] = {}
    for key, e in data["makam"].items():
        karar_pc = pc_of(e["karar"], key)
        intervals: list[int] = []
        for c in e["dizi"]:
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
            Variant(v["name"], frozenset(_rel(pc_of(p, key), karar_pc) for p in v["add"]), v.get("note", ""))
            for v in e.get("variants", [])
        )
        guclu_rel = _rel(pc_of(e["guclu"], key), karar_pc)
        if guclu_rel not in degrees:
            raise TheoryError(f"{key}: güçlü '{e['guclu']}' is not a scale degree")
        makams[key] = Makam(
            key=key, display=e.get("display", key), karar_perde=e["karar"], karar_pc=karar_pc,
            intervals=tuple(intervals), degrees=frozenset(degrees), guclu_perde=e["guclu"],
            guclu_rel=guclu_rel, seyir=e.get("seyir", "unknown"), source=e["source"],
            reviewers=tuple(e.get("reviewers", [])), variants=variants,
        )
    return Theory(data["meta"]["system"], perde, makams)
