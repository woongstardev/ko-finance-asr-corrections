#!/usr/bin/env python3
"""Ask the benchmark whether a candidate snapshot is safe to publish.

    python3 scripts/benchmark_gate.py                       # check data/
    python3 scripts/benchmark_gate.py --pairs /tmp/x/pairs.json --warn-only

Exit 0 = publishable, 1 = a hard finding. `--warn-only` downgrades everything to
a warning, which is what the weekly dry-run uses: a dry-run reports, a --write
stops the line.

Two questions, both of which the benchmark can already answer and neither of
which anything was asking before a release:

1. **Did the evaluation set only grow?** The set is append-only by construction
   (benchmark/make_eval_set.py), so an item that changed or vanished means a
   pair's correction moved under it, or the generator's behaviour drifted. Either
   way every published per-item result silently stops meaning what it said.
   Items belonging to a pair that left the snapshot are expected losses, not
   findings, and trap items are hand-edited so their changes are warnings.

2. **Did the new pairs make the dictionary behave worse?** Re-run the `boundary`
   baseline on the candidate.
   - A `mangled` outcome that did not exist before is a **failure**: it means one
     pair's key now fires inside another pair's replacement and the result is
     neither the error nor the correction. That is the SK하이하이닉스 accident,
     mechanically detected.
   - A drop in net score is only a **warning**. Adding traps legitimately lowers
     it, and so does adding a short risky key that the dataset still wants to
     ship; that is a judgement call for a person, not a gate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "benchmark" / "eval-set.json"
BOUNDARY_RESULT = REPO / "benchmark" / "results" / "baseline-boundary.json"


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"benchmark_gate: {' '.join(cmd[1:3])} failed\n{proc.stderr}")


def check_eval_growth(candidate_pairs: Path, tmp: Path, fail, warn) -> Path:
    run([sys.executable, str(REPO / "benchmark" / "make_eval_set.py"),
         "--pairs", str(candidate_pairs), "--out", str(tmp / "eval-set.json"),
         "--previous", str(EVAL)])

    if not EVAL.exists():
        warn("no committed eval set to compare against — first run?")
        return tmp / "eval-set.json"

    old = {i["id"]: i for i in json.loads(EVAL.read_text(encoding="utf-8"))["items"]}
    new = {i["id"]: i for i in json.loads((tmp / "eval-set.json").read_text(encoding="utf-8"))["items"]}
    shipped = {
        (p["wrong"], p["right"])
        for p in json.loads(candidate_pairs.read_text(encoding="utf-8"))["pairs"]
    }

    for item_id, item in old.items():
        if item_id in new:
            if new[item_id] != item:
                report = warn if item["kind"] == "trap" else fail
                report(f"item {item_id} changed content "
                       f"({item['kind']}; input was {item['input']!r})")
            continue
        if item["kind"] == "trap":
            warn(f"trap item {item_id} disappeared — traps.json edited?")
        elif (item.get("wrong"), item.get("right")) in shipped:
            fail(f"item {item_id} vanished while its pair is still in the snapshot")

    added = len(set(new) - set(old))
    print(f"  eval set: {len(old)} -> {len(new)} items ({added} added)")
    return tmp / "eval-set.json"


def check_baseline(candidate_pairs: Path, eval_path: Path, tmp: Path, fail, warn) -> None:
    pred, result = tmp / "boundary.json", tmp / "boundary-result.json"
    run([sys.executable, str(REPO / "benchmark" / "baselines.py"),
         "--mode", "boundary", "--pairs", str(candidate_pairs),
         "--eval", str(eval_path), "--out", str(pred)])
    run([sys.executable, str(REPO / "benchmark" / "score.py"),
         "--pred", str(pred), "--eval", str(eval_path),
         "--name", "gate-boundary", "--json", str(result)])

    now = json.loads(result.read_text(encoding="utf-8"))
    before = (json.loads(BOUNDARY_RESULT.read_text(encoding="utf-8"))
              if BOUNDARY_RESULT.exists() else {})

    was, is_ = before.get("mangled", 0), now.get("mangled", 0)
    if is_ > was:
        fail(f"boundary baseline now mangles {is_} item(s), was {was} — a new pair's key "
             "fires inside another pair's replacement (cascading substitution)")

    old_net, new_net = before.get("net_score"), now.get("net_score")
    if old_net is not None and new_net is not None and new_net < old_net - 1e-9:
        warn(f"boundary net score {old_net:.3f} -> {new_net:.3f} "
             "(expected when traps or risky short keys are added; check it is intended)")
    print(f"  boundary baseline: net {new_net:.3f}, mangled {is_}, "
          f"over-corrections {now.get('over_corrections', {}).get('total')}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", type=Path, default=REPO / "data" / "pairs.json")
    ap.add_argument("--warn-only", action="store_true",
                    help="report findings without failing (dry-run mode)")
    args = ap.parse_args()

    failures: list[str] = []
    warnings: list[str] = []
    fail = warnings.append if args.warn_only else failures.append
    warn = warnings.append

    with tempfile.TemporaryDirectory(prefix="bench-gate-") as raw:
        tmp = Path(raw)
        eval_path = check_eval_growth(args.pairs, tmp, fail, warn)
        check_baseline(args.pairs, eval_path, tmp, fail, warn)

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        sys.exit(f"benchmark_gate: {len(failures)} failure(s)")
    print(f"benchmark_gate: OK ({len(warnings)} warning(s))")


if __name__ == "__main__":
    main()
