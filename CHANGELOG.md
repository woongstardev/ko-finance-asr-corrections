# Changelog

All notable changes to the published snapshot (`data/`) are recorded here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), adapted for a
dataset — **Added** = new pairs, **Removed** = pairs recalled from the snapshot
(the only patch-release trigger), **Changed** = metadata changes on existing
pairs (tier, evidence, scope — not weekly frequency drift, which is expected as
the corpus grows and is not chronicled per-pair).

Versions are calendar snapshots (`vYYYY.MM`) after the initial `v0.1`; a pair's
identity across versions is its `(wrong, right)` tuple (`docs/SCHEMA.md`).
Entries are appended by `scripts/refresh_snapshot.py --write`; the Unreleased
section becomes the next release's notes.

## [Unreleased]

### Added
- Initial public snapshot: 89 verified confusion pairs (tier A/B, enabled)
  exported 2026-08-13 from the upstream production dictionary — stock names,
  finance terms, and number damage from Korean finance-YouTube auto-captions.
  Full-corpus frequencies (`corpus_count`) from a 595-video scan.
- `evidence` field (2026-08-13): verification provenance (`human` /
  `auditor-consensus` / `goldset-alignment`) separated from `tier`, which
  remains an authority ordering.
- Benchmark: frozen eval set, trap set, scorer, and three replacement baselines
  (naive / word-boundary / production-guarded) with per-round verification
  numbers.
- `HBN → HBM` (2026-08-27)
- `MDI → 엔비디아` (2026-08-27)
- `SK니스 → SK하이닉스` (2026-08-27)
- `SK닉스 → SK하이닉스` (2026-08-27)
- `SK하닉스 → SK하이닉스` (2026-08-27)
- `SMP → 에스앤피` (2026-08-27)
- `S아닉스 → SK하이닉스` (2026-08-27)
- `가이더스 → 가이던스` (2026-08-27)
- `공매돌 → 공매도` (2026-08-27)
- `김에비디아 → 엔비디아` (2026-08-27)
- `단도체 → 반도체` (2026-08-27)
- `마이러크럼 → 마이크론` (2026-08-27)
- `매도체 → 반도체` (2026-08-27)
- `반도지 → 반도체` (2026-08-27)
- `반조체 → 반도체` (2026-08-27)
- `밤도체 → 반도체` (2026-08-27)
- `밸루에이션 → 밸류에이션` (2026-08-27)
- `변동상 → 변동성` (2026-08-27)
- `본동성 → 변동성` (2026-08-27)
- `브드컴 → 브로드컴` (2026-08-27)
- `비슷하라 → 비스타라` (2026-08-27)
- `삼성원자 → 삼성전자` (2026-08-27)
- `삼성자 → 삼성전자` (2026-08-27)
- `삼성전나 → 삼성전자` (2026-08-27)
- `소부 장단도 → 소부장도` (2026-08-27)
- `소부 장단들 → 소부장들` (2026-08-27)
- `소부 장단안에서 → 소부장 안에서` (2026-08-27)
- `소부 장단에 → 소부장에` (2026-08-27)
- `소부 장단을 → 소부장을` (2026-08-27)
- `소부 장단이 → 소부장이` (2026-08-27)
- `스페이스섹스 → 스페이스X` (2026-08-27)
- `스페이스엑스 → 스페이스X` (2026-08-27)
- `시카총 → 시가총액` (2026-08-27)
- `아이비 → IBM` (2026-08-27)
- `에스키아닉스 → SK하이닉스` (2026-08-27)
- `엔비어 → 엔비디아` (2026-08-27)
- `엘파벳 → 알파벳` (2026-08-27)
- `영업익 → 영업이익` (2026-08-27)
- `오남이 → 모나미` (2026-08-27)
- `오라늄 → 우라늄` (2026-08-27)
- `우라님 → 우라늄` (2026-08-27)
- `유라늄 → 우라늄` (2026-08-27)
- `제약 바위 → 제약 바이오` (2026-08-27)
- `채치T → 챗지피티` (2026-08-27)
- `컨센스 → 컨센서스` (2026-08-27)
- `코이브 → 코어위브` (2026-08-27)
- `파운트리 → 파운드리` (2026-08-27)
- `하이니프 → 하이닉스` (2026-08-27)
- `하이렉스 → 하이닉스` (2026-08-27)
- `하인스 → 하이닉스` (2026-08-27)

### Removed
- `SPB → SPV` (2026-08-27) — see `data/withdrawn.json` for why, and for the narrower key that replaced it where one did
- `바위 → 바이오` (2026-08-27) — see `data/withdrawn.json` for why, and for the narrower key that replaced it where one did
- `소부 장단 → 소부장` (2026-08-27) — see `data/withdrawn.json` for why, and for the narrower key that replaced it where one did
- `하스 → 하이닉스` (2026-08-27) — see `data/withdrawn.json` for why, and for the narrower key that replaced it where one did

### Changed
- `right_count`, `ticker`, `market` added to every pair (2026-08-27)
- Frequencies are now counted over the cumulative corpus (1,490 videos, 43 channels,
  672.3 hours) rather than one host's working tree of 595, so every `corpus_count`
  grew with the denominator (2026-08-27)
- Benchmark `mini-v0.2` → `mini-v0.4`: 135 pairs, 721 items, 47 traps. Boundary
  baseline 88.7% → 92.4% net (2026-08-27)
- Benchmark: first held-out row — on the 220 items from pairs added after the
  committed LLM run, the previous snapshot's dictionary scores 2.3% and
  `claude-opus-5` scores 72.9% (2026-08-27)
- Benchmark promoted to `mini-v0.2` (2026-08-23): the trap set grew from 14 to
  40 hand-written sentences, chosen from a mechanical risk ranking
  (`benchmark/mine_traps.py`), and the eval set from 456 to 482 items. Baseline
  net scores moved accordingly (boundary 96.0% -> 88.7%) and are **not
  comparable across benchmark versions**; both are recorded in
  `benchmark/README.md`. No `data/` pair changed.
- Benchmark evaluation set is now append-only: item ids derive from the pair
  rather than its position, and existing items are carried across unchanged when
  the snapshot grows. Ids from `mini-v0` do not carry over to `mini-v0.2`.
- Benchmark: first LLM reference row (2026-08-23) — `claude-opus-5`, no
  dictionary, mean of 3 runs: 61.2% net against the dictionary's 88.7%, with
  four times fewer over-corrections and 114 confident wrong answers. Runner,
  manifest and per-run results are committed; the run itself needs credentials
  and is not part of scoring.
