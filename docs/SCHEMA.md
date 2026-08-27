# Data schema (draft — will be frozen at v0.1)

One record per verified confusion pair. Source of truth is the upstream production
dictionary; this repo publishes a filtered snapshot (stock names and finance terms only —
person-name pairs and source sentences are excluded).

**Primary key: the `(wrong, right)` tuple.** It is unique within a snapshot and stable
across snapshots — upstream keys its dictionary on the same tuple, so a pair that survives
into next month's release keeps its identity. There is deliberately no synthetic id field;
a hash of the same two strings would carry no additional information. Cite a pair by the
tuple plus the snapshot version.

| Field | Type | Description |
|---|---|---|
| `wrong` | string | Misrecognized surface form as observed in YouTube auto-captions (e.g. `변합기`) |
| `right` | string | Verified correction (e.g. `변압기`) |
| `corpus_count` | int \| null | **Cumulative-corpus frequency**: total matches of `wrong` across every caption transcript the upstream pipeline has processed to date (1,490 videos at last export <!-- stat:scanned_videos -->, growing; whitespace-flexible substring matching, same normalization as the production replacer). *Cumulative*, not *current*: the counted tree is an append-only mirror that keeps transcripts the live pipeline has since retired under its retention policy — as of 2026-08-27 that difference is 292 videos, so counting the live tree instead would let a routine deletion shrink a published frequency. Produced by the upstream corpus recount; null if the counts artifact was absent at export. **It counts occurrences of the surface form, not confirmed errors** — for a `wrong` form that is also ordinary Korean, the count would overstate the error rate. No shipped pair is such a form today, but the distinction matters as the snapshot grows |
| `right_count` | int \| null | **How often the verified form appears in the same corpus**, counted by the same scan with the same matching rules. Together with `corpus_count` it gives the pair's *error rate* — `corpus_count / (corpus_count + right_count)` — which is what turns this from a frequency list into a measurement of how often an ASR system gets a term wrong. `0` is an observation, not a gap: the correct spelling was never once transcribed correctly anywhere in the corpus (10 pairs at the current snapshot). `null` means the counts artifact did not carry the term, the same convention `corpus_count` uses. The rate is deliberately **not** stored — two counts already determine it, and a stored third number would drift against them |
| `observed_count` | int | Times `wrong` was observed during candidate mining rounds (small numbers by design — not the headline frequency, see `corpus_count`) |
| `tier` | `"A"` \| `"B"` | **Authority level.** A = a person approved this pair. B = promoted automatically, without a person in the loop, on the strength of `evidence` plus a verbatim registry match. Tier says who stands behind the pair, not how it was verified — that is `evidence` |
| `evidence` | `"human"` \| `"auditor-consensus"` \| `"goldset-alignment"` | **How the pair was verified.** `human` = a person judged it directly. `auditor-consensus` = two LLM auditors judged it independently and agreed, and `right` matched an external registry verbatim. `goldset-alignment` = the same misrecognition was observed in an aligned (auto-caption, official-caption) pair for the same utterance. A value of `unknown` means the exporter met an upstream verification path this schema has not described yet, and is a bug to be fixed, not a category |
| `category` | `"stock"` \| `"term"` \| `"number"` \| `"other"` | Vocabulary kind. `stock`/`term` = verbatim registry/glossary match; `number` = amount/figure damage; `other` = domain colloquialisms, foreign companies outside the KRX registry, multi-word phrases |
| `auditor_models` | string[] | Model identifiers of the independent auditors that agreed. **Orthogonal to `tier`**: it is non-empty whenever two auditors agreed, which can also happen on a tier A pair that a person then approved on top of that consensus (one shipped pair, `업항 → 업황`, is exactly this). Do not infer tier from this field |
| `approved_at` | date | Promotion date |
| `word_boundary` | bool | Whether replacement requires word-boundary match |
| `apply_scope` | string | Application scope constraint used in production (`unique`, …) |

## What is deliberately NOT included

- **Person-name pairs** — excluded from the public snapshot.
- **Source sentences / context examples** — the dataset is the pair + statistics, not the corpus.
- Tier C (mined-but-unverified) candidates — only pairs that survived verification ship.

## Withdrawn pairs (`data/withdrawn.json`)

Pairs that were promoted, shipped, and later removed. Publishing them is the point: a
correction dictionary that only shows its successes cannot be audited, and a consumer who
copied an earlier snapshot needs to know which keys to stop applying.

| Field | Type | Description |
|---|---|---|
| `wrong` / `right` | string | The withdrawn pair. Same primary key as `pairs.json`, and the two files must never both contain it |
| `withdrawn_at` | date | When it left the snapshot |
| `reason` | `"over-correction"` \| `"ambiguous-target"` \| `"artifact"` | Narrow by design. Free-text reasons would leak upstream review detail, and three categories cover what a consumer can act on |
| `evidence_kind` | `"corpus-counterexample"` \| `"user-report"` \| `"audit"` | What triggered the withdrawal |
| `corpus_count` | int \| null | Matches in the corpus at withdrawal, so the blast radius is visible |
| `justified_matches` | int \| null | How many of those were genuine misrecognitions. **A withdrawal does not mean every application was wrong** — `바위 → 바이오` was right 34 times out of 71 |
| `replaced_by` | string[] | Narrower keys that took over, empty when the pair was dropped outright. Apply these instead |
| `shipped_in` | string[] | Snapshot versions that carried it. Empty means it never reached a tagged release |
| `why` | string | One paragraph, written for a consumer deciding what to do about it |

`scripts/validate_snapshot.py` enforces the field list, both enums, `justified_matches ≤
corpus_count`, and the rule that matters most: **a withdrawn pair must not also be a shipped
pair**.

## Files

- `data/pairs.json` — canonical, full metadata
- `data/pairs.csv` — flat convenience export (same rows)
- `data/withdrawn.json` — pairs removed from the snapshot, with what replaced them

Top-level metadata in `pairs.json`: `exported_at`, `pair_count`, and `corpus`
(`scanned_videos`, `counted_at`) describing the frequency scan the counts came from.

`scanned_videos` is the size of that cumulative mirror at export time, and it is
published rather than merely used because the mirror can lag live intake by a few
videos (18 on 2026-08-27). When a frequency looks wrong later, the pair of numbers
says whether the cause was the definition or the lag; a gate cannot tell them apart
from inside this repository, since only the upstream host sees the live tree.

**A snapshot with populated `corpus_count` values has `scanned_videos > 0`, and its
counts are not all zero.** Both are enforced by `scripts/validate_snapshot.py`, and
`scripts/refresh_snapshot.py` additionally refuses to write a candidate whose corpus
shrank by more than half. The rule exists because on 2026-08-27 the upstream
transcript tree disappeared between two runs: the recount reported zero videos, every
`corpus_count` became 0, and nothing in the release path objected — zero is a legal
integer and the benchmark never reads the counts. Frequency is a headline claim of
this dataset, so a scan that reached nothing must fail loudly rather than publish
quietly.

`first_seen` was dropped before v0.1 — the production dictionary left it empty for most
rows and backfilling from the corpus was not worth the cost. It is therefore absent from
the field table above; `scripts/validate_snapshot.py` enforces that list.

## Why `evidence` exists as its own field

Until 2026-08-13 the tier value implied the verification path: B meant "auditor consensus
plus registry". Upstream is adding a path that promotes on caption-alignment evidence
*without* auditor consensus, which would have made that reading false while the field
kept its old name and values. Rather than add a tier value — which would silently break
every consumer filtering on `tier in ("A", "B")` — verification moved into its own
additive field. Tier stays an authority ordering; `evidence` carries the provenance and
can grow new values without invalidating existing ones.

<!-- TODO(v0.1): freeze field list, then version the schema. -->
