# Makam Descriptor

A culture-aware description tool for Turkish makam music, designed to be called by an LLM agent (the MML MIR Supertool). It describes a score in the tradition's own terms, at 53-comma resolution, and says so when a piece falls outside what it knows.

Status: **v0.2, Phase 0.** Scores only (SymbTr `.txt`). Theory layer: 7 makams, AEU, unreviewed.

## Architecture

| Layer | Module | Status of its content |
| --- | --- | --- |
| Theory | `data/theory_aeu.toml`, `theory.py` | **Postulated.** Makams composed from cins, validated on load (dizi = 53 commas, güçlü is a degree). Each entry names its source system and reviewers. The file also names the SymbTr pitch column written in its own system. |
| Measurement | `measure.py`, `symbtr.py` | **Measured.** Karar = final note; duration-weighted 53-bin distribution relative to it. Every sounding note counts, ornamented or not. |
| Consistency | `consistency.py` | **Derived.** Identification at exact comma positions on the dizi; abstention with ±1 comma slack on dizi + declared variants, threshold 0.90 (fixed before the first run, never tuned). |
| Tool interface | `tool.py` | `describe(path)` → strict-JSON dict; `call_tool(arguments)` never raises; `TOOL_SPEC` for function calling. |
| Baseline | `western.py` | Krumhansl–Kessler on the 53→12 projection, for side-by-side comparison. |

```bash
pip install -e ".[dev]"
python -m makam_descriptor path/to/SymbTr/txt/hicaz--sarki--....txt
python eval/run_eval.py path/to/SymbTr/txt --unknown proposal    # or: frequency
pytest
```

`pytest` and `eval/run_eval.py` also run from a plain checkout, without the install.

SymbTr is not included (CC BY-NC-SA). Clone it separately: `git clone https://github.com/MTG/SymbTr`. The figures below are from SymbTr 2.4.3 (commit `246bbe3`), all 2200 scores of which the tool reads without error.

## What the output means

- `abstain: true` — no applicable makam covers the piece. Name nothing.
- `top_makam` — the single best fit among the makams that cover the piece; `null` on an exact tie.
- `ambiguous: true` — more than one candidate within the margin. The pitch content does not decide; report all of `makam_candidates`.
- `accepted_via_variants: true` — the piece leaves the dizi and stays inside a variant the theory declares (see `fits[].variants`).

## Results (v0.2, 751 scores in 7 known makams)

Ranking, regardless of abstention: top-1 **87.9 %**, exact tie at the top 2.7 % (counted as a miss), true makam in the candidate set **96.9 %** (mean set size 1.21).

What the tool asserts: abstains on **2.4 %** of known-makam pieces, names the right makam for **86.4 %**, a wrong one for **8.5 %**, and leaves the rest as a tie.

| Makam | n | top-1 | tie | in set | abstains | named right | named wrong |
| --- | --- | --- | --- | --- | --- | --- | --- |
| rast | 109 | 99.1 % | 0 % | 99.1 % | 2.8 % | 96.3 % | 0.9 % |
| mâhur | 88 | 94.3 % | 0 % | 97.7 % | 4.5 % | 86.4 % | 9.1 % |
| nihâvend | 130 | 97.7 % | 0 % | 97.7 % | 2.3 % | 96.9 % | 0.8 % |
| uşşak | 118 | **62.7 %** | 12.7 % | 97.5 % | 0.8 % | 61.9 % | 24.6 % |
| hüseynî | 92 | **64.1 %** | 5.4 % | 89.1 % | 3.3 % | 66.3 % | 25.0 % |
| hicâz | 157 | 98.7 % | 0 % | 99.4 % | 1.3 % | 98.1 % | 0.6 % |
| bûselik | 57 | 94.7 % | 0 % | 94.7 % | 3.5 % | 94.7 % | 1.8 % |

The aggregate hides the weak spot: **uşşak and hüseynî are told apart about two times in three.** Their dizi differ in one degree (acem / eviç) and both makams use both pitches. A quarter of these pieces (52 of 210) get a wrong `top_makam`. In 40 of those 52 `ambiguous` is set and the true makam is among the candidates; in 12 it is named wrongly with no warning.

Abstention depends strongly on which makams count as "unknown":

| Unknown set | n | Abstain | Abstain, karar known | AUROC | AUROC, karar known | AUROC, Western r |
| --- | --- | --- | --- | --- | --- | --- |
| `proposal`: hüzzam, segâh, hicazkâr, kürdîlihicazkâr, sabâ, karcığar | 456 | 87.9 % | 78.6 % (n = 257) | 0.984 | 0.976 | 0.709 |
| `frequency`: the 9 most frequent makams outside the theory, unselected | 648 | 71.8 % | 52.5 % (n = 385) | 0.881 | 0.804 | 0.644 |

"Western r" uses the key-profile correlation as a novelty score. That correlation was never meant for the job, so read the column as "what a Western tool offers for this question", not as a competitor tuned to it.

Where unknown pieces get named anyway (`frequency` set): muhayyer is never flagged (0 %; named hüseynî 48, uşşak 14 of 67) and bayâtî almost never (1.6 %; named uşşak 48 of 62). Their dizi coincide with hüseynî and uşşak; they differ in seyir. Karcığar is flagged 62 % of the time (16 of 53 named hüseynî), kürdîlihicazkâr 70 % (20 of 70 named nihâvend), sabâ 82 %. Hüzzam, segâh and acemaşîrân are always flagged, but only because their karar is not in the theory. **A pitch-distribution tool can detect novelty in the scale, not in melodic behaviour.** Phase 1's güçlü and seyir features are meant to close this.

Leave-one-makam-out (remove a makam from the theory, check its pieces are flagged): nihâvend 99 %, hicâz 96 %; hüseynî 20 %, rast 9 % (absorbed by mâhur), bûselik 7 %, mâhur 5 % (absorbed by rast), uşşak 1 % (absorbed by hüseynî). A makam with a one-comma neighbour in the theory is absorbed, not flagged.

## What changed since v0.1, and what it did to the numbers

Three things in v0.1 were wrong, and one decision was made after seeing its results. The table applies them one at a time; every row is reproducible (`eval/v0.1/`, `eval/ablation/`, `eval/results_*.json`).

| Stage | top-1 | tie at top | abstains, known | named right | abstains, `proposal` | AUROC | abstains, `frequency` | AUROC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v0.1 as shipped | 85.6 % | not counted | 13.2 % | 74.4 % | 94.5 % | 0.964 | 77.2 % | 0.862 |
| 1. reader fixed, ties counted (`--pitch-column Koma53 --no-variants`) | 74.6 % | 17.2 % | 12.9 % | 72.8 % | 93.9 % | 0.965 | 76.7 % | 0.862 |
| 2. pitch column of the theory's own system (`--no-variants`) | 87.9 % | 2.7 % | 12.6 % | 77.1 % | 92.8 % | 0.962 | 75.5 % | 0.856 |
| 3. declared variants count for abstention; acem variants for rast and hicâz (default) | 87.9 % | 2.7 % | 2.4 % | 86.4 % | 87.9 % | 0.984 | 71.8 % | 0.881 |

1. **Ties were decided by the order of the TOML file.** When two makams fitted equally, v0.1 named whichever was listed first. On SymbTr 129 of the 751 known pieces (17 %) were tied at the top, and 82 of v0.1's 643 top-1 hits were such ties, every one of them an uşşak piece tied with bûselik or hüseynî and listed first: uşşak's reported 84.7 % was 15.3 % won and 69.5 % tied. A tie now yields `top_makam: null` and counts as a miss. The reader also skipped ornamented notes (trill, tremolo, mordent, ...; 2.8 % of all sounding notes). That moved the numbers only slightly, and in the 6 scores that end on an ornamented note the karar happened to come out the same.
2. **The theory was AEU and the measurement was not.** SymbTr has two pitch columns: `KomaAE` (AEU notation) and `Koma53` (53-TET, following practice). v0.1 read `Koma53`, where uşşak's segâh and hüseynî's eviç sit one comma away from their AEU positions, so "identification at exact comma positions" could not see the very degrees that separate these makams. That is where the ties came from, and why hüseynî's top-1 was 18.5 %. The theory file now names its column and the tool reads that one.
3. **The tool abstained on pieces that used its own declared variants.** 17 of the 19 nihâvend abstentions (with the right karar) were pieces with the eviç leading tone the theory itself lists. Variants now count for abstention, and never for the ranking. In the same step two variants were added to the theory, `descending_acem` for rast and for hicâz: in the 42 hicâz abstentions acem carried on average 8.8 % of the piece, and no other off-scale perde more than 1.3 %.

Step 3 is a judgement, not a bug fix, and it was taken after looking at v0.1's results, on the same data it is evaluated on. It costs detection at the fixed threshold (87.9 % of `proposal` unknowns flagged, down from 92.8 %) and buys fewer false abstentions (2.4 %, down from 12.6 %); the threshold-free AUROC improves. `Params(variants_in_abstention=False)` restores the old rule. The 0.90 threshold itself has not been touched.

## Known limits

- Karar from the last note only (it is the theory's karar in 98.4 % of known-makam pieces); no geçki (modulation) handling.
- Uşşak vs hüseynî is decided in emphasis, not scale (hüseynî/nevâ duration ratio, median 1.24 vs 0.50); not yet a feature. Güçlü emphasis is reported per fit but not used, and cannot be measured for mâhur, whose güçlü is the octave of its karar.
- The comparison is AEU notation against AEU theory. It says nothing about intonation in performance, which is what `Koma53` approximates and what a second theory layer would have to address.
- Labels come from SymbTr file names.
- AEU is one theory among several; the theory layer is plural by design but holds only AEU so far.

## Questions for the theory reviewer

- Hicâz with descending acem is the hümâyun dizi. One entry with a variant (as now), or two makams?
- `seyir` is recorded as ascending for hicâz and as both for bûselik; common descriptions differ on both. It is not used yet, but should be right before Phase 1 uses it.
- The two acem variants added in v0.2 follow the rule already used for hüseynî; they are as unreviewed as the rest.

## Licence

Code: Apache-2.0. Data read at runtime (SymbTr) keeps its own licence.
