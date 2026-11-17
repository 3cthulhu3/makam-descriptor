"""Command line: python -m makam_descriptor SCORE.txt [SCORE.txt ...]

One score prints one JSON object; several print a JSON array, in order. A score
that cannot be read becomes an {"error": ...} entry and the exit status is 1.
"""
import argparse
import json
import sys

from .symbtr import PITCH_COLUMNS
from .tool import call_tool


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m makam_descriptor", description="Describe SymbTr .txt scores.")
    ap.add_argument("scores", nargs="+", metavar="SCORE.txt")
    ap.add_argument("--pitch-column", choices=PITCH_COLUMNS,
                    help="SymbTr pitch column (default: the one written in the theory's system)")
    a = ap.parse_args(argv)
    results = []
    for p in a.scores:
        out = call_tool({"path": p, "pitch_column": a.pitch_column})
        if "error" in out:
            out["input"] = {"name": p}
        results.append(out)
    doc = results[0] if len(results) == 1 else results
    print(json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if any("error" in r for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
