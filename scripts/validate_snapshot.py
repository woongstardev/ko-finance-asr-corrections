#!/usr/bin/env python3
"""Check a snapshot against the contract docs/SCHEMA.md publishes.

    python3 scripts/validate_snapshot.py                 # validate data/
    python3 scripts/validate_snapshot.py --dir /tmp/x    # validate a candidate export

Exit 0 = the snapshot matches the published schema. Exit 1 = it does not.

Why this exists
---------------
`release_check.py` guards the *boundary* (person names, secrets, internal
infrastructure). Nothing guarded the *contract*: docs/SCHEMA.md promises a field
list, types, enum values and a primary key, and until now an upstream change
could drift any of them and still export cleanly. v0.1 declares the schema
frozen, and a freeze nobody watches is a sentence, not a guarantee.

Rules are hardcoded here rather than loaded from a schema framework. Table
Schema and friends remain the ecosystem standard (checked 2026-08-14, unchanged
2026-08-23), but they are third-party dependencies, and this repository's
survival rule is that nothing here needs `pip install`. The cost of that choice
is two places to keep in step, so **every rule below cites the SCHEMA.md section
it enforces, and a SCHEMA.md change is expected to arrive with a change here**
(AGENTS.md says so too).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GGULMUSE_DEFAULT = Path.home() / "projects" / "ggulmuse"

# SCHEMA.md "Files": pairs.json is canonical, pairs.csv is the same rows flat.
FIELDS: dict[str, object] = {
    "wrong": str,
    "right": str,
    "corpus_count": (int, type(None)),  # nullable when the counts artifact was absent
    # SCHEMA.md → field table. Same scan, same nullability: null means the artifact
    # did not carry the verified form, while 0 is an observation — the correct
    # spelling was never once transcribed correctly in the whole corpus.
    "right_count": (int, type(None)),
    # SCHEMA.md → field table. Registry identity of the corrected term; null for
    # every row the registry does not resolve, which is most non-stock rows.
    "ticker": (str, type(None)),
    "market": (str, type(None)),
    "observed_count": int,
    "tier": str,
    "evidence": str,
    "category": str,
    "auditor_models": list,
    "approved_at": str,
    "word_boundary": bool,
    "apply_scope": str,
}
# SCHEMA.md field table. `unknown` is called out there as a bug, not a category,
# so it is a failure here rather than an accepted enum member.
ENUMS = {
    "tier": {"A", "B"},
    "evidence": {"human", "auditor-consensus", "goldset-alignment"},
    "category": {"stock", "term", "number", "other"},
}
META_KEYS = ("dataset", "exported_at", "pair_count", "corpus", "pairs")

# Prose numbers carry a marker naming the statistic they quote; the checker then
# requires that statistic's real value to appear on the marked line. This is the
# cheap half of the fix for the 2026-08-13 incident, where a refresh updated
# data/ to a 595-video corpus and left 521 standing in four prose files.
STAT_MARKER = re.compile(r"<!--\s*stat:([A-Za-z_]+)(?::([^\s>]+))?\s*-->")
# CHANGELOG.md is deliberately absent: its entries are historical records, and a
# released line must keep the number it shipped with. Marking it would demand that
# last month's release notes track this month's data.
# The HF card is in here because it is the file most likely to go stale unnoticed:
# it is a copy of claims that live elsewhere, and it is read by people who never
# see this repository. It was three snapshots out of date when it joined the list.
MARKED_FILES = ("README.md", "docs/SCHEMA.md", "benchmark/README.md",
                "docs/hf-dataset-card.md", "docs/METHODOLOGY.md")


def exclusion_names(ggulmuse: Path) -> tuple[set[str], list[Path]]:
    """Same union the exporter filters with — upstream list first, legacy second.

    The check must never know less than the filter does, so it reads the same
    two places rather than a copy.
    """
    names: set[str] = set()
    found: list[Path] = []
    for path in (
        ggulmuse / "pipeline" / "data" / "person-exclusions.txt",
        REPO / "scripts" / "person-exclusions.txt",
    ):
        if path.exists():
            found.append(path)
            names |= {
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            }
    return names, found


def check_pairs(payload: dict, fail, warn) -> None:
    for key in META_KEYS:
        if key not in payload:
            fail(f"pairs.json is missing top-level '{key}' (SCHEMA.md → Files)")
    pairs = payload.get("pairs") or []
    if payload.get("pair_count") != len(pairs):
        fail(f"pair_count {payload.get('pair_count')} != {len(pairs)} pairs")

    corpus = payload.get("corpus") or {}
    if not isinstance(corpus.get("scanned_videos"), int):
        fail("corpus.scanned_videos missing or not an int (SCHEMA.md → Files)")

    # SCHEMA.md → corpus_count. A scan that reached nothing is not a snapshot with
    # small numbers, it is a broken scan. 2026-08-27: the upstream transcript tree
    # disappeared between two runs, the recount reported 0 videos, every
    # corpus_count went to 0, and both this validator and the benchmark gate
    # passed the result — zero is a legal int and the benchmark never reads the
    # counts. Frequency is the headline claim of this dataset; it fails loudly now.
    # SCHEMA.md → Files. The profile is optional, but a partial one is a bug:
    # it is written by one script in one pass, so a missing half means something
    # truncated it.
    profile_keys = {"channels", "hours", "mean_video_minutes"}
    present = profile_keys & set(corpus)
    if present and present != profile_keys:
        fail(f"corpus profile is partial: has {sorted(present)}, missing "
             f"{sorted(profile_keys - present)} (SCHEMA.md → Files)")
    for key in present:
        if not isinstance(corpus[key], (int, float)) or corpus[key] <= 0:
            fail(f"corpus.{key} must be a positive number, got {corpus[key]!r}")

    counted = [
        pair.get("corpus_count") for pair in pairs
        if isinstance(pair.get("corpus_count"), int)
        and not isinstance(pair.get("corpus_count"), bool)
    ]
    scanned = corpus.get("scanned_videos")
    if pairs and counted:
        if isinstance(scanned, int) and scanned <= 0:
            fail("corpus.scanned_videos is 0 but corpus_count is populated — the "
                 "frequency scan reached no transcripts (SCHEMA.md → corpus_count)")
        if not any(counted):
            fail(f"every corpus_count is 0 across {len(counted)} pair(s) — a pair "
                 "ships because it was observed, so an all-zero column means the "
                 "counts artifact is broken, not the corpus "
                 "(SCHEMA.md → corpus_count)")
    elif pairs and isinstance(scanned, int) and scanned <= 0:
        warn("no corpus_count on any pair and scanned_videos is 0 — exported "
             "without a counts artifact (SCHEMA.md allows null, but check it)")

    seen: dict[tuple[str, str], int] = {}
    for idx, pair in enumerate(pairs):
        where = f"pair[{idx}] {pair.get('wrong')!r}->{pair.get('right')!r}"
        for field, expected in FIELDS.items():
            if field not in pair:
                fail(f"{where}: missing field '{field}' (SCHEMA.md → field table)")
                continue
            if not isinstance(pair[field], expected):
                fail(f"{where}: '{field}' is {type(pair[field]).__name__}, "
                     f"expected {expected} (SCHEMA.md → field table)")
        for field, allowed in ENUMS.items():
            value = pair.get(field)
            if value is not None and value not in allowed:
                extra = (" — SCHEMA.md calls this a bug to fix, not a category"
                         if value == "unknown" else "")
                fail(f"{where}: {field}={value!r} not in {sorted(allowed)}{extra}")
        if not isinstance(pair.get("auditor_models"), list) or any(
            not isinstance(m, str) for m in pair.get("auditor_models") or []
        ):
            fail(f"{where}: auditor_models must be a list of strings")
        if pair.get("wrong") == pair.get("right"):
            fail(f"{where}: wrong == right, which corrects nothing")

        key = (pair.get("wrong"), pair.get("right"))
        if key in seen:
            fail(f"{where}: duplicate primary key, first seen at pair[{seen[key]}] "
                 f"(SCHEMA.md → 'Primary key: the (wrong, right) tuple')")
        seen[key] = idx

    # The exporter's ordering, restated: frequency desc, then observed desc, then
    # key. Item ids in the benchmark are derived from a sorted view, so a silent
    # reordering here is a silent reshuffle downstream.
    def sort_key(r: dict) -> tuple:
        # Ill-typed rows already failed above; coerce here so a bad type reports
        # as a type error rather than crashing the run with a TypeError.
        counts = [r.get("corpus_count"), r.get("observed_count")]
        counts = [-c if isinstance(c, int) and not isinstance(c, bool) else 0 for c in counts]
        return (*counts, str(r.get("wrong") or ""))

    ordered = sorted(pairs, key=sort_key)
    if [p.get("wrong") for p in pairs] != [p.get("wrong") for p in ordered]:
        fail("pairs are not in the exporter's sort order "
             "(corpus_count desc, observed_count desc, wrong asc)")


def check_csv(payload: dict, csv_path: Path, fail, warn) -> None:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    pairs = payload.get("pairs") or []
    if len(rows) != len(pairs):
        fail(f"pairs.csv has {len(rows)} rows, pairs.json has {len(pairs)}")
        return
    for idx, (row, pair) in enumerate(zip(rows, pairs)):
        for field in FIELDS:
            got, want = row.get(field), pair.get(field)
            if field == "auditor_models":
                want = ";".join(want or [])
            elif want is None:
                want = ""
            else:
                want = str(want)
            if got != want:
                fail(f"row {idx} field '{field}': csv {got!r} != json {want!r}")
                return  # one report is enough; they are generated together


WITHDRAWN_FIELDS: dict[str, object] = {
    "wrong": str,
    "right": str,
    "withdrawn_at": str,
    "reason": str,
    "evidence_kind": str,
    "corpus_count": (int, type(None)),
    "justified_matches": (int, type(None)),
    "replaced_by": list,
    "shipped_in": list,
    "why": str,
}
WITHDRAWN_REASONS = {"over-correction", "ambiguous-target", "artifact"}
WITHDRAWN_EVIDENCE = {"corpus-counterexample", "user-report", "audit"}


def check_biasing_list(payload: dict, path: Path, fail, warn) -> None:
    """SCHEMA.md → Files. A derived file that nobody regenerates is a stale file.

    `data/biasing-list.txt` is produced from the same pairs; the only way it can
    be wrong is by being older than they are, so the check is set equality
    against the verified forms rather than a format check.
    """
    if not path.exists():
        return
    listed = {
        line.split("\t")[0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    expected = {p.get("right") for p in payload.get("pairs") or []}
    missing, extra = expected - listed, listed - expected
    if missing or extra:
        fail(f"biasing-list.txt is out of date with pairs.json "
             f"({len(missing)} missing, {len(extra)} stale) — "
             "run scripts/make_biasing_list.py")
    else:
        print(f"  biasing list: {len(listed)} terms, in sync")


def check_withdrawn(payload: dict, path: Path, fail, warn) -> None:
    """SCHEMA.md → Withdrawn pairs. Optional file; strict when present.

    The rule that matters is the last one: a withdrawn pair must not also be a
    shipped pair. Withdrawal is the only patch-release trigger this dataset has,
    so a key reappearing in pairs.json while the history still says it was unsafe
    is the one way this file can mislead rather than inform.
    """
    if not path.exists():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = doc.get("withdrawn")
    if not isinstance(rows, list):
        fail("withdrawn.json has no 'withdrawn' list (SCHEMA.md → Withdrawn pairs)")
        return

    shipped = {(p.get("wrong"), p.get("right")) for p in payload.get("pairs") or []}
    seen: set[tuple] = set()
    for idx, row in enumerate(rows):
        where = f"withdrawn[{idx}] {row.get('wrong')!r}->{row.get('right')!r}"
        for field, expected in WITHDRAWN_FIELDS.items():
            if field not in row:
                fail(f"{where}: missing field {field!r} (SCHEMA.md → Withdrawn pairs)")
            elif not isinstance(row[field], expected):
                fail(f"{where}: {field!r} is {type(row[field]).__name__}, expected {expected}")
        if row.get("reason") not in WITHDRAWN_REASONS:
            fail(f"{where}: reason={row.get('reason')!r} not in {sorted(WITHDRAWN_REASONS)}")
        if row.get("evidence_kind") not in WITHDRAWN_EVIDENCE:
            fail(f"{where}: evidence_kind={row.get('evidence_kind')!r} not in "
                 f"{sorted(WITHDRAWN_EVIDENCE)}")
        justified, total = row.get("justified_matches"), row.get("corpus_count")
        if isinstance(justified, int) and isinstance(total, int) and justified > total:
            fail(f"{where}: justified_matches {justified} exceeds corpus_count {total}")
        key = (row.get("wrong"), row.get("right"))
        if key in seen:
            fail(f"{where}: duplicate entry")
        seen.add(key)
        if key in shipped:
            fail(f"{where}: this pair is also in pairs.json — a key cannot be both "
                 "withdrawn and shipped (SCHEMA.md → Withdrawn pairs)")
    print(f"  withdrawn: {len(rows)} entr(y|ies), none shipped")


def check_person_names(payload: dict, ggulmuse: Path, require: bool, fail, warn) -> None:
    """Last line of defence, after the exporter's filter (AGENTS.md hard line)."""
    names, sources = exclusion_names(ggulmuse)
    if not names:
        message = ("no person-exclusion list found — this check ran with 0 patterns "
                   "and proves nothing")
        (fail if require else warn)(message)
        return
    haystack = [(p.get("wrong", ""), p.get("right", "")) for p in payload.get("pairs") or []]
    for name in sorted(names):
        for wrong, right in haystack:
            if name in wrong or name in right:
                fail(f"person name found in a shipped pair: {wrong!r}->{right!r}")
    print(f"  person check: {len(names)} patterns from {len(sources)} list(s)")


def check_prose_stats(payload: dict, fail, warn) -> None:
    """Every marked prose line must quote the live number."""
    pairs = payload.get("pairs") or []
    counts = {p["wrong"]: p.get("corpus_count") for p in pairs}
    # SCHEMA.md → right_count. An error rate is the one number here a reader is
    # most likely to quote back, and it is derived from two fields that both move
    # every month, so prose that states one gets checked like any other stat.
    # Rounded to one decimal, the way the prose writes it.
    rates = {}
    for pair in pairs:
        wrong, right = pair.get("corpus_count"), pair.get("right_count")
        if isinstance(wrong, int) and isinstance(right, int) and wrong + right:
            rates[pair["wrong"]] = f"{wrong / (wrong + right) * 100:.1f}"
    corpus = payload.get("corpus") or {}
    # Composition counts are here because they are exactly what drifted twice:
    # marked lines followed the snapshot automatically while sentences describing
    # the same snapshot in words did not.
    tiers = [p.get("tier") for p in pairs]
    stats: dict[str, object] = {
        "pair_count": payload.get("pair_count"),
        "scanned_videos": corpus.get("scanned_videos"),
        "corpus_channels": corpus.get("channels"),
        "corpus_hours": corpus.get("hours"),
        "tier_a": tiers.count("A"),
        "tier_b": tiers.count("B"),
        # The guarded baseline's population: keys long enough to survive a
        # four-character floor. Quoted in benchmark/README.md, and it moves every
        # time the snapshot gains short keys.
        "guarded_keys": sum(1 for p in pairs
                            if len((p.get("wrong") or "").replace(" ", "")) >= 4),
    }
    categories = {}
    for pair in pairs:
        category = pair.get("category")
        if category:
            categories[category] = categories.get(category, 0) + 1
    eval_path = REPO / "benchmark" / "eval-set.json"
    if eval_path.exists():
        ev = json.loads(eval_path.read_text(encoding="utf-8"))
        stats["eval_items"] = sum((ev.get("item_counts") or {}).values())
        stats["trap_count"] = (ev.get("item_counts") or {}).get("trap")

    marked = 0
    for rel in MARKED_FILES:
        path = REPO / rel
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in STAT_MARKER.finditer(line):
                marked += 1
                stat, arg = match.group(1), match.group(2)
                if stat == "category" and arg is not None:
                    if arg not in categories:
                        fail(f"{rel}:{lineno}: stat:category:{arg} is not a category "
                             "in this snapshot")
                        continue
                    value = categories[arg]
                elif stat == "rate" and arg is not None:
                    if arg not in rates:
                        fail(f"{rel}:{lineno}: stat:rate:{arg} names a pair with no "
                             "error rate in the snapshot")
                        continue
                    # The rate is written as 87.9, so match the decimal form found
                    # on the line rather than the integer scan used below.
                    written = set(re.findall(r"\d+\.\d", line))
                    if rates[arg] not in written:
                        fail(f"{rel}:{lineno}: marked for rate:{arg} = {rates[arg]}%, "
                             f"but the line says {sorted(written) or 'no rate'}")
                    continue
                elif stat == "count" and arg is not None:
                    if arg not in counts:
                        fail(f"{rel}:{lineno}: stat:count:{arg} names a pair that is "
                             "no longer in the snapshot")
                        continue
                    value = counts[arg]
                elif stat in stats:
                    value = stats[stat]
                else:
                    fail(f"{rel}:{lineno}: unknown stat marker {match.group(0)}")
                    continue
                # Decimals as well as integers: a corpus is 672.3 hours, and
                # scanning for \d[\d,]* alone would read that as 672 and 3 and
                # fail a line that is perfectly correct.
                numbers = {n.replace(",", "")
                           for n in re.findall(r"\d[\d,]*(?:\.\d+)?", line)}
                if str(value) not in numbers:
                    fail(f"{rel}:{lineno}: marked for {stat}"
                         f"{':' + arg if arg else ''} = {value}, but the line says "
                         f"{sorted(numbers) or 'no number'}")
    print(f"  prose stats: {marked} marked line(s) checked")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=REPO / "data",
                    help="directory holding pairs.json/pairs.csv")
    ap.add_argument("--ggulmuse", type=Path, default=GGULMUSE_DEFAULT)
    ap.add_argument("--require-person-list", action="store_true",
                    help="fail (not warn) when no exclusion list is available")
    ap.add_argument("--skip-prose", action="store_true",
                    help="skip prose markers when validating a candidate export")
    ap.add_argument("--warn-only", action="store_true",
                    help="report findings without failing (dry-run mode)")
    args = ap.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    warn = warnings.append
    fail = warn if args.warn_only else failures.append

    payload = json.loads((args.dir / "pairs.json").read_text(encoding="utf-8"))
    check_pairs(payload, fail, warn)
    check_csv(payload, args.dir / "pairs.csv", fail, warn)
    check_person_names(payload, args.ggulmuse, args.require_person_list, fail, warn)
    check_withdrawn(payload, args.dir / "withdrawn.json", fail, warn)
    check_biasing_list(payload, args.dir / "biasing-list.txt", fail, warn)
    if not args.skip_prose:
        check_prose_stats(payload, fail, warn)

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(f"validate_snapshot: {len(failures)} failure(s)")
    print(f"validate_snapshot: OK ({payload.get('pair_count')} pairs, "
          f"{len(warnings)} warning(s))")


if __name__ == "__main__":
    main()
