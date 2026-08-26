# AGENTS.md

Instructions for coding agents (and humans) working in this repository.

This repo publishes a **filtered snapshot** of a correction dictionary that is produced and
verified elsewhere: the upstream [껄무새 (Ggulmuse)](https://ggulmuse.woongstar.com) pipeline
corrects real YouTube auto-captions at scale, and what ships here is the public-safe slice of
that dictionary plus a benchmark built from it. Two consequences shape everything below —
`data/` is generated rather than authored, and some material is deliberately excluded.

## Hard lines

These are not style preferences. A change that breaks one is wrong even if it passes tests.

- **No person-name pairs in `data/`.** Stock names, finance terms and number damage only.
  Misheard person names are a real and frequent error class this dataset does not cover, by
  policy. A filter enforces it at export and `scripts/validate_snapshot.py` checks it again.
- **No caption text or context sentences** — anywhere, including issues and examples. The
  dataset is pairs plus statistics plus metadata. Source transcripts are not redistributable
  and are not ours to publish.
- **No unverified candidates.** Only pairs that survived upstream verification ship.
- **No upstream internals, operational detail, or secrets in commits.** Host paths, internal
  ticket numbers, private module layout. `scripts/release_check.py` scans for these; run it
  with `--publication` for the stricter pre-release pass.

## Commands

Everything is standard-library Python 3.10+. There is nothing to install.

```bash
python3 benchmark/test_score.py         # scorer unit tests
python3 scripts/validate_snapshot.py    # schema contract, keys, json/csv agreement, prose numbers
python3 scripts/benchmark_gate.py       # release gate: eval set grew only, no new cascades
python3 scripts/release_check.py        # publication boundary
python3 benchmark/make_eval_set.py      # regenerate the eval set (append-only)
python3 benchmark/baselines.py --all    # reference systems -> predictions/
```

CI runs the first three on every push.

## Conventions

- **`data/` is generated. Do not hand-edit it.** Corrections happen upstream and arrive in the
  next snapshot; see [CONTRIBUTING.md](CONTRIBUTING.md) for the paths that do work.
- **No third-party imports** in `benchmark/` or `scripts/`. The Korean NLP ecosystem is full
  of packages that died with a dependency; a dataset that needs `pip install` to be *scored*
  stops being scorable. Vendor what you truly need.
- **A commit that changes `docs/SCHEMA.md` also changes `scripts/validate_snapshot.py`.** The
  validation rules are hardcoded there rather than delegated to a schema framework (see the
  no-dependencies rule), so the two are a double source of truth. Each rule cites the SCHEMA
  section it enforces; keep them in step in the same commit or they drift silently.
- **Don't move published numbers without moving the version.** The baseline table in
  `README.md` and `benchmark/results/*.json` are claims. If a change moves them, move them in
  the same commit, say why, and bump the benchmark identifier.
- Commit messages in English; each document keeps the language it is written in. Single `main`
  branch. Stage explicit paths — never `git add -A`.
- Schema changes are free until v0.1. After that, a `data/` schema change is a minor version.

## Releases

Snapshots are calendar releases (`v0.1`, then monthly `vYYYY.MM`), and a patch release exists
for exactly one reason: **withdrawing a pair that over-corrects**. Adding pairs is never a
patch.

The release path is automated in `scripts/refresh_snapshot.py`, which recounts upstream,
re-exports, runs every gate against the candidate, and only then touches `data/`:

```bash
python3 scripts/refresh_snapshot.py                 # dry-run: report only
sh scripts/install-refresh-timer.sh                 # weekly dry-run as a user timer
python3 scripts/refresh_snapshot.py --write         # monthly: update data/ + CHANGELOG.md
```

Two things stay human on purpose. A person reviews the person-name candidates the filter
dropped before any publish, and a person decides that a release happens. Reports are written
outside the repository (`OSS_REFRESH_REPORT_DIR`) because they name those candidates.

Host-specific paths — the upstream checkout, where reports go, which credentials the optional
Telegram notification uses — are passed to the installer through the environment and land in
the generated unit, never in this repository:

```bash
GGULMUSE_ROOT=... OSS_REFRESH_TELEGRAM_ENV=... sh scripts/install-refresh-timer.sh
```
