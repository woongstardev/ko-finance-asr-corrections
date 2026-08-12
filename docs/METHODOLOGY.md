# Verification methodology

How pairs get promoted into this dataset **without a gold-label corpus**, what was measured
while doing it, and what the numbers do and do not support.

## The loop

```
mine candidates from the caption corpus (same misrecognition repeating across videos)
        │
        ▼
two LLM auditors judge each candidate INDEPENDENTLY (no shared context, no vote order)
        │
        ├── disagreement ──────────────► stays a candidate. Never ships.
        │
        ▼ consensus
external fact check: does `right` exist verbatim in a registry?
(listed-stock spellings ~20K · finance glossary · person registry)
        │
        ├── yes ──► Tier B — promoted automatically
        │
        └── no  ──► human queue ──┬── approved ──► Tier A
                                  └── rejected  ──► never ships, and later mining
                                                    rounds do not revive it
        │
        ▼
shipped = enabled AND tier in (A, B)
        │
        └── observed causing a wrong replacement in production
                 └──► disabled immediately, and absent from the next snapshot
```

The public snapshot applies one more filter on top: person-name pairs are dropped even when
they are Tier A, so a verified pair can exist upstream and still never appear here.

## Promotion and rollback state machine

| State | Set by | Ships? | Leaves the state by |
|---|---|---|---|
| candidate | mining | no | auditor consensus, or being re-observed in a later round |
| queued (Tier C) | consensus without registry backing | no | a human decision |
| rejected | human | no | nothing — a human decision is never overwritten by later mining |
| Tier A | human approval | yes | rollback |
| Tier B | consensus + verbatim registry match | yes | rollback, or a human overriding it |
| disabled | rollback | no | re-approval by a human |

One row per `wrong → right`. Re-observation across rounds updates the observation count and
last-seen date rather than creating a duplicate, which is why `observed_count` in the data is
small and bounded by the number of rounds — `corpus_count` is the frequency number to quote.

## Measured, per round

Two full audit rounds, both on 2026-08-11/12, auditors `claude-code/opus` and
`codex/gpt-5.6-sol`:

| | Round 1 | Round 2 |
|---|---|---|
| Videos audited | 8 | 3 |
| Candidates raised | 498 | 145 |
| Corrections applied | 469 | 123 |
| Auditor consensus rate (agreed / judged) | 82.2% (398/484) | 83.1% (113/136) |
| Both auditors OK, of applied corrections | 81.9% | 81.3% |
| **Both auditors flagged an over-correction** | **9.2%** | **10.6%** |
| Promoted to Tier B | 48 | 37 |
| Sent to the human queue (Tier C) | 436 | 99 |
| Glossary misses | 15 | 13 |
| Share of corrections already covered by the dictionary | 0.0% | 2.4% |

Three things worth reading off that table.

**About one applied correction in ten was an over-correction that both auditors caught.**
Not a disagreement, not a near miss — both independent judges said the system had damaged
text that was fine. This is the single number that shaped the benchmark: a scorer that counts
only fixes would call these rounds a success. It is also why the benchmark's headline metric
subtracts over-corrections rather than reporting them alongside.

**Prompt-level instructions moved the failure type without reducing the total.** Tightening
the prompt against invented compounds cut that failure class from 14 to 1 and pushed the
damage into numbers and proper nouns instead. The total stayed flat. Verification structure
(independent auditors, registry checks, deterministic pre-replacement) moved the number;
asking the model to be careful did not.

**The dictionary is starting to carry load.** 0.0% → 2.4% of applied corrections came from
deterministic dictionary replacement rather than the LLM pass. That share is the mechanism by
which this dataset pays for itself upstream: every promoted pair is one fewer thing the
expensive, uncertain layer has to get right.

## Composition of the current snapshot

89 pairs: 45 Tier A (human-approved), 44 Tier B (consensus + registry). By category: 37
`other`, 32 `stock`, 14 `term`, 6 `number`. Every Tier B pair carries both auditor model ids;
Tier A pairs carry none by construction, since a human approved them directly.

## Design rules, learned from production incidents

- **Never replace with a different real entity.** Registry membership alone is not enough.
  Observed failures include swapping in a different person, a different listed company, and
  reversing the polarity of a sentence. These are permanently forbidden at every tier.
- **Minimum key length 2**, and prefer long keys — `외한 시장 → 외환 시장` rather than
  `외한 → 외환`, because the longer key carries its own context and cannot structurally match
  inside `제외한`. Putting context in the key beats bolting a guard onto a short one. Korean
  is agglutinative, so there is no word boundary to fall back on; the benchmark's `guarded`
  baseline shows what a blunt length rule costs (32 points of recall).
- **Whitespace-flexible matching is mandatory, not an optimization.** Auto-captions drop the
  space at event boundaries essentially always, so exact matching misses most real
  occurrences.
- **Deterministic dictionary replacement runs before any LLM pass**, so the expensive and
  uncertain layer only ever sees what the cheap and certain layer could not fix.

## What these numbers do not support

- Two rounds on 11 videos is a small sample, and both rounds ran the same auditor pair. The
  agreement rates say something about that configuration, not about LLM auditing in general.
- Auditor consensus is a **proxy for correctness**, not correctness. Both auditors can be
  wrong in the same direction, and the registry check only catches the subset of those cases
  where the result is not a real entity.
- The corpus is one domain (Korean stock YouTube), a handful of channels, and one ASR system
  (YouTube auto-captions). See the limitations section in the [README](../README.md).
