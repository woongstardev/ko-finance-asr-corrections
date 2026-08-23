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
| `corpus_count` | int \| null | **Full-corpus frequency**: total matches of `wrong` across the entire caption corpus (595 videos at last export <!-- stat:scanned_videos -->, growing; whitespace-flexible substring matching, same normalization as the production replacer). Produced upstream by ggulmuse an upstream pipeline task; null if the counts artifact was absent at export. **It counts occurrences of the surface form, not confirmed errors** — for a `wrong` form that is also ordinary Korean, the count would overstate the error rate. No shipped pair is such a form today, but the distinction matters as the snapshot grows |
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

## Files

- `data/pairs.json` — canonical, full metadata
- `data/pairs.csv` — flat convenience export (same rows)

Top-level metadata in `pairs.json`: `exported_at`, `pair_count`, and `corpus`
(`scanned_videos`, `counted_at`) describing the frequency scan the counts came from.

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
