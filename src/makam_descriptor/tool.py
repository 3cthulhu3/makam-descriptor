"""Tool interface for an LLM agent (the MIR Supertool).

`describe()` returns a plain dict that is strict JSON (no NaN or Infinity).
`call_tool()` is the same thing behind a function-calling envelope: it takes the
arguments object and never raises. `TOOL_SPEC` is a generic JSON-Schema function
description; adapt the envelope once the Supertool's expected format is known
(open question 2 in the proposal).
"""
from __future__ import annotations

from pathlib import Path

from .consistency import Params, compare
from .measure import MeasurementError, measure
from .symbtr import PITCH_COLUMNS, SymbTrFormatError, read_symbtr_txt
from .theory import Theory, load_theory
from .western import key_find

__all__ = ["describe", "describe_notes", "call_tool", "TOOL_SPEC"]

_THEORY: Theory | None = None


def _theory() -> Theory:
    global _THEORY
    if _THEORY is None:
        _THEORY = load_theory()
    return _THEORY


def _r(x: float | None, nd: int) -> float | None:
    return None if x is None else round(x, nd)


def describe_notes(notes, theory: Theory | None = None, params: Params = Params()) -> dict:
    th = theory or _theory()
    m = measure(notes)
    c = compare(m, th, params)
    karar_name = th.perde_name(m.karar_pc)
    return {
        "karar": karar_name or f"comma class {m.karar_pc} (unnamed)",
        "makam_candidates": c["candidates"],
        "top_makam": c["top"],
        "ambiguous": len(c["candidates"]) > 1,
        "naming_conflict": c["naming_conflict"],
        "accepted_via_variants": c["accepted_via_variants"],
        "fits": [
            {"makam": f.makam, "display": th.makams[f.makam].display,
             "share_on_scale": round(f.exact, 3),
             "share_within_1_comma": round(f.tolerant, 3),
             "share_within_1_comma_with_variants": round(f.coverage, 3),
             "variants": {k: round(v, 3) for k, v in f.variants.items()},
             "variant_in_declared_direction": {k: _r(v, 3) for k, v in (f.variant_in_direction or {}).items()},
             "guclu": th.perde[th.makams[f.makam].guclu_perde].get("display", th.makams[f.makam].guclu_perde),
             "guclu_emphasis": _r(f.guclu_emphasis, 2)}
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
            "abstain_threshold": params.abstain_threshold,
            "abstain_tolerance_commas": params.abstain_tolerance,
            "n_notes": m.n_notes,
        },
    }


def describe(path: str | Path, theory: Theory | None = None, params: Params = Params(),
             pitch_column: str | None = None) -> dict:
    """Describe a SymbTr .txt score.

    The pitch column defaults to the one written in the theory's own system
    (KomaAE for AEU). Raises OSError, SymbTrFormatError or MeasurementError.
    """
    th = theory or _theory()
    score = read_symbtr_txt(path, pitch_column or th.symbtr_column)
    out = describe_notes(score.notes, th, params)
    out["input"] = {"name": score.name, "format": "symbtr-txt"}
    out["provenance"]["pitch_column"] = score.pitch_column
    out["provenance"]["unparsed_rows"] = score.skipped_rows
    return out


def call_tool(arguments: dict) -> dict:
    """Function-calling entry point: returns the description, or {"error": ...}. Never raises."""
    try:
        path = arguments["path"]
        column = arguments.get("pitch_column")
        if not isinstance(path, str) or (column is not None and column not in PITCH_COLUMNS):
            raise TypeError
    except (KeyError, TypeError, AttributeError):
        return {"error": {"type": "bad_arguments",
                          "message": f"expected an object with a string 'path' and, optionally, "
                                     f"'pitch_column' in {list(PITCH_COLUMNS)}"}}
    try:
        return describe(path, pitch_column=column)
    except FileNotFoundError:
        return {"error": {"type": "file_not_found", "message": f"no such file: {arguments.get('path')}"}}
    except SymbTrFormatError as e:
        return {"error": {"type": "bad_format", "message": str(e)}}
    except MeasurementError as e:
        return {"error": {"type": "no_notes", "message": str(e)}}
    except (OSError, UnicodeDecodeError, ValueError) as e:
        return {"error": {"type": "unreadable", "message": str(e)}}


TOOL_SPEC = {
    "name": "makam_descriptor",
    "description": (
        "Describe a Turkish makam music score in the tradition's own terms (53-comma "
        "resolution). Returns the karar, candidate makams with fit scores, the share of "
        "the piece outside every known scale, and an explicit abstain flag. If abstain "
        "is true, do not name a makam. If ambiguous is true, or top_makam is null, the "
        "pitch content does not decide between the candidates: name them all, not one. "
        "naming_conflict means the best-fitting makam is not covered by its own theory "
        "entry while another candidate is; treat it as ambiguous. "
        "The tool compares pitch content only; it cannot tell apart makams that share a "
        "scale and differ in melodic progression (seyir). Also returns a Western "
        "key-finder answer on the same input for comparison; that answer is computed "
        "after rounding to 12 semitones and is not a makam analysis. On failure the "
        "result is an object with a single 'error' key."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to a SymbTr .txt score"},
            "pitch_column": {
                "type": "string", "enum": list(PITCH_COLUMNS),
                "description": "SymbTr pitch column to read. Omit to use the column written in "
                               "the theory's own system (KomaAE for AEU).",
            },
        },
        "required": ["path"],
    },
}
