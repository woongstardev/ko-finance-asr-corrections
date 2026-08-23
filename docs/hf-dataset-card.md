# HuggingFace dataset card (draft — not yet uploaded)

> **This file is a draft of the `README.md` that will live in the HuggingFace mirror**
> `woongstardev/ko-finance-asr-corrections`. It is not uploaded until the repository goes
> public (see [`tasks/003-v01-release.md`](../tasks/003-v01-release.md)).
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
---
```

# ko-finance-asr-corrections

Frequency-annotated Korean ASR confusion pairs from finance/stock YouTube — **89 pairs**
mined from a **595-video** auto-caption corpus, each with an observed corpus frequency and
verification provenance.

한국어 금융·주식 유튜브 자동자막에서 실측한 ASR 오인식→교정 쌍입니다. 모든 쌍에 관측
빈도와 검증 메타데이터(2-LLM 합의 감사, 승격 티어)가 붙어 있습니다.

## What makes it different

No public "confusion pair dictionary with observed frequencies" exists in any language (as of
a 2026-08 survey), and Korean ASR error-correction data is nearly nonexistent — the only prior
public pair set is KEBAP (2,478 pairs, error-type labels, frozen since 2023) and no
finance-domain resource exists. Frequency is what makes a pair list actionable: it says which
errors dominate real traffic (`펀더멘탈→펀더멘털` ×449, `하이니스→하이닉스` ×342,
`변합기→변압기` ×333, `FMC→FOMC` ×270).

## Fields

`wrong`, `right`, `corpus_count`, `observed_count`, `tier`, `evidence`, `category`,
`auditor_models`, `approved_at`, `word_boundary`, `apply_scope`.
Field-by-field definitions: [`docs/SCHEMA.md`](https://github.com/woongstardev/ko-finance-asr-corrections/blob/main/docs/SCHEMA.md).

## How it was verified

No gold labels exist for this task, so verification is a loop, not an annotation pass: two
independent LLM auditors judge each candidate, only consensus is adopted, an external registry
check confirms stock names, and pairs are promoted through tiers with instant rollback.
Details and per-round numbers: [`docs/METHODOLOGY.md`](https://github.com/woongstardev/ko-finance-asr-corrections/blob/main/docs/METHODOLOGY.md).

## Limitations (read these)

One corpus, one ASR system, one domain; 89 pairs is a seed, not a lexicon; frequency-ranked
mining skews toward what these channels talk about; `corpus_count` counts surface forms, not
confirmed errors; some pairs encode a spelling standard rather than a mishearing; tier B pairs
were verified by auditor consensus, not by a human; **no person-name pairs and no source
sentences ship, by policy**. The full list is in the repository README — read it before using
the data as a general Korean ASR error list, because it is not one.

## Benchmark

A standard-library scorer, a 456-item synthetic evaluation set, and three dictionary baselines
live in the GitHub repository. Fixes and over-corrections are scored together, because a
correction dictionary that fixes 100 errors while damaging 20 correct sentences is not a good
dictionary.

## License and citation

Data: CC BY 4.0. Code (benchmark, scripts): MIT.
Cite via `CITATION.cff` in the GitHub repository.

Produced by the [껄무새](https://ggulmuse.woongstar.com) pipeline.
