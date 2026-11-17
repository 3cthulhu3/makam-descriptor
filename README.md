# Makam Descriptor

A culture-aware description tool for Turkish makam music, designed to be called by an LLM agent (the MML MIR Supertool). It describes a score in the tradition's own terms, at 53-comma resolution, and says so when a piece falls outside what it knows.

Status: **v0.3, Phase 0.** Scores only (SymbTr `.txt`). Theory layer: 7 makams, AEU, **unreviewed**.

## Architecture

| Layer | Module | Status of its content |
| --- | --- | --- |
| Theory | `data/theory_aeu.toml`, `theory.py` | **Postulated.** Makams composed from cins, validated on load. Each entry names its source system and reviewers. Variants may declare the melodic direction in which they are used. The file names the SymbTr pitch column written in its own system. |
| Measurement | `measure.py`, `symbtr.py` | **Measured.** Karar = final note; duration-weighted 53-bin distribution relative to it, also split by direction of departure (next note of a different pitch lower or higher). Every sounding note counts. |
| Consistency | `consistency.py` | **Derived.** Ranking: exact comma positions on the dizi. Abstention: ±1 comma on dizi + declared variants (a directional variant counts only for notes moving in its direction), threshold 0.90, fixed before the first run and never tuned. Naming: only the best dizi fit may be named. |
| Tool interface | `tool.py` | `describe(path)` → strict-JSON dict; `call_tool(arguments)` never raises; `TOOL_SPEC` for function calling. |
| Baseline | `western.py` | Krumhansl–Kessler on the 53→12 projection, for side-by-side comparison. |

```bash
pip install -e ".[dev]"                     # optional: pytest and eval also run from a plain checkout
pytest
python -m makam_descriptor path/to/SymbTr/txt/hicaz--sarki--....txt
python eval/run_eval.py path/to/SymbTr/txt                 # dev split, 'frequency' unknowns
python eval/render_readme_tables.py                        # the tables below, from eval/{dev,test}/*.json
```

SymbTr is not included (CC BY-NC-SA). Clone it separately: `git clone https://github.com/MTG/SymbTr`. Figures below: SymbTr 2.4.3, commit `246bbe3`; the tool reads all 2200 scores without error.

## Data protocol

From v0.3 on, SymbTr is split **by composer** into dev and test (`eval/make_split.py`, manifest `eval/split_v1.json`): a composer, or for anonymous pieces a piece name, goes to test iff a salted SHA-256 of its name falls below 0.30. The rule was fixed before any result on the split was seen; nothing is stratified or hand-picked. 1604 dev / 596 test scores. Whole composers are held out, so test also measures transfer to unseen composers.

Development and every decision use dev (`--split dev`, the default). Test is opened once per release. For v0.3 it was opened once, for v0.2 and v0.3 together, after all v0.3 changes were committed.

Everything before v0.3 (v0.1, v0.2 and their ablations in `eval/v0.1/`, `eval/v0.2/`, `eval/ablation/`) was developed and evaluated on all of SymbTr. Those numbers are kept for the history, not as held-out results.

## What the output means

- `abstain: true` — no applicable makam covers the piece. Name nothing.
- `top_makam` — the best dizi fit, if what the theory says about it covers the piece. `null` on an exact tie or a naming conflict.
- `naming_conflict: true` — the best dizi fit is not covered by its own theory entry, while another makam is. Neither is named; both are in `makam_candidates`.
- `ambiguous: true` — more than one candidate. The pitch content does not decide; report all of `makam_candidates`.
- `accepted_via_variants: true` — the named makam covers the piece only with a declared variant; `fits[].variant_in_declared_direction` says how much of the variant's weight moves in the direction the theory declares.

For an agent, the figure that matters most is **named wrong, unflagged**: a single makam named, no ambiguity signal, and wrong.

## Results (v0.3)

`n` = known / `frequency` unknowns / `proposal` unknowns. `frequency` is the nine most frequent SymbTr makams outside the theory, unselected; `proposal` is the six behind the original proposal's figures, all of which differ from every known makam in their dizi.

| Split | Rules | named right | named wrong | …of which unflagged | naming conflict | abstains, known | abstains, `frequency` | AUROC | abstains, `proposal` | AUROC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (n = 522 / 461 / 316) | v0.2 | 86.6 % | 8.2 % | 2.5 % | 0.0 % | 2.5 % | 70.7 % | 0.866 | 89.6 % | 0.984 |
| dev (n = 522 / 461 / 316) | + naming rule | 86.2 % | 7.7 % | 1.9 % | 1.0 % | 2.5 % | 70.7 % | 0.866 | 89.6 % | 0.984 |
| dev (n = 522 / 461 / 316) | + direction = v0.3 | 86.2 % | 7.7 % | 1.9 % | 0.8 % | 2.7 % | 70.9 % | 0.879 | 89.9 % | 0.983 |
| test (n = 229 / 187 / 140) | v0.2 | 86.0 % | 9.2 % | 3.1 % | 0.0 % | 2.2 % | 74.3 % | 0.918 | 84.3 % | 0.983 |
| test (n = 229 / 187 / 140) | + direction = v0.3 | 85.6 % | 7.9 % | 1.7 % | 1.3 % | 2.6 % | 76.5 % | 0.921 | 87.1 % | 0.980 |

Scale of the test differences: one known piece is 0.44 points, one `frequency` unknown 0.53. The v0.2 → v0.3 change on test (named wrong 21 → 18, unflagged 7 → 4, `frequency` flagged 139 → 143) is in the expected direction and small. Ranking top-1 is 87.9 % on dev and 87.8 % on test: the tool has no fitted parameters, and it transfers to unseen composers without loss.

Per makam, test:

| Makam | n | top-1 | tie | in set | abstains | named right | named wrong | …unflagged |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rast | 34 | 97.1 % | 0.0 % | 97.1 % | 5.9 % | 91.2 % | 2.9 % | 2.9 % |
| mâhur | 21 | 95.2 % | 0.0 % | 100.0 % | 0.0 % | 85.7 % | 4.8 % | 0.0 % |
| nihâvend | 43 | 100.0 % | 0.0 % | 100.0 % | 0.0 % | 100.0 % | 0.0 % | 0.0 % |
| uşşak | 33 | 57.6 % | 18.2 % | 93.9 % | 3.0 % | 57.6 % | 21.2 % | 3.0 % |
| hüseynî | 30 | 66.7 % | 0.0 % | 90.0 % | 3.3 % | 66.7 % | 26.7 % | 6.7 % |
| hicâz | 47 | 97.9 % | 0.0 % | 97.9 % | 2.1 % | 95.7 % | 2.1 % | 0.0 % |
| bûselik | 21 | 95.2 % | 0.0 % | 95.2 % | 4.8 % | 95.2 % | 0.0 % | 0.0 % |

| Unknown makam | n | flagged | karar known | named as |
| --- | --- | --- | --- | --- |
| hüzzam | 25 | 100.0 % | 0 | — |
| segâh | 28 | 100.0 % | 0 | — |
| hicazkâr | 22 | 100.0 % | 21 | — |
| kürdîlihicazkâr | 25 | 80.0 % | 24 | nihâvend 5 |
| muhayyer | 15 | 0.0 % | 15 | hüseynî 11, uşşak 3, tie 1 |
| sabâ | 25 | 84.0 % | 25 | conflict 2, uşşak 2 |
| acemaşîrân | 20 | 100.0 % | 0 | — |
| bayâtî | 12 | 8.3 % | 11 | uşşak 6, hüseynî 3, conflict 1, bûselik 1 |
| karcığar | 15 | 40.0 % | 15 | hüseynî 6, tie 1, bûselik 1, conflict 1 |

Leave-one-makam-out, test: nihâvend 100 %, hicâz 98 %, hüseynî 20 %, bûselik 10 %, rast 6 %, uşşak 3 %, mâhur 0 %.

### What these numbers say

1. **Uşşak and hüseynî are told apart about two times in three.** Their dizi differ in one degree (acem / eviç), and both makams use both pitches. This is the tool's largest error mass and the main source of wrong names. Pitch content cannot fix it; the güçlü can (hüseynî/nevâ duration ratio, median 1.24 in hüseynî against 0.50 in uşşak, all of SymbTr).
2. **Novelty in the scale is detected, novelty in melodic behaviour is not.** Muhayyer and bayâtî have the dizi of hüseynî and uşşak and differ in seyir; they are almost never flagged. On dev, 135 unknown pieces were accepted: 119 on a dizi alone, which no variant rule can touch, and 16 only through a variant.
3. **A makam with a one-comma neighbour in the theory is absorbed, not flagged** (rast ↔ mâhur, uşşak ↔ hüseynî ↔ bûselik). The abstention claim holds for makams whose scale is new to the theory, not in general.
4. The "Western r" AUROC column of earlier versions is dropped from the headline: a key-profile correlation was never meant as a novelty score. It is still in the JSON (`auroc_western_correlation`).

## History

### v0.2 → v0.3

1. **Naming rule.** In v0.2 a makam was named from among those whose coverage (dizi + declared variants) passed the threshold. Variants declared for one makam could then take pieces from a neighbour that declares none: on all of SymbTr, 9 pieces were named differently from their best dizi fit, 4 of them mâhur pieces named rast through rast's acem variant; 3 of the 9 names were right, against 5 for the best fit. Coverage now decides *whether* a makam may be named, never *which*; a conflict yields `top_makam: null` and both candidates.
2. **Direction-conditioned variants.** The theory's `descending_acem` variants (rast, hüseynî, hicâz) are now applied only to notes that depart downward. Checked on dev only: acem departs downward in 87 % (hicâz), 93 % (rast) and 86 % (hüseynî) of its duration; eviç, the dizi degree beside it, in 38–44 %. The textbook rule is borne out, and the variant is now a claim a piece can contradict. Its effect on the aggregate is small: of the 16 dev unknowns accepted through a variant, 12 pass through nihâvend's and bûselik's leading-tone variants, which stay direction-free (see the reviewer questions).
3. **Evaluation.** Dev/test split; `--unknown` defaults to the unselected `frequency` set; the script always evaluates the checkout it lives in (before, an installed older version silently took precedence); AUROC quantises scores to 1e-9 (in v0.2, 45 of the 412 fully covered SymbTr scores came out as 1 ± 2·10⁻¹⁶ depending on summation order, and AUROC broke ties on that; effect up to 0.003).

`Params(name_best_fit_only=False, variant_direction=False)` and `--v02-naming --no-direction` restore v0.2.

### v0.1 → v0.2 (all of SymbTr, pre-split)

| Stage | top-1 | tie at top | abstains, known | named right | abstains, `proposal` | AUROC | abstains, `frequency` | AUROC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0.1 as shipped | 85.6 % | not counted | 13.2 % | 74.4 % | 94.5 % | 0.964 | 77.2 % | 0.862 |
| 1. reader fixed, ties counted | 74.6 % | 17.2 % | 12.9 % | 72.8 % | 93.9 % | 0.965 | 76.7 % | 0.862 |
| 2. pitch column of the theory's own system | 87.9 % | 2.7 % | 12.6 % | 77.1 % | 92.8 % | 0.962 | 75.5 % | 0.856 |
| 3. declared variants count for abstention; acem variants for rast and hicâz | 87.9 % | 2.7 % | 2.4 % | 86.4 % | 87.9 % | 0.984 | 71.8 % | 0.881 |

1. v0.1 broke ties by the order of the TOML file: 82 of its 643 top-1 hits were uşşak pieces tied with bûselik or hüseynî and listed first. It also skipped ornamented notes (2.8 % of sounding notes).
2. v0.1 compared AEU theory with SymbTr's `Koma53` column. See the next section for what that column is.
3. Taken after seeing v0.1's results, on the data it was evaluated on: a judgement, not a bug fix.

## About SymbTr's two pitch columns

SymbTr gives every note twice: `KomaAE`, the AEU notation, and `Koma53`, a 53-TET respelling. They differ on 65 666 notes. The difference is **conditioned on the makam**: the AEU segâh (`B4b1`) is written one comma lower in `Koma53` in 88 % of its occurrences in uşşak, 87 % in hüseynî, 88 % in bayâtî, 84 % in muhayyer and 88 % in sabâ, but in 2 % in rast, 1 % in segâh and 1 % in hüzzam. That matches the performance knowledge that segâh sits lower in the uşşak family. But it is an editor's respelling made knowing the makam, not a measurement of intonation.

Consequences:

- Reading `Koma53` lets a tool partly read the editor's knowledge of the label. The tool reads `KomaAE`, the column in its theory's own system.
- `Koma53` is not a route to performed intonation; recordings are (Phase 2).
- Even on `KomaAE`, a score's perde choices are the composer's: on scores "the comma is the makam" partly means "the notated perde is the makam". Score-level accuracy is an upper bound for what audio will give.

## Known limits

- Karar from the last note only (the theory's karar in 98.5 % of known-makam pieces on dev); no geçki (modulation) handling. `measure.windows()` exists but is unused.
- Güçlü emphasis is reported per fit but not used; it cannot be measured for mâhur, whose güçlü is the octave of its karar.
- Labels come from SymbTr file names; the `hicaz` label also covers hümâyun-like pieces.
- Calibration and agent benefit (questions 3 and 4 of the proposal's evaluation plan) are not measured yet.
- AEU is one theory among several; the theory layer is plural by design but holds only AEU.

## Questions for the theory reviewer

- Hicâz with descending acem is the hümâyun dizi. One entry with a variant (as now), or two makams?
- Nihâvend's eviç and bûselik's nîm zirgüle are declared as variants without a direction. On dev they depart upward in 69 % and 80 % of their duration, as leading tones would. Should they be declared ascending? (Not done: it would be a theory edit driven by the data it is evaluated on.)
- `seyir` is recorded as ascending for hicâz and as both for bûselik; common descriptions differ. Not used yet, but should be right before Phase 1 uses it.
- The three `descending_acem` variants and the two leading-tone variants are as unreviewed as the rest.

## Licence

Code: Apache-2.0. Data read at runtime (SymbTr) keeps its own licence.
