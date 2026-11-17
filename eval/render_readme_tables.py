"""Print the README result tables from eval/{dev,test}/*.json, so the README never drifts from them."""
import json
from pathlib import Path

E = Path(__file__).resolve().parent
pct = lambda x: "–" if x is None else f"{100 * x:.1f} %"  # noqa: E731
NAMES = {"rast": "rast", "mahur": "mâhur", "nihavent": "nihâvend", "ussak": "uşşak", "huseyni": "hüseynî",
         "hicaz": "hicâz", "buselik": "bûselik", "huzzam": "hüzzam", "segah": "segâh", "hicazkar": "hicazkâr",
         "kurdilihicazkar": "kürdîlihicazkâr", "muhayyer": "muhayyer", "saba": "sabâ",
         "acemasiran": "acemaşîrân", "beyati": "bayâtî", "karcigar": "karcığar"}


def j(split, unknown, stage):
    p = E / split / f"{unknown}_{stage}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def headline():
    print("| Split | Rules | named right | named wrong | …of which unflagged | naming conflict | abstains, known "
          "| abstains, `frequency` | AUROC | abstains, `proposal` | AUROC |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for split in ("dev", "test"):
        for stage, label in (("v02", "v0.2"), ("naming", "+ naming rule"), ("v03", "+ direction = v0.3")):
            f, p = j(split, "frequency", stage), j(split, "proposal", stage)
            if not f:
                continue
            i, a, pa = f["identification"], f["abstention"], p["abstention"]
            print(f"| {split} (n = {f['n_known']} / {f['n_unknown']} / {p['n_unknown']}) | {label} "
                  f"| {pct(i['accepted_and_correct'])} | {pct(i['accepted_and_wrong'])} "
                  f"| {pct(i['accepted_and_wrong_unflagged'])} | {pct(i['naming_conflict'])} "
                  f"| {pct(i['abstain_rate_known'])} | {pct(a['abstain_rate_unknown'])} | {a['auroc']:.3f} "
                  f"| {pct(pa['abstain_rate_unknown'])} | {pa['auroc']:.3f} |")


def per_makam(split="test"):
    f = j(split, "frequency", "v03")
    print("| Makam | n | top-1 | tie | in set | abstains | named right | named wrong | …unflagged |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for mk, v in f["per_makam"].items():
        if "top1" in v:
            print(f"| {NAMES[mk]} | {v['n']} | {pct(v['top1'])} | {pct(v['tied_top'])} | {pct(v['in_set'])} "
                  f"| {pct(v['abstain'])} | {pct(v['accepted_correct'])} | {pct(v['accepted_wrong'])} "
                  f"| {pct(v['accepted_wrong_unflagged'])} |")
    print()
    print("| Unknown makam | n | flagged | karar known | named as |")
    print("| --- | --- | --- | --- | --- |")
    for mk, v in f["per_makam"].items():
        if "named_as" in v:
            named = ", ".join(f"{NAMES.get(k, k)} {n}" for k, n in v["named_as"].items()) or "—"
            print(f"| {NAMES[mk]} | {v['n']} | {pct(v['abstain'])} | {v['n_karar_known']} | {named} |")
    print()
    lomo = ", ".join(f"{NAMES[k]} {100 * v['flagged']:.0f} %" for k, v in
                     sorted(f["leave_one_makam_out"].items(), key=lambda kv: -kv[1]["flagged"]))
    print(f"Leave-one-makam-out, {split}: {lomo}.")


if __name__ == "__main__":
    headline()
    print()
    per_makam("test")
