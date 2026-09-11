#!/usr/bin/env python3
"""Turn the working tree into a release commit: CHANGELOG, CITATION, schema freeze.

    python3 scripts/prepare_release.py --version v0.1              # show the diff
    python3 scripts/prepare_release.py --version v0.1 --write      # apply it

Then review, commit, and tag. **This script never tags, pushes, or publishes** -
those are the irreversible half and they stay with a person.

Why this exists
---------------
A release here is three edits in three files that have to agree, and the cost of
getting them wrong is asymmetric: a snapshot published under a version that says
`0.1.0-dev`, or a CHANGELOG whose Unreleased section quietly became the release
notes of the *next* version, is wrong in the published artifact rather than in a
draft. The monthly calendar releases (`vYYYY.MM`) repeat all three, so the
second time this runs it is already cheaper than doing it by hand.

What it changes
    CHANGELOG.md   `## [Unreleased]` becomes `## [<version>] - <date>`, and a
                   fresh empty Unreleased section takes its place.
    CITATION.cff   `version:` and `date-released:`. The version is the tag
                   without its leading v, so `v0.1` publishes as `0.1`; pass
                   --cff-version when the citation needs a different string
                   (`v0.1` -> `0.1.0` for the first release, by convention).
    docs/SCHEMA.md the "draft - will be frozen" title and the freeze TODO, but
                   only for v0.1: after that the schema is frozen and a change
                   is a version bump, which is a different job.

Refuses to run on a dirty tree. A release commit that also carries unrelated
edits cannot be reviewed as a release.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCHEMA_TITLE_OLD = "# Data schema (draft — will be frozen at v0.1)"
SCHEMA_TITLE_NEW = "# Data schema (frozen at v0.1)"
SCHEMA_TODO = "<!-- TODO(v0.1): freeze field list, then version the schema. -->"
SCHEMA_FROZEN = """**Frozen as of v0.1.** The field list, types and enum values above are the published
contract: a change to any of them is a minor version of this dataset, announced in
`CHANGELOG.md`, and `scripts/validate_snapshot.py` fails the release that tries to ship one
silently. Adding a field is still a minor version - a consumer that selects columns by name
is entitled to know. What is *not* frozen: the pairs themselves, their frequencies, and the
category verdicts behind `scripts/category-review.tsv`, all of which move every snapshot."""


def dirty() -> list[str]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                         capture_output=True, text=True, check=False).stdout
    return [line for line in out.splitlines() if line.strip()]


def edit_changelog(text: str, version: str, when: str) -> str:
    marker = "## [Unreleased]"
    if marker not in text:
        sys.exit("CHANGELOG.md has no '## [Unreleased]' section to release")
    if f"## [{version}]" in text:
        sys.exit(f"CHANGELOG.md already has a {version} section")
    return text.replace(marker, f"## [Unreleased]\n\n## [{version}] - {when}", 1)


def edit_citation(text: str, cff_version: str, when: str) -> str:
    text, n = re.subn(r'^version: .*$', f"version: {cff_version}", text, count=1, flags=re.M)
    if not n:
        sys.exit("CITATION.cff has no 'version:' line")
    text, n = re.subn(r'^date-released: .*$', f'date-released: "{when}"', text,
                      count=1, flags=re.M)
    if not n:
        sys.exit("CITATION.cff has no 'date-released:' line")
    return text


def edit_schema(text: str) -> str:
    if SCHEMA_TITLE_OLD in text:
        text = text.replace(SCHEMA_TITLE_OLD, SCHEMA_TITLE_NEW, 1)
    if SCHEMA_TODO in text:
        text = text.replace(SCHEMA_TODO, SCHEMA_FROZEN, 1)
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", required=True, help="release tag, e.g. v0.1 or v2026.10")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--cff-version", default=None,
                    help="citation version string (default: the tag without its v)")
    ap.add_argument("--write", action="store_true", help="apply; without it, print the diff")
    args = ap.parse_args()

    if args.write and (changes := dirty()):
        sys.exit("working tree is not clean - commit or stash first:\n  "
                 + "\n  ".join(changes[:10]))

    cff_version = args.cff_version or args.version.lstrip("v")
    plans = [
        (REPO / "CHANGELOG.md", lambda t: edit_changelog(t, args.version, args.date)),
        (REPO / "CITATION.cff", lambda t: edit_citation(t, cff_version, args.date)),
    ]
    if args.version == "v0.1":
        plans.append((REPO / "docs" / "SCHEMA.md", edit_schema))

    touched = 0
    for path, edit in plans:
        before = path.read_text(encoding="utf-8")
        after = edit(before)
        if before == after:
            print(f"{path.name}: nothing to change")
            continue
        touched += 1
        if args.write:
            path.write_text(after, encoding="utf-8")
            print(f"{path.name}: updated")
        else:
            sys.stdout.writelines(difflib.unified_diff(
                before.splitlines(keepends=True), after.splitlines(keepends=True),
                fromfile=f"a/{path.name}", tofile=f"b/{path.name}"))

    if not args.write:
        print(f"\n(dry run - {touched} file(s) would change; pass --write to apply)")
        return
    print("\nNext, and none of it automated on purpose:")
    print("  1. python3 scripts/validate_snapshot.py && python3 scripts/release_check.py --publication")
    print("  2. review the diff, commit")
    print(f"  3. enable the Zenodo GitHub integration BEFORE tagging - a tag pushed first")
    print("     is never archived and cannot be attached to a concept DOI afterwards")
    print(f"  4. git tag {args.version} && git push origin {args.version}")
    print("  5. add the concept DOI to CITATION.cff identifiers once Zenodo issues it")


if __name__ == "__main__":
    main()
