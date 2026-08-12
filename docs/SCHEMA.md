# Data schema (draft — will be frozen at v0.1)

One record per verified confusion pair. Source of truth is the upstream production
dictionary; this repo publishes a filtered snapshot (stock names and finance terms only —
person-name pairs and source sentences are excluded).

| Field | Type | Description |
|---|---|---|
| `wrong` | string | Misrecognized surface form as observed in YouTube auto-captions (e.g. `변합기`) |
| `right` | string | Verified correction (e.g. `변압기`) |
| `observed_count` | int | Times `wrong` was observed during candidate mining rounds |
| `tier` | `"A"` \| `"B"` | Promotion tier. A = human-approved. B = `right` exists verbatim in an external registry (listed stocks / finance glossary) **and** both LLM auditors independently agreed |
| `category` | `"stock"` \| `"term"` \| `"number"` \| `"other"` | Vocabulary kind. `stock`/`term` = verbatim registry/glossary match; `number` = amount/figure damage; `other` = domain colloquialisms, foreign companies outside the KRX registry, multi-word phrases |
| `auditor_models` | string[] | Model identifiers of the independent auditors that agreed (empty for tier A pairs approved directly by a human) |
| `first_seen` | date | First observation date |
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

<!-- TODO(v0.1):
  - Add `corpus_count`: full-corpus frequency (whole ~440-video caption scan). Current
    `observed_count` only counts mining rounds (max ~6); the headline frequencies
    (e.g. 펀더멘탈→펀더멘털 ×375) come from the corpus scan and must ship as a field.
  - first_seen is empty for most rows — backfill from corpus scan or drop the field.
  - Freeze field list, then version the schema. -->
