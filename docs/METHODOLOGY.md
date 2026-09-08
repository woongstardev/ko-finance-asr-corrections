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

The snapshot holds 210 pairs <!-- stat:pair_count -->:

| Split | Count |
|---|---|
| Tier A — a person approved it | 85 <!-- stat:tier_a --> |
| Tier B — promoted automatically | 125 <!-- stat:tier_b --> |
| `stock` | 111 <!-- stat:category:stock --> |
| `term` | 73 <!-- stat:category:term --> |
| `general` | 14 <!-- stat:category:general --> |
| `other` | 6 <!-- stat:category:other --> |
| `number` | 6 <!-- stat:category:number --> |

`other` is 42 here for a reason that is about tooling rather than vocabulary: until 2026-09-02
the category came only from the registry, so every pair the registry could not resolve landed
there — sector abbreviations, indices carrying a particle, unlisted companies and a handful of
ordinary Korean words, all in one bucket. Those 42 were classified by recorded verdict (`scripts/category-review.tsv`), and the table
above is the result: `other` is now what its name says rather than a record of registry
coverage. Every snapshot since has classified its own new pairs the same way — 31 of them on
2026-09-08 — so the queue the exporter prints is what is genuinely new, not a backlog.

By verification path: 49 `human`, 48 `goldset-alignment`, 38 `auditor-consensus` — the
alignment path did not exist at the first snapshot and is now the second largest, which is why
`evidence` had to stop being implied by `tier`.

Every Tier B pair carries both auditor model ids. Tier A pairs usually carry none — but not
by construction, and one shipped pair (`업항 → 업황`) is Tier A *with* both ids, because a
person approved a pair that had already reached auditor consensus. Provenance therefore
lives in its own `evidence` field rather than being inferred from `tier` or from whether
`auditor_models` is empty. See [`SCHEMA.md`](SCHEMA.md).

## Manual captions are not gold

The obvious way to build an ASR correction dataset is to take videos that have both an
official (human-written) caption track and an auto-generated one, align them, and treat
every difference as an error the ASR made. We measured what that actually yields, and it
does not work the way it sounds.

Pilot, 2026-08-13: **3 videos, ~2h40m, one channel.** Small — read the ratios, not the
absolute counts.

| | |
|---|---|
| Word tokens aligned | 22,213 |
| Mismatching | 18.8% |
| 1:1 substitution candidates | 1,290 (1,116 unique) |
| Registry-verifiable (stocks, names) | 32 unique |
| Latin/numeric (`FMC → FOMC`, `SMP → S&P`, `YY로 → YOY로`) | 110 unique |
| **Everything else — style, not error** | **974 unique (87.3%)** |

**Only 12.7% of the unique differences were misrecognitions.** The rest is a human editor
turning speech into prose: `그니까 → 그러니까`, `요거 → 이거`, dropped fillers, normalized
endings. Treat the official caption as an answer key and you are mostly measuring how
formal the channel's caption writer is.

Worse, the direction is not always what you would assume. In `15% → 15프로`, the official
caption wrote what the speaker actually said and the *auto* caption was the normalized one.
For an archive whose claim is "who said what", verbatim fidelity is the goal and the
official caption is the less faithful text. The same alignment, scored with a different
objective, would call that a regression.

So official captions are not a gold reference. They are a **candidate miner**: high recall,
low precision, cheap to run, and useless without a precision stage. In this pipeline that
stage is the same registry check that governs everything else — which is why pairs found
this way carry `evidence: goldset-alignment` and still have to match a registry entry
verbatim before they ship.

Two consequences worth stating for anyone reproducing this:

- **Restrict scoring to verifiable spans.** Measuring whole-transcript agreement optimizes
  toward prose-normalization, not toward correcting misrecognitions.
- **Official captions contain errors too.** They are a second opinion, not ground truth.

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


## What the damage looks like, at the jamo level

`scripts/jamo_analysis.py` decomposes each pair into Hangul jamo and measures the edit
distance between the misrecognized and verified forms. On the 135-pair snapshot:

| Jamo edit distance | Pairs |
|---|---|
| 1 | 45 (33.3%) |
| 2 | 40 (29.6%) |
| 3 | 28 (20.7%) |
| 4 or more | 22 (16.3%) |

**Nearly two thirds of these errors are one or two jamo wide.** The most frequent single-jamo
substitutions are ㅔ→ㅐ, ㅎ→ㅇ and ㄹ→ㄴ — respectively the vowel merger most Korean speakers
no longer distinguish, h-deletion between voiced sounds, and lateral-nasal confusion. The ASR
is not hallucinating; it is failing on the same contrasts that are weak in the spoken language,
and then a language model picks the wrong word from the neighbourhood.

That is also the argument for why a dictionary helps here at all. If the acoustic difference
between `하이닉스` and `하이니스` is one jamo, no amount of context recovers which listed
company was meant — but an observation that this specific corruption occurred 672 times does.

Two honest limits. This is **jamo, not pronunciation**: no phonological rules are applied, so
the analysis under-counts errors that are identical in speech but differ in spelling. And the
distances are not published as a field — they are a pure function of `(wrong, right)`, and a
stored copy would be one more number to keep in step with the two that determine it.
