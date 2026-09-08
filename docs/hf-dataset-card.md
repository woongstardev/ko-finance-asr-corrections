# HuggingFace dataset card (draft — not yet uploaded)

> **This file is a draft of the `README.md` that will live in the HuggingFace mirror**
> `woongstardev/ko-finance-asr-corrections`. It is not uploaded until the repository goes
> public (see [`ROADMAP.md`](../ROADMAP.md)).
>
> **The source of truth is the repository [`README.md`](../README.md), not this card.**
> The card is a summary that links back. When the two disagree, the README wins; the monthly
> release procedure only refreshes the numbers and the version string here
> (see [`AGENTS.md`](../AGENTS.md) → 스냅숏 갱신).
>
> Croissant metadata is **not** authored by hand: the Hub generates it automatically for every
> dataset it can convert to Parquet, and serves it at `/api/datasets/{repo}/croissant`
> (checked 2026-08-23).

Everything below the line is the card content to upload verbatim.

---

```yaml
---
language:
  - ko
pretty_name: Korean Finance ASR Correction Pairs
license: cc-by-4.0
task_categories:
  - text2text-generation
size_categories:
  - n<1K
tags:
  - korean
  - asr
  - speech-recognition
  - error-correction
  - confusion-pairs
  - post-processing
  - finance
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/pairs.csv
  - config_name: withdrawn
    data_files:
      - split: train
        path: data/withdrawn.json
---
```

# ko-finance-asr-corrections

Frequency-annotated Korean ASR confusion pairs from finance/stock YouTube.

- **210 pairs** <!-- stat:pair_count -->
- mined from **2,391 videos** <!-- stat:scanned_videos --> of auto-captions
- across **47 channels** <!-- stat:corpus_channels -->
- totalling **1,080.1 hours** <!-- stat:corpus_hours -->

Each pair carries how often the term was mangled *and* how often it was said correctly, plus
verification provenance.

한국어 금융·주식 유튜브 자동자막에서 실측한 ASR 오인식→교정 쌍입니다. 모든 쌍에 오표기·정답
표기 빈도(→ 용어별 오인식률)와 검증 메타데이터(2-LLM 합의 감사, 승격 티어)가 붙어 있습니다.

## What makes it different

No public "confusion pair dictionary with observed frequencies" exists in any language (as of
a 2026-08 survey), and Korean ASR error-correction data is nearly nonexistent — the only prior
public pair set is KEBAP (2,478 pairs, error-type labels, frozen since 2023) and no
finance-domain resource exists. Frequency is what makes a pair list actionable: it says which
errors dominate real traffic:

- `펀더멘탈 → 펀더멘털` ×1,151 <!-- stat:count:펀더멘탈 -->
- `하이니스 → 하이닉스` ×904 <!-- stat:count:하이니스 -->
- `변합기 → 변압기` ×682 <!-- stat:count:변합기 -->
- `FMC → FOMC` ×1,106 <!-- stat:count:FMC -->

Those four were 449, 342, 333 and 270 one snapshot ago; the counts grow with the corpus, which
is why every number in this card carries a marker the release checker verifies.

## Fields

`wrong`, `right`, `corpus_count`, `observed_count`, `tier`, `evidence`, `category`,
`auditor_models`, `approved_at`, `word_boundary`, `apply_scope`.
Field-by-field definitions: [`docs/SCHEMA.md`](https://github.com/woongstardev/ko-finance-asr-corrections/blob/main/docs/SCHEMA.md).

## How it was verified

No gold labels exist for this task, so verification is a loop, not an annotation pass: two
independent LLM auditors judge each candidate, only consensus is adopted, an external registry
check confirms stock names, and pairs are promoted through tiers with instant rollback.
Details and per-round numbers: [`docs/METHODOLOGY.md`](https://github.com/woongstardev/ko-finance-asr-corrections/blob/main/docs/METHODOLOGY.md).

## Error rates, not just frequencies

Each pair carries `corpus_count` (the misrecognized form) and `right_count` (the verified one)
from the same scan, so a row states how often the term came out wrong:
`FMC → FOMC` 74.8% <!-- stat:rate:FMC -->, `엔트로픽 → 앤트로픽` 87.3% <!-- stat:rate:엔트로픽 -->.
23 pairs have `right_count: 0` <!-- stat:right_count_zero --> — across all 2,391 videos <!-- stat:scanned_videos --> the captions
never once produced the correct spelling. Stock rows also carry `ticker` and `market`, so they
join to price data without matching on a name.

`data/withdrawn.json` lists pairs that shipped and were later removed, with how many of their
matches were genuine and which narrower key replaced them. A withdrawal says the key was
unsafe as written, not that every correction it made was wrong.

## Limitations (read these)

One corpus, one ASR system, one domain; 210 pairs <!-- stat:pair_count --> is a seed, not a lexicon; frequency-ranked
mining skews toward what these channels talk about; `corpus_count` counts surface forms, not
confirmed errors; some pairs encode a spelling standard rather than a mishearing; tier B pairs
were verified by auditor consensus, not by a human; **no person-name pairs and no source
sentences ship, by policy**. The full list is in the repository README — read it before using
the data as a general Korean ASR error list, because it is not one.

## Benchmark

A standard-library scorer, a 1,100-item <!-- stat:eval_items --> synthetic evaluation set, and three dictionary baselines
live in the GitHub repository. Fixes and over-corrections are scored together, because a
correction dictionary that fixes 100 errors while damaging 20 correct sentences is not a good
dictionary.

## License and citation

Data: CC BY 4.0. Code (benchmark, scripts): MIT.
Cite via `CITATION.cff` in the GitHub repository.

Produced by the [껄무새](https://ggulmuse.woongstar.com) pipeline.
