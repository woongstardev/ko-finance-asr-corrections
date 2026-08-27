# Contributing

Thanks for looking. This repository is unusual in one way that determines everything below:
**it is a published snapshot, not the source of truth.** The pairs in `data/` are exported
from the production correction dictionary of the [껄무새 (Ggulmuse)](https://ggulmuse.woongstar.com)
pipeline, where every pair has already passed two independent LLM auditors and an external
registry check. What you see here is the filtered, public-safe slice of that dictionary.

So the contribution paths are shaped differently for data and for code.

## Data: propose, don't patch

`data/pairs.json`, `data/pairs.csv`, `data/withdrawn.json` and `data/biasing-list.txt` are
generated files — the last one by `scripts/make_biasing_list.py`, which the validator checks
for drift. **Pull requests that edit them
will be closed**, not because the change is unwelcome but because it would be overwritten by
the next monthly export — and because a pair that skipped upstream verification would break
the guarantee the dataset makes about its own provenance.

| You want to | Do this | What happens next |
|---|---|---|
| Add a pair we're missing | [Propose a correction pair](../../issues/new?template=new-pair.yml) | Upstream verification (auditor consensus + registry) → next monthly snapshot |
| Report a pair that over-corrects | [Report an over-correction](../../issues/new?template=bad-pair.yml) | Recalled upstream, re-exported — this is the only trigger for a patch release |
| Report a field value that looks wrong | Issue, after checking [`docs/SCHEMA.md`](docs/SCHEMA.md) | Fixed upstream, corrected in the next snapshot |

Verification is not instant and not guaranteed: a proposal that the auditors do not agree on,
or that the registry does not confirm, stays out. That is the point of the loop —
see [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md), including the measured ~1-in-10
over-correction rate that made the benchmark score over-corrections at all.

### The one hard rule

**Never paste caption text, transcripts, or person names** — not in issues, not in PRs, not in
example data. This dataset deliberately ships pairs, counts and metadata only, and misheard
person names are an error class it does not cover *by policy*, not by oversight. When you need
to show a failure, write a short example sentence of your own; a constructed sentence
reproduces a string replacement just as well as a real one.

If a person's name or caption text has already reached the published data, that is a private
report, not a public issue — see [`SECURITY.md`](SECURITY.md).

## Code: normal pull requests

`benchmark/` and `scripts/` are ordinary MIT-licensed Python and take ordinary PRs.

- **Standard library only.** No third-party imports, in either directory. This is a survival
  constraint, not a style preference: the Korean NLP ecosystem is a graveyard of packages that
  died with a dependency (py-hanspell went down with an unofficial API, KoNLPy froze under its
  Java dependency). A dataset that needs `pip install` to be *scored* is a dataset that stops
  being scorable. Vendor what you truly need instead.
- **Run the tests**: `python3 benchmark/test_score.py` (they need nothing installed).
- **Don't change scoring semantics silently.** The published baseline table in
  `README.md` and `benchmark/results/*.json` are claims; if a change moves the numbers, move
  them in the same PR and say why in the commit message.
- Commit messages in English. Single `main` branch, no long-lived forks needed.

## Licensing of contributions

By contributing you agree that your contribution is licensed the same way the surrounding
material is: data under [CC BY 4.0](LICENSE-DATA), code under [MIT](LICENSE).

## Conduct

This project follows the [Contributor Covenant 3.0](CODE_OF_CONDUCT.md).
