"""Tool interface for an LLM agent (the MIR Supertool).

`describe()` returns a plain JSON-serialisable dict. `TOOL_SPEC` is a generic
JSON-Schema function description; adapt the envelope once the Supertool's
expected format is known (open question 2 in the proposal).
"""
from __future__ import annotations

from pathlib import Path

from .consistency import Params, compare
from .measure import measure
from .symbtr import Note, read_symbtr_txt
from .theory import Theory, load_theory
from .western import key_find

__all__ = ["describe", "describe_notes", "TOOL_SPEC"]

_THEORY: Theory | None = None


def _theory() -> Theory:
    global _THEORY
    if _THEORY is None:
        _THEORY = load_theory()
    return _THEORY


def describe_notes(notes, theory: Theory | None = None, params: Params = Params()) -> dict:
    th = theory or _theory()
    m = measure(notes)
    c = compare(m, th, params)
    karar_name = th.perde_name(m.karar_pc)
    return {
        "karar": karar_name or f"comma class {m.karar_pc} (unnamed)",
        "makam_candidates": c["candidates"],
        "top_makam": c["top"],
        "fits": [
            {"makam": f.makam, "share_on_scale": round(f.exact, 3),
             "share_within_1_comma": round(f.tolerant, 3),
             "variants": {k: round(v, 3) for k, v in f.variants.items()},
             "guclu_emphasis": round(f.guclu_emphasis, 2)}
            for f in c["fits"]
        ],
        "out_of_theory_share": c["out_of_theory_share"],
        "abstain": c["abstain"],
        "abstain_reasons": c["reasons"],
        "western_baseline": key_find(m.abs_pcd),
        "provenance": {
            "theory_system": th.system,
            "theory_reviewed": all(th.makams[k].reviewers for k in c["candidates"]) if c["candidates"] else False,
            "karar_method": "final note (score input)",
            "n_notes": m.n_notes,
        },
    }


def describe(path: str | Path, theory: Theory | None = None, params: Params = Params()) -> dict:
    score = read_symbtr_txt(path)
    out = describe_notes(score.notes, theory, params)
    out["input"] = {"name": score.name, "format": "symbtr-txt"}
    return out


TOOL_SPEC = {
    "name": "makam_descriptor",
    "description": (
        "Describe a Turkish makam music score in the tradition's own terms (53-comma "
        "resolution). Returns the karar, candidate makams with fit scores, the share of "
        "the piece outside every known scale, and an explicit abstain flag. Also returns "
        "a Western key-finder answer on the same input for comparison; that answer is "
        "computed after rounding to 12 semitones and is not a makam analysis. If "
        "abstain is true, do not name a makam."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path to a SymbTr .txt score"}},
        "required": ["path"],
    },
}
