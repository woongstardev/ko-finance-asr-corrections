# ko-finance-asr-corrections

> **Frequency-annotated Korean ASR confusion pairs from finance/stock YouTube — dataset + benchmark.**
>
> 한국어 금융·주식 유튜브 자동자막에서 실측한 ASR 오인식→교정 쌍 데이터셋과 벤치마크.
> 모든 쌍에 **관측 빈도**와 **검증 메타데이터**(2-LLM 합의 감사, 3단 승격 티어)가 붙어 있습니다.

> ⚠️ **Status: pre-release (private).** Preparing v0.1. Schema may change until first public release.

This data is produced and verified by the live pipeline of
[껄무새 (Ggulmuse)](https://ggulmuse.woongstar.com) — a Korean stock-YouTube claim-tracking
archive. The pairs here are the byproduct of correcting real YouTube auto-captions at scale.

## Why this exists

- Korean ASR error-correction data is nearly nonexistent: the only public pair dataset is
  KEBAP (2.5K pairs, error-type labels, frozen since 2023). No finance-domain resource exists.
- **No public "confusion pair dictionary with observed frequencies" exists in any language**
  (as of our 2026-08 survey). Frequency is what makes a pair list actionable: it tells you
  which errors dominate real traffic (e.g. `펀더멘탈→펀더멘털` ×449, `변합기→변압기` ×333,
  `FMC→FOMC` ×270 — full scan of a 595-video caption corpus).
- Every pair carries provenance: how it was mined, which auditor models independently agreed,
  and its promotion tier (human-approved / registry-verified).

## What's inside

| Path | Contents |
|---|---|
| `data/` | Confusion pairs (JSON/CSV): `wrong`, `right`, `observed_count`, `tier`, verification metadata. Stock names & finance terms only — no person names, no source sentences. |
| `benchmark/` | Mini benchmark v0: pure-stdlib scorer, a 456-item synthetic evaluation set (no caption text), and three dictionary baselines. Fixes and over-corrections are scored together — see [`benchmark/README.md`](benchmark/README.md). |
| `docs/SCHEMA.md` | Field-by-field schema. |
| `docs/METHODOLOGY.md` | The no-gold-label verification loop: 2 independent LLM auditors → consensus-only adoption → external registry check → 3-tier promotion → instant rollback. |

## The benchmark in one table

Task: fix the misrecognition, change nothing else. Three ways of using the dataset itself as
a correction system, scored on 456 synthetic items (no caption text). Net score is fixes
minus over-corrections, over error items.

| Baseline | Recall | Over-corrections | **Net score** |
|---|---|---|---|
| Plain substring replacement | 75.9% | 11 | **72.8%** |
| Whitespace-flexible matching | 100.0% | 14 | **96.0%** |
| Whitespace-flexible, keys ≥ 4 chars | 68.0% | 2 | **67.4%** |

Details, scoring rules and what the numbers mean: [`benchmark/README.md`](benchmark/README.md).

## Known limitations

Stated up front, because a niche dataset earns trust by being explicit about its edges.

- **One corpus, one ASR system, one domain.** Every pair comes from YouTube auto-captions of
  Korean stock/investing channels — 595 videos as of the current snapshot. A different ASR
  engine mishears differently, so these pairs are not a general Korean ASR error list.
- **89 pairs is small.** This is a frequency-annotated seed, not a comprehensive lexicon. It
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
  these same pairs, so a dictionary lookup reaches 100% recall. v0 measures restraint and
  robustness, not generalization to unseen misrecognitions.

## Relationship to prior work

| Resource | What it is | How this differs |
|---|---|---|
| [KEBAP](https://github.com/seonminkoo/KEBAP) (EMNLP 2023) | 2,478 Korean ASR error pairs, error-type taxonomy | We provide **observed frequencies** and domain focus; KEBAP classifies error types |
| [HyPoradise](https://arxiv.org/abs/2309.15701) / GenSEC | English N-best→transcript GER benchmark | Same task family; we are Korean, domain-specific, and dictionary-shaped |
| [korean-weather-asr](https://huggingface.co/datasets/ddehun/korean-weather-asr) | Korean weather-domain ASR benchmark | Closest Korean domain-benchmark precedent; different domain, no correction pairs |

## Versioning & updates

Snapshot releases (`v0.1`, then monthly `vYYYY.MM`). The upstream pipeline keeps producing
verified pairs; each snapshot adds newly promoted entries and retires rolled-back ones.

## License

- **Data** (`data/`): [CC BY 4.0](LICENSE-DATA)
- **Code** (`benchmark/`, `scripts/`): [MIT](LICENSE)

## Citation

See [CITATION.cff](CITATION.cff). A short technical report is planned.

---

Produced by the [껄무새](https://ggulmuse.woongstar.com) pipeline —
"who said what, and what actually happened" for Korean stock YouTube.
