# Makam Descriptor

A culture-aware description tool for Turkish makam music, designed to be called by an LLM agent (the MML MIR Supertool). It describes a score in the tradition's own terms, at 53-comma resolution, and says so when a piece falls outside what it knows.

Status: **v0.1, Phase 0 rebuilt as a package.** Scores only (SymbTr `.txt`). Theory layer: 7 makams, AEU, unreviewed.

## Architecture

| Layer | Module | Status of its content |
| --- | --- | --- |
| Theory | `data/theory_aeu.toml`, `theory.py` | **Postulated.** Makams composed from cins, validated on load (dizi = 53 commas, güçlü is a degree). Each entry names its source system and reviewers. |
| Measurement | `measure.py`, `symbtr.py` | **Measured.** Karar = final note; duration-weighted 53-bin distribution relative to it. |
| Consistency | `consistency.py` | **Derived.** Identification at exact comma positions; abstention with ±1 comma slack, threshold 0.90 (fixed before the first run, not tuned). |
| Tool interface | `tool.py` | `describe(path)` → JSON-serialisable dict; `TOOL_SPEC` for function calling. |
| Baseline | `western.py` | Krumhansl–Kessler on the 53→12 projection, for side-by-side comparison. |

```bash
pip install -e ".[dev]"
python -m makam_descriptor path/to/SymbTr/txt/hicaz--sarki--....txt
python eval/run_eval.py path/to/SymbTr/txt --unknown proposal    # or: frequency
pytest
```

SymbTr is not included (CC BY-NC-SA). Clone it separately: `git clone https://github.com/MTG/SymbTr`.

## Results (v0.1, SymbTr master, 751 scores in 7 known makams)

Identification (ranking, regardless of abstention): top-1 **85.6 %**, true makam in candidate set **96.5 %** (mean set size 1.49). Abstention on known makams: **13.2 %** (hicaz 28 %, nihavent 17 %). Accepted *and* correct: **74.4 %**.

Abstention depends strongly on which makams count as "unknown":

| Unknown set | n | Abstain | Abstain, karar known | AUROC | AUROC, karar known | AUROC, Western r |
| --- | --- | --- | --- | --- | --- | --- |
| `proposal`: hüzzam, segah, hicazkâr, kürdîlihicazkâr, sabâ, karcığar | 456 | 94.5 % | 90.3 % | 0.964 | 0.942 | 0.702 |
| `frequency`: the 9 most frequent makams outside the theory, unselected | 648 | 77.2 % | 61.6 % | 0.862 | 0.772 | 0.640 |

The difference is almost entirely muhayyer (abstains 1 %) and bayâtî (8 %). At pitch-set resolution their dizi coincide with hüseynî and uşşak; they differ in seyir. **A pitch-distribution tool can detect novelty in the scale, not in melodic behaviour.** Phase 1's güçlü and seyir features are meant to close this.

Leave-one-makam-out (remove a makam from the theory, check its pieces are flagged): nihâvend 100 %, hicâz 99 %; rast 10 % (absorbed by mâhur), mâhur 9 % (absorbed by rast), uşşak 8 %, bûselik 14 %, hüseynî 21 %. Makams with a one-comma neighbour in the theory are absorbed, not flagged.

## Known limits

- Karar from the last note only; no geçki (modulation) handling, so modulating pieces over-abstain (hicaz).
- Hüseynî vs uşşak is decided in emphasis, not scale (hüseynî/nevâ duration ratio, median 1.24 vs 0.50); not yet a feature.
- Labels come from SymbTr file names.
- AEU is one theory among several; the theory layer is plural by design but holds only AEU so far.

## Licence

Code: Apache-2.0. Data read at runtime (SymbTr) keeps its own licence.
