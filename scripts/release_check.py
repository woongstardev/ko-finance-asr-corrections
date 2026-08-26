"""Pre-release boundary check — the 2026-08-13 dry-run (task 006), as code.

A check that lives in someone's memory gets skipped; this one is run by
refresh_snapshot.py --write and can be run alone any time:

    python3 scripts/release_check.py

What it enforces (FAIL = do not publish / do not write the snapshot):
  1. No excluded person name appears in data/ in ANY commit. Patterns come
     from the person-exclusion list (upstream first, legacy in-repo second) —
     the check must never know less than the filter does.
  2. No secret-shaped string in any commit (tokens, service_role, key=...).
  3. No internal host / tailnet name in any commit.

What it only WARNS about (known, decision pending with 웅스타 — task 006):
  - scripts/person-exclusions.txt existing anywhere in history (item 1)
  - personal email in commit authorship (item 3)

With --publication (the pre-flip check of task 003) one more class becomes a
FAILURE rather than a warning: internal operational references in the working
tree — upstream task numbers, host paths, timer names, fleet-internal documents.
AGENTS.md forbids committing those, and as of 2026-08-26 the tree breaks that
rule in its planning documents (task 010 §A). Keeping it a warning by default
leaves today's monthly release path working while the publish/withhold decision
is open; making it a failure under --publication stops the tree drifting further
before the flip.

Exit 0 = publishable, 1 = hard finding, plus warnings on stderr either way.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GGULMUSE = Path(
    os.environ.get("GGULMUSE_ROOT", str(Path.home() / "projects" / "ggulmuse"))
).expanduser()

SECRET_PATTERNS = [
    "service_role",
    "supabase[._]co",
    r"api[_-]?key\s*[:=]\s*['\"]",
    r"Bearer [A-Za-z0-9_\-]{16,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY",
]
INTERNAL_HOST_PATTERNS = [
    r"\.ts\.net",
    r"tail[0-9a-f]{6}",
    r"100\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}",
]

# Operational detail that AGENTS.md forbids committing. None of these is a secret;
# together they describe how the upstream pipeline and this fleet are run, which is
# exactly what the hard line is about. Scanned in the working tree only — history is
# a separate, irreversible problem (task 010 §A-3).
INTERNAL_REFERENCE_PATTERNS = [
    r"pipeline-[0-9]{3}",                          # upstream task numbers
    r"~/(projects|orbit|max|alpha|bravo)/",        # host paths
    r"~/\.local/state/[a-z]",  # a concrete state path, not the XDG convention itself
    r"FLEET\.md|WOONGSTAR_CHECK\.md",              # fleet-internal documents
    r"correction_(cycle|dict|corpus|audit)\.py",   # upstream module layout
]
# Files whose entire purpose is internal, and which the publish/withhold decision
# covers as a unit. Listing them keeps the report about *unexpected* leaks; the
# decision itself is task 010 §A-2.
INTERNAL_BY_DESIGN = ("tasks/", "CLAUDE.md", "docs/GGULMUSE-CONTEXT.md")

# Files that legitimately quote the patterns because they document this check.
# Person names are never allowlisted — that check has no such exemption.
PATTERN_DOC_FILES = [
    "scripts/release_check.py",
    "tasks/006-public-boundary-cleanup.md",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    ).stdout


def all_commits() -> list[str]:
    return git("rev-list", "--all").split()


def grep_history(pattern: str, commits: list[str], pathspec: list[str]) -> list[str]:
    hits: list[str] = []
    for rev in commits:
        out = subprocess.run(
            ["git", "grep", "-I", "-i", "-n", "-E", pattern, rev, "--", *pathspec]
            if pathspec
            else ["git", "grep", "-I", "-i", "-n", "-E", pattern, rev],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        hits += out.splitlines()
    return hits


def internal_references() -> dict[str, list[str]]:
    """Working-tree hits, grouped by file. Empty when the tree is clean."""
    found: dict[str, list[str]] = {}
    for pat in INTERNAL_REFERENCE_PATTERNS:
        out = subprocess.run(
            ["git", "grep", "-I", "-n", "-E", pat],
            cwd=REPO, capture_output=True, text=True, check=False,
        ).stdout
        for line in out.splitlines():
            path = line.split(":", 1)[0]
            if path in PATTERN_DOC_FILES:
                continue
            found.setdefault(path, []).append(line)
    return found


def load_person_patterns() -> list[str]:
    names: set[str] = set()
    for path in (
        GGULMUSE / "pipeline" / "data" / "person-exclusions.txt",
        REPO / "scripts" / "person-exclusions.txt",
    ):
        if path.exists():
            names |= {
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            }
    return sorted(names)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--publication", action="store_true",
                    help="pre-flip check: internal references fail instead of warning")
    args = ap.parse_args()

    commits = all_commits()
    failures: list[str] = []
    warnings: list[str] = []

    persons = load_person_patterns()
    if not persons:
        warnings.append("no person-exclusion list found — person check ran with 0 patterns")
    for name in persons:
        hits = grep_history(name, commits, ["data/"])
        if hits:
            failures.append(f"person name '{name}' found in data/ history:\n  " + "\n  ".join(hits))

    for kind, patterns in (
        ("secret-shaped", SECRET_PATTERNS),
        ("internal-host", INTERNAL_HOST_PATTERNS),
    ):
        for pat in patterns:
            hits = grep_history(pat, commits, [])
            hits = [h for h in hits if not any(doc in h for doc in PATTERN_DOC_FILES)]
            if hits:
                failures.append(f"{kind} match /{pat}/:\n  " + "\n  ".join(hits[:20]))

    ever = git("log", "--all", "--pretty=format:", "--name-only").split()
    if "scripts/person-exclusions.txt" in ever:
        warnings.append(
            "scripts/person-exclusions.txt exists in git history "
            "(task 006 item 1 — history handling pending 웅스타 decision)"
        )

    emails = sorted(set(git("log", "--all", "--format=%ae").split()))
    personal = [e for e in emails if not e.endswith("users.noreply.github.com")]
    if personal:
        warnings.append(
            "personal email(s) in commit authorship: "
            + ", ".join(personal)
            + " (task 006 item 3 — rewrite pending 웅스타 decision)"
        )

    refs = internal_references()
    if refs:
        by_design = {f: h for f, h in refs.items()
                     if any(f == d or f.startswith(d) for d in INTERNAL_BY_DESIGN)}
        unexpected = {f: h for f, h in refs.items() if f not in by_design}
        lines = [
            f"internal operational references in {len(refs)} tracked file(s), "
            f"{sum(len(h) for h in refs.values())} line(s) — AGENTS.md forbids "
            "committing these (task 010 §A)",
            f"  internal by design, publish/withhold undecided: {len(by_design)} file(s)",
        ]
        lines += [f"    {f}: {len(h)}" for f, h in sorted(by_design.items())]
        lines.append(f"  not covered by that decision: {len(unexpected)} file(s)")
        lines += [f"    {f}: {len(h)}" for f, h in sorted(unexpected.items())]
        (failures if args.publication else warnings).append("\n".join(lines))

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(1)
    print(f"release_check: OK ({len(commits)} commits scanned, {len(warnings)} warning(s))")


if __name__ == "__main__":
    main()
