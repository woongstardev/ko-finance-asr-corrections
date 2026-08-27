# Roadmap

What this dataset is heading toward, and what it is not. Dates are targets, not commitments —
the pairs arrive when upstream verification produces them, not when a calendar says so.

## Now — pre-release

Preparing `v0.1`. The schema may still change; after v0.1 a `data/` schema change means a
minor version.

- **Snapshot growth.** The upstream pipeline keeps verifying pairs, and each monthly snapshot
  adds the newly promoted ones. The published snapshot is 135 pairs counted over a cumulative
  corpus of 1,490 videos; the next one is larger.
- **Benchmark `mini-v0.4`.** 721 items, 47 traps, three dictionary baselines, one LLM
  reference row and a held-out row. See [`benchmark/README.md`](benchmark/README.md).
- **Release automation.** A weekly dry-run detects upstream change; a monthly human step
  publishes it. Four gates run against a candidate export before anything is written:
  publication boundary, corpus coverage, schema contract and benchmark regression.

## Next — after v0.1

- **Monthly snapshots** (`vYYYY.MM`). For a niche dataset, trust comes from being updated, not
  from being large.
- **A HuggingFace mirror**, kept as a summary of this repository rather than a second source
  of truth.
- **~~A held-out evaluation split.~~** Done, and without withholding anything: pairs that
  arrive after a benchmark run have by definition not been seen by it, so each month's delta
  is a held-out set for the systems measured before it. The first measurement (2026-08-27) is
  the reversal the in-domain table cannot show — the previous snapshot's dictionary scores
  2.3% on new pairs where an LLM scores 72.9%. Continues monthly.
- **More traps.** Trap candidates are mined mechanically (`benchmark/mine_traps.py`) and the
  sentences are written by hand; the set grows with the pair list.

## Later — if the dataset earns it

- **A correction library**, not just data: a deterministic replacement engine with the
  whitespace-flexible matching and guards the benchmark already measures, plus a phonetic
  index for misrecognitions that are not yet in the dictionary. The upstream pipeline would
  become its first user, which is what keeps a published library honest.
- **A short technical report**, so the verification method is citable independently of the
  data.

## Deliberately not planned

- **Person-name pairs.** A real and frequent error class this dataset does not cover, by
  policy, and that is not going to change here.
- **Source sentences.** Pairs, counts and metadata only.
- **Third-party dependencies** in the benchmark or scripts.
- **A general Korean ASR error list.** Every pair comes from one corpus, one ASR system, one
  domain. Read [Known limitations](README.md#known-limitations) before treating it as more.

## How to influence it

Propose a pair or report an over-correction through the issue forms — see
[CONTRIBUTING.md](CONTRIBUTING.md). Additions go through upstream verification, so the honest
version is: proposals shape the snapshot after they are verified, not on merge.
