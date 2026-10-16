#!/usr/bin/env python3
"""Ask Zenodo whether a GitHub release was actually archived.

    python3 scripts/zenodo_check.py                  # the version in CITATION.cff
    python3 scripts/zenodo_check.py --version v2026.10

Exit 0 = the concept DOI's latest record carries this version (its DOI is
printed), 1 = it does not, 2 = Zenodo could not be asked.

Why this exists
---------------
`gh release create` succeeding says nothing about Zenodo. The archive is made by
a webhook GitHub sends on the release event, and when Zenodo answers it with an
error nothing retries and nothing reports: v2026.10's three deliveries all came
back 500/502, and the release sat without a DOI until someone looked. This asks
the public API, so it needs no credentials, and it is the check to run before
any redelivery - a redelivery after a delivery that did land makes a duplicate
archive.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
API = "https://zenodo.org/api/records/{}"


def citation_field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.M)
    return match.group(1) if match else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--version", help="release tag, e.g. v2026.10 (default: CITATION.cff)")
    args = ap.parse_args()

    cff = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    version = (args.version or citation_field(cff, r'^version: "?([^"\n]+)"?$') or "").lstrip("v")
    # The first DOI listed is the concept DOI; Zenodo resolves its record id to
    # the latest version.
    concept = citation_field(cff, r'value: "10\.5281/zenodo\.(\d+)"')
    if not version or not concept:
        sys.exit("CITATION.cff has no version or no Zenodo concept DOI")

    try:
        with urllib.request.urlopen(API.format(concept), timeout=60) as resp:
            record = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"zenodo_check: could not reach Zenodo ({exc}) - retry later; "
              "do not redeliver the webhook blind", file=sys.stderr)
        sys.exit(2)

    latest = (record.get("metadata") or {}).get("version")
    if latest == version:
        print(f"zenodo_check: OK - {version} archived as {record.get('doi')}")
        return
    print(f"zenodo_check: NOT ARCHIVED - latest Zenodo version is {latest!r}, expected "
          f"{version!r}.\n  Look at the webhook deliveries (gh api repos/<repo>/hooks/<id>/"
          "deliveries); if none is a 202, redeliver the `released` one once.\n"
          "  Delivery ids are 19 digits: read them as strings, not through --jq.",
          file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
