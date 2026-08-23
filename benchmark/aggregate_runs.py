#!/usr/bin/env python3
"""Combine N scored runs of one system into a mean-and-spread summary.

    python3 benchmark/aggregate_runs.py --name llm-claude-opus-5-cli \
        benchmark/results/llm-claude-opus-5-cli-run*.json

Written because the reproducibility rules require reporting a spread, and a
rule that has no tool behind it becomes a rule people skip. Deterministic
systems (the dictionary baselines) do not need this - a single run is the
whole distribution. LLM rows do.

Pure stdlib. `spread` is the population standard deviation across runs, and
`min`/`max` are reported too: with N=3 the standard deviation is a weak
estimate, and the range is the honest thing to also show.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

# Metrics worth summarising. Counts and rates both, because a rate hides how
# many items moved when the denominators are this small.
METRICS = ("recall", "over_correction_rate", "precision_proxy", "net_score")
COUNTS = ("fixed", "missed", "mangled", "missing_predictions")


def summarise(values: list[float]) -> dict:
    return {
        "mean": round(statistics.fmean(values), 4),
        "spread": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "runs": len(values),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", nargs="+", type=Path, help="scored result JSONs, one per run")
    ap.add_argument("--name", default=None, help="system label for the summary")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    loaded = [json.loads(p.read_text(encoding="utf-8")) for p in args.results]
    name = args.name or loaded[0].get("system") or "system"

    summary = {
        "system": name,
        "runs": len(loaded),
        "run_files": [str(p) for p in args.results],
        "metrics": {m: summarise([r[m] for r in loaded]) for m in METRICS},
        "counts": {c: summarise([float(r[c]) for c in [c] for r in loaded]) for c in COUNTS},
        "over_corrections": summarise([float(r["over_corrections"]["total"]) for r in loaded]),
    }

    print(f"# {name} ({len(loaded)} runs)\n")
    for metric, s in summary["metrics"].items():
        print(f"  {metric:22} {s['mean']:.4f}  ±{s['spread']:.4f}  "
              f"[{s['min']:.4f}, {s['max']:.4f}]")
    print()
    for count, s in summary["counts"].items():
        print(f"  {count:22} {s['mean']:.1f}  ±{s['spread']:.1f}  [{s['min']:.0f}, {s['max']:.0f}]")
    oc = summary["over_corrections"]
    print(f"  {'over_corrections':22} {oc['mean']:.1f}  ±{oc['spread']:.1f} "
          f"[{oc['min']:.0f}, {oc['max']:.0f}]")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8")
        print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
