import json
import sys

from .tool import describe

if len(sys.argv) < 2:
    sys.exit("usage: python -m makam_descriptor SCORE.txt [SCORE.txt ...]")
for p in sys.argv[1:]:
    print(json.dumps(describe(p), ensure_ascii=False, indent=2))
