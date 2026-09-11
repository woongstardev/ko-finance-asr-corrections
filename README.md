# ko-finance-asr-corrections

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22700919.svg)](https://doi.org/10.5281/zenodo.22700919)

> **Frequency-annotated Korean ASR confusion pairs from finance/stock YouTube — dataset + benchmark.**
>
> 한국어 금융·주식 유튜브 자동자막에서 실측한 ASR 오인식→교정 쌍 데이터셋과 벤치마크.
> 모든 쌍에 **관측 빈도**와 **검증 메타데이터**(2-LLM 합의 감사, 3단 승격 티어)가 붙어 있습니다.

This data is produced and verified by the live pipeline of
[껄무새 (Ggulmuse)](https://ggulmuse.woongstar.com) — a Korean stock-YouTube claim-tracking
archive. The pairs here are the byproduct of correcting real YouTube auto-captions at scale.

## Why this exists

- Korean ASR error-correction data is nearly nonexistent: the only public pair dataset is
  KEBAP (2.5K pairs, error-type labels, frozen since 2023). No finance-domain resource exists.
- **No public "confusion pair dictionary with observed frequencies" exists in any language**
  (as of our 2026-08 survey). Frequency is what makes a pair list actionable: it tells you
  which errors dominate real traffic (e.g. `펀더멘탈→펀더멘털` ×1,151, <!-- stat:count:펀더멘탈 -->
  `변합기→변압기` ×682, <!-- stat:count:변합기 -->
  `FMC→FOMC` ×1,106 <!-- stat:count:FMC --> — full scan of a
  2,391-video caption corpus). <!-- stat:scanned_videos -->
- Every pair carries provenance: how it was mined, which auditor models independently agreed,
  and its promotion tier (human-approved / registry-verified).

## What's inside

| Path | Contents |
|---|---|
| `data/` | Confusion pairs (JSON/CSV): `wrong`, `right`, `observed_count`, `tier`, verification metadata. Stock names and finance terms, plus a small labelled tail of ordinary Korean the same pipeline verified (`category`) — no person names, no source sentences. |
| `benchmark/` | <!-- stat:eval_items --> Mini benchmark v0.7: pure-stdlib scorer, a 1,100-item synthetic evaluation set (no caption text), a mechanical trap-risk miner, and three dictionary baselines. Fixes and over-corrections are scored together — see [`benchmark/README.md`](benchmark/README.md). |
| `docs/SCHEMA.md` | Field-by-field schema. |
| `docs/METHODOLOGY.md` | The no-gold-label verification loop: 2 independent LLM auditors → consensus-only adoption → external registry check → 3-tier promotion → instant rollback. |

## How often does the ASR actually get it wrong?

Each pair carries both counts — the misrecognized form and the verified one — from the same
scan, so a pair states an error rate rather than just a frequency. This is the part no one
outside the pipeline can produce: it takes the corpus, not the dictionary.

| Pair | Wrong | Right | **Error rate** |
|---|---|---|---|
| `엔트로픽 → 앤트로픽` | 669 | 97 | **87.3%** <!-- stat:rate:엔트로픽 --> |
| `장기체 → 장기채` | 605 | 116 | **83.9%** <!-- stat:rate:장기체 --> |
| `FMC → FOMC` | 1,106 | 372 | **74.8%** <!-- stat:rate:FMC --> |
| `휴먼노이드 → 휴머노이드` | 448 | 116 | **79.4%** <!-- stat:rate:휴먼노이드 --> |

23 pairs have `right_count: 0` <!-- stat:right_count_zero -->, which is a stronger statement than a high rate:
across 2,391 videos <!-- stat:scanned_videos --> the auto-captions never once produced the correct spelling.
`보스턴 다이내믹스` and `서브프라임 모기지` are in that group.

The corpus behind those rates:

- **2,391 videos** <!-- stat:scanned_videos -->
- **47 channels** <!-- stat:corpus_channels --> — a count, not a list; the profile describes the
  corpus without identifying its sources
- **1,080.1 hours** <!-- stat:corpus_hours --> of speech, averaging 27.1 minutes a video

Read the rates as *this corpus, this ASR system*: the denominator is Korean finance YouTube
auto-captions, not Korean speech in general. And `corpus_count` counts a surface form, not a
confirmed error — see [Known limitations](#known-limitations).

## Using it as ASR biasing vocabulary

`data/biasing-list.txt` is the verified forms alone, ordered by how badly each is
misrecognized — a phrase list for contextual biasing, a Whisper `initial_prompt`, or a
rescoring lexicon. Recent work in this area synthesizes plausible pronunciation variants to
build such lists; here the variants are the `wrong` column, observed rather than generated,
with counts attached. Regenerate it with `scripts/make_biasing_list.py`; the validator fails
if it drifts from `data/pairs.json`.

## What was taken back out

`data/withdrawn.json` lists pairs that shipped and were later removed — five so far, all after
a full-corpus recheck found sentences they damaged. Two were dropped outright (`하스 → 하이닉스`
fires inside `하이퍼스케일러들`; `SPB` means both `SPV` and `S&P`) and three were narrowed rather
than dropped, with the replacement keys named in the file. The newest, `삼성자 → 삼성전자`, is
the expensive kind: it was right 1,180 times out of 1,215 and still went, because the 35
remaining fire inside 삼성자산운용 and Korean gives the replacer no boundary to stop at. Five
particle-suffixed keys took over and reach 236 of those matches.

**A withdrawal does not mean every application was wrong.** `바위 → 바이오` was correct 34 times
out of 71 — the rest were the ordinary word for rock — which is exactly why it became
`제약 바위 → 제약 바이오` instead of disappearing. If you copied an earlier snapshot, this file
is the list of keys to stop applying, and what to apply instead.

## The benchmark in one table

Task: fix the misrecognition, change nothing else. Three ways of using the dataset itself as
a correction system, scored on 1,100 synthetic items <!-- stat:eval_items --> (no caption text),
of which 51 are traps <!-- stat:trap_count --> — ordinary sentences a blind replacement damages. Net score is fixes minus over-corrections,
over error items.

| System | Recall | Over-corrections | **Net score** |
|---|---|---|---|
| Plain substring replacement | 75.2% | 26 | **72.1%** |
| Whitespace-flexible matching | 100.0% | 44 | **94.8%** |
| Whitespace-flexible, keys ≥ 4 chars | 69.6% | 15 | **67.8%** |
| gpt-5.6-sol, no dictionary (3 runs) | 70.8% | 28.7 | **67.4%** |
| Claude Opus 5, no dictionary (3 runs) | 63.8% | 9.3 | **61.2%** † |

The LLM rows are the comparison this benchmark exists to make, and the first one is measured
on exactly these 1,100 items. A frontier model given only the sentence **over-corrects about
half as often** as the dictionary — it has the restraint — but it cannot recover the specific
term: 176 of 839 error items come back as a confident wrong answer, usually a different
plausible finance term. Which misrecognition maps to which company is an observation, not an
inference, and that observation is what this dataset is.

† The LLM row was measured on `mini-v0.2`'s 482 items and is **not** rescored against the
newer set: an LLM row belongs to the eval set it was produced against, and producing a new one
costs an API run. Its outputs are committed (`benchmark/results/predictions/`), so the number
can be checked without an API key. The dictionary rows above are `mini-v0.7`.

Benchmark `mini-v0.7` (210 pairs, 1,100 items). Earlier numbers are kept in
[`benchmark/README.md`](benchmark/README.md) and are not comparable across versions — the
pair list, the trap set and the item count all moved.

**And a held-out row, which reverses it.** Every pair that arrives after a measurement is a
slice that measurement never saw, so each month's additions score the previous snapshot. On
September's 45 new pairs, the *previous* snapshot's dictionary fixes **none** of the 180 error
items that are genuinely new — and mangles 8 of them, because a short key it still holds fires
inside a new misrecognition and leaves the tail behind. A general model (`gpt-5.6-sol`) reaches
**81.5%** on the same items, and edits 8 of the 45 already-correct sentences, where the
dictionary edits none. Both results are real: a dictionary is worth 100% on the errors it has
seen and nothing on the ones it has not, which is precisely why the pairs are the product here
and the lookup is not. Quote this dataset for coverage of observed errors, never as evidence
that dictionaries generalise — and take the monthly snapshot rather than pinning one, because
a stale dictionary does not merely miss, it damages.

Details, scoring rules, the held-out table and what the numbers mean:
[`benchmark/README.md`](benchmark/README.md).

## Known limitations

Stated up front, because a niche dataset earns trust by being explicit about its edges.

- **One corpus, one ASR system, one domain.** Every pair comes from YouTube auto-captions of
  Korean stock/investing channels — 2,391 videos as of the current snapshot. <!-- stat:scanned_videos --> A different ASR
  engine mishears differently, so these pairs are not a general Korean ASR error list.
- **The domain label is the corpus's, not a filter's.** Pairs are promoted because upstream
  verification judged them correct, so a handful describe ordinary Korean rather than finance
  (`지진난주 → 지지난주`). They ship labelled `general` instead of being dropped; filter on
  `category` if you want a strictly domain lexicon.
- **210 pairs is small.** <!-- stat:pair_count --> This is a frequency-annotated seed, not a comprehensive lexicon. It
  grows with monthly snapshots as the upstream pipeline verifies more pairs.
- **Skewed by construction.** Frequency-ranked mining favours what the channels talk about
  most, so semiconductor and index vocabulary dominates, and a single company can account for
  a family of variants (`하이니스`, `하이네스`, `SK 하인`, `하잉스`, …).
- **`corpus_count` counts surface forms, not confirmed errors.** No shipped pair is also an
  ordinary Korean word, but the metric would overstate frequency for one that was. See
  [`docs/SCHEMA.md`](docs/SCHEMA.md).
- **Some pairs encode a spelling standard, not only a mishearing.** `펀더멘탈 → 펀더멘털`, the
  highest-frequency pair, is the standard transliteration correcting a widely used variant.
  Treat the dataset as "what the upstream pipeline normalizes", not purely "what the ASR got
  wrong".
- **Verification is auditor consensus plus a registry check, not human ground truth.** Tier A
  pairs were approved by a person; Tier B pairs were not. See
  [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md), including the measured ~1-in-10
  over-correction rate that motivated the benchmark's penalty.
- **No person-name pairs and no source sentences**, by policy. Misheard names are a real and
  frequent error class that this dataset deliberately does not cover, and contexts cannot be
  recomputed from what ships here.
- **The benchmark is in-domain by construction.** Its error sentences are generated from
  these same pairs, so a dictionary lookup reaches 100% recall. It measures restraint and
  robustness, not generalization to unseen misrecognitions.

## Relationship to prior work

| Resource | What it is | How this differs |
|---|---|---|
| [KEBAP](https://github.com/seonminkoo/KEBAP) (EMNLP 2023) | 2,478 Korean ASR error pairs, error-type taxonomy | We provide **observed frequencies** and domain focus; KEBAP classifies error types |
| [HyPoradise](https://arxiv.org/abs/2309.15701) / GenSEC | English N-best→transcript GER benchmark | Same task family; we are Korean, domain-specific, and dictionary-shaped |
| [korean-weather-asr](https://huggingface.co/datasets/ddehun/korean-weather-asr) | Korean weather-domain ASR benchmark | Closest Korean domain-benchmark precedent; different domain, no correction pairs |

## Versioning & updates

Snapshot releases (`v0.1`, then monthly `vYYYY.MM`). What is planned, and what is
deliberately not: [ROADMAP.md](ROADMAP.md). The upstream pipeline keeps producing
verified pairs; each snapshot adds newly promoted entries and retires rolled-back ones.

## Contributing

`data/` is a generated export, so it does not take pull requests — pairs are verified upstream
and arrive with the next snapshot. Propose a pair or report an over-correction through the
issue forms; `benchmark/` and `scripts/` take ordinary PRs (standard library only).
See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and
[SECURITY.md](SECURITY.md) — the last one is where a privacy report goes, privately.

## License

- **Data** (`data/`): [CC BY 4.0](LICENSE-DATA)
- **Code** (`benchmark/`, `scripts/`): [MIT](LICENSE)

## Citation

Every snapshot is archived on Zenodo with its own DOI. Cite the **concept DOI** unless you
need to pin a specific snapshot — it always resolves to the latest one:

- Concept DOI (all versions): [`10.5281/zenodo.22700919`](https://doi.org/10.5281/zenodo.22700919)
- v0.1 (2026-09-11, 210 pairs): [`10.5281/zenodo.22700920`](https://doi.org/10.5281/zenodo.22700920)

Machine-readable metadata is in [CITATION.cff](CITATION.cff). A short technical report is
planned.

---

Produced by the [껄무새](https://ggulmuse.woongstar.com) pipeline —
"who said what, and what actually happened" for Korean stock YouTube.
