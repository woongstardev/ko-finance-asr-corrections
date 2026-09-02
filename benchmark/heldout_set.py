#!/usr/bin/env python3
"""Extract the held-out slice of the evaluation set: items the previous snapshot did not have.

    python3 benchmark/heldout_set.py --out /tmp/heldout-2026-09.json
    python3 benchmark/baselines.py --mode boundary --eval /tmp/heldout-2026-09.json \
        --pairs <previous snapshot pairs.json>
    python3 benchmark/llm_reference.py --transport cli --eval /tmp/heldout-2026-09.json \
        --label heldout-2026-09

Why this exists
---------------
The benchmark's structural weakness is that its items are generated from the
pairs themselves, so a dictionary baseline scores 100% recall by construction.
Withholding pairs would fix that and is not an option here - "everything that is
verified ships" is the argument this dataset makes.

Time gives the same effect for free. Pairs promoted after a measurement were, by
definition, unseen by it, so each month's added items are a held-out set for
every system measured before them. The first measurement (2026-08-27) is the
reversal the in-domain table cannot show: the previous snapshot's dictionary
scores 2.3% where an LLM scores 72.9%.

That extraction was done by hand once. This is the second month, so it is a
script - and the ids make it exact rather than approximate: the eval set is
append-only with content-derived ids, so "new this month" is a set difference,
not a heuristic.

Withdrawn pairs
---------------
A pair that leaves the snapshot takes its items with it, so the current set is
append-only apart from those losses. They are expected (scripts/benchmark_gate.py
says the same) and are reported, not fatal; only a wholesale rebuild is refused.

Baseline resolution
-------------------
By default the baseline is the most recent committed version of the eval set
whose item ids differ from the current file - which is the previous snapshot's
eval set whether or not this month's regeneration has been committed yet. Pass
--baseline to name a file, or --baseline-rev to name a revision.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVAL_REL = "benchmark/eval-set.json"
DEFAULT_EVAL = REPO / EVAL_REL
# Share of baseline items that may vanish before the difference stops being a
# month of growth and starts being a rebuild. See the check that uses it.
REBUILD_SHARE = 0.1


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout


def ids_of(doc: dict) -> set[str]:
    return {item["id"] for item in doc["items"]}


def previous_committed(current_ids: set[str]) -> tuple[dict, str]:
    """The newest committed eval set that is not the current one.

    Frequency drift rewrites the file without changing which items exist, so
    revisions are compared by item ids rather than by bytes: a snapshot that
    only moved counts is not a previous snapshot for held-out purposes.
    """
    revs = git("log", "--format=%H", "--", EVAL_REL).split()
    for rev in revs:
        try:
            doc = json.loads(git("show", f"{rev}:{EVAL_REL}"))
        except (RuntimeError, ValueError):
            continue
        if ids_of(doc) != current_ids:
            return doc, rev
    raise SystemExit(
        "no earlier eval set found in git history - the first snapshot has no held-out slice"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--eval", type=Path, default=DEFAULT_EVAL, dest="eval_path")
    ap.add_argument("--baseline", type=Path, default=None,
                    help="previous eval set as a file (default: resolve from git history)")
    ap.add_argument("--baseline-rev", default=None,
                    help="previous eval set as a git revision, e.g. HEAD~1")
    ap.add_argument("--out", type=Path, default=None,
                    help="write the held-out eval set here (default: stdout summary only)")
    args = ap.parse_args()

    current = json.loads(args.eval_path.read_text(encoding="utf-8"))
    current_ids = ids_of(current)

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        origin = str(args.baseline)
    elif args.baseline_rev:
        baseline = json.loads(git("show", f"{args.baseline_rev}:{EVAL_REL}"))
        origin = f"{args.baseline_rev}:{EVAL_REL}"
    else:
        baseline, rev = previous_committed(current_ids)
        origin = f"{rev[:7]}:{EVAL_REL}"

    baseline_ids = ids_of(baseline)
    dropped = len(baseline_ids - current_ids)
    # A withdrawn pair takes its items with it, which scripts/benchmark_gate.py
    # already calls an expected loss rather than a finding - mini-v0.3 to v0.4
    # lost 5 of 689 items that way (0.7%). A rebuilt set is a different animal:
    # the one --no-carry-over rebuild in this repo's history dropped 442 of 482
    # (92%), and a delta against that is not a held-out slice, it is two
    # benchmarks subtracted from each other.
    if dropped > len(baseline_ids) * REBUILD_SHARE:
        sys.exit(f"{dropped} of {len(baseline_ids)} baseline items are absent from the "
                 "current eval set - it was rebuilt, not appended to; a held-out slice "
                 "is not meaningful across a rebuild")

    items = [item for item in current["items"] if item["id"] not in baseline_ids]
    if not items:
        sys.exit(f"no new items since {origin} - nothing to measure this month")

    counts: dict[str, int] = {}
    for item in items:
        key = item["kind"]
        if item.get("variant"):
            key = f"{key}:{item['variant']}"
        counts[key] = counts.get(key, 0) + 1
    pairs = sorted({item["wrong"] for item in items if "wrong" in item})

    doc = {
        "benchmark": current["benchmark"],
        "slice": "held-out",
        "generated_at": current["generated_at"],
        "baseline": {
            "origin": origin,
            "benchmark": baseline.get("benchmark"),
            "pair_count": baseline.get("pair_count"),
            "item_count": len(baseline_ids),
        },
        "pair_count": len(pairs),
        "item_counts": counts,
        "frames": current["frames"],
        "note": (
            "Items added after the baseline eval set, so unseen by any system measured "
            "against it. Score the BASELINE snapshot's dictionary here, not the current "
            "one: the current dictionary contains these pairs and scores 100% by "
            "construction. Synthetic sentences only, as in the full set."
        ),
        "items": items,
    }

    print(f"held-out vs {origin}: {len(items)} items from {len(pairs)} new pairs")
    if dropped:
        print(f"  ({dropped} baseline items are gone with pairs that left the snapshot)")
    for key in sorted(counts):
        print(f"  {key}: {counts[key]}")
    if args.out:
        args.out.write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
