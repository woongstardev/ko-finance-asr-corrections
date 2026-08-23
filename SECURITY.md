# Security and privacy reports

This repository ships data files and a self-contained, standard-library-only scorer. It runs
no service and holds no credentials, so "security" here is mostly about a **privacy boundary**
— and that boundary is the most serious thing this project can get wrong.

## Report privately, not in a public issue

Email **oss@woongstar.com**, or use GitHub's private reporting on this repository
(**Security → Report a vulnerability**).

Please do **not** open a public issue for the reports below. A public issue that quotes the
offending name or caption text republishes exactly what the report is asking us to remove.

## What we especially want to hear about

| Report | Why it is urgent |
|---|---|
| A **person's name** appears in `data/`, in the git history, or anywhere in this repo | The project's hard line is that no person-name pair ships. A leak here is a privacy failure, not a data-quality bug |
| **Caption text or a source sentence** appears anywhere in the repo | Only pairs, counts and metadata are meant to be publishable |
| An internal host, path, or credential-shaped string appears in any commit | Should be impossible — `scripts/release_check.py` scans every commit before a release — but a miss is worth knowing about |
| A shipped pair damages correct text | Not private; use the [over-correction form](../../issues/new?template=bad-pair.yml). Listed here so the two paths don't get confused |

## What happens after a report

1. Confirmation that we received it, and whether we can reproduce it.
2. Removal upstream first (the published data is an export; deleting only the exported copy
   would let it return in the next snapshot), then a re-export and a patch release.
3. If the material is in git history rather than the current tree, history rewriting is on the
   table — that is an irreversible, owner-only decision and it has been done before.

Response is best-effort by a single maintainer, not an SLA. Privacy reports are handled ahead
of everything else in the queue.
