# Verification methodology (draft)

How pairs get promoted into this dataset **without a gold-label corpus**.

```
mine candidates from corpus (repetition across videos/channels)
        │
        ▼
two LLM auditors judge each candidate INDEPENDENTLY (no shared context)
        │
        ▼
consensus-only adoption  ──  disagreement → stays a candidate
        │
        ▼
external fact check: does `right` exist verbatim in a registry?
(listed-stock spellings ~20K · finance glossary)
        │
        ▼
3-tier promotion:  A human-approved · B registry+consensus · C neither (never ships)
        │
        ▼
instant rollback: any pair observed causing a wrong replacement in production
is disabled immediately and removed from the next snapshot
```

Design rules learned from production incidents:

- **Never replace with a different real entity.** Registry membership alone is not enough —
  observed failure modes include swapping to a different person or a different stock,
  and polarity reversal. These are permanently forbidden regardless of tier.
- **Minimum key length 2**, and prefer long keys (context inside the key, e.g.
  `외한 시장→외환 시장` instead of `외한→외환`) over post-hoc guard logic.
- Deterministic dictionary replacement runs **before** any LLM correction pass, so the
  expensive/uncertain layer only sees what the cheap/certain layer could not fix.

Measured over two production audit rounds: both-auditors-OK rate 81.9% / 81.3%.

<!-- TODO(v0.1): write up as a proper doc with numbers per round, auditor model list,
     and the promotion/rollback state machine. This is the part a tech report cites. -->
