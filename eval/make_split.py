"""Freeze a composer-level dev/test split of SymbTr (run once; the manifest is committed).

Rule, fixed before any evaluation on it:
  * group = composer (5th field of the SymbTr file name); anonymous pieces
    (empty composer) are grouped by piece name (4th field), so versions of the
    same tune stay together;
  * a group goes to test iff sha256("makam-descriptor/split-v1/" + group),
    read as a 32-bit fraction, is below 0.30.
No stratification, no inspection of results: the hash decides. Whole composers
are held out, so the test set also measures transfer to unseen composers.

Usage: python eval/make_split.py SymbTr/txt eval/split_v1.json
"""
import hashlib
import json
import sys
from pathlib import Path

SALT, TEST_SHARE = "makam-descriptor/split-v1/", 0.30


def group_of(name: str) -> str:
    parts = name.split("--")
    composer = parts[4] if len(parts) > 4 else ""
    return f"composer:{composer}" if composer else f"anon:{parts[3] if len(parts) > 3 else name}"


def is_test(group: str) -> bool:
    h = int(hashlib.sha256((SALT + group).encode("utf-8")).hexdigest()[:8], 16)
    return h / 2**32 < TEST_SHARE


def main(txt_dir: str, out: str) -> None:
    names = sorted(p.stem for p in Path(txt_dir).glob("*.txt"))
    split = {"dev": [], "test": []}
    for n in names:
        split["test" if is_test(group_of(n)) else "dev"].append(n)
    manifest = {
        "rule": __doc__.split("Usage")[0].strip(),
        "salt": SALT, "test_share": TEST_SHARE,
        "n": {k: len(v) for k, v in split.items()},
        **split,
    }
    Path(out).write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(manifest["n"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
