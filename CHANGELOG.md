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

### Changed
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
