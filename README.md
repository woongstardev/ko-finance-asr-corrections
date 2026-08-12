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
  which errors dominate real traffic (e.g. `펀더멘탈→펀더멘털` ×414, `변합기→변압기` ×322,
  `FMC→FOMC` ×261 — full scan of a 521-video caption corpus).
- Every pair carries provenance: how it was mined, which auditor models independently agreed,
  and its promotion tier (human-approved / registry-verified).

## What's inside

| Path | Contents |
|---|---|
| `data/` | Confusion pairs (JSON/CSV): `wrong`, `right`, `observed_count`, `tier`, verification metadata. Stock names & finance terms only — no person names, no source sentences. |
| `benchmark/` | Mini benchmark v0: pure-stdlib scorer, a 456-item synthetic evaluation set (no caption text), and three dictionary baselines. Fixes and over-corrections are scored together — see [`benchmark/README.md`](benchmark/README.md). |
| `docs/SCHEMA.md` | Field-by-field schema. |
| `docs/METHODOLOGY.md` | The no-gold-label verification loop: 2 independent LLM auditors → consensus-only adoption → external registry check → 3-tier promotion → instant rollback. |

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
