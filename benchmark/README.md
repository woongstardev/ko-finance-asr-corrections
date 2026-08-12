# Benchmark (draft)

Task: **given Korean finance-domain sentences containing ASR misrecognitions, fix them
without over-correcting.**

Planned for v0.1:

- `score.py` — port of the production scorer (`score_round`): counts fixed / missed /
  over-corrected, reports per-category breakdown.
- Evaluation protocol doc: what counts as a fix, how over-correction is penalized,
  tie to the pair dataset in `data/`.

<!-- TODO(v0.1): port score_round from the production pipeline (strip pipeline
     dependencies, pure stdlib), define the public eval input format, and decide the
     evaluation sentence source (synthetic templates from pairs — NOT source captions). -->
