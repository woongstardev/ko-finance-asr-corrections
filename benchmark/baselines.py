#!/usr/bin/env python3
"""Reference baselines: the dataset used as a correction system, three ways.

Pure stdlib. The point of these is not to be good - it is to give the benchmark
a floor and to show what the over-correction penalty actually measures.

    naive     plain substring replacement, every pair, every occurrence.
    boundary  whitespace-flexible matching with a non-alphanumeric boundary on
              ASCII keys. This mirrors how the upstream pipeline matches, since
              auto-captions drop spaces inside a phrase.
    guarded   boundary, minus any key shorter than --min-key characters. Short
              Korean keys are where blind replacement does its damage; Korean is
              agglutinative, so there is no word boundary to lean on.

    python3 benchmark/baselines.py --all
    python3 benchmark/baselines.py --mode naive --out /tmp/naive.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_EVAL = REPO / "benchmark" / "eval-set.json"
DEFAULT_PAIRS = REPO / "data" / "pairs.json"
DEFAULT_OUTDIR = REPO / "benchmark" / "predictions"

MODES = ("naive", "boundary", "guarded")


def ws_flexible(term: str) -> re.Pattern:
    """Match `term` even when spaces have been dropped or inserted inside it.

    Simplified from the upstream matcher: auto-captions lose the spaces at event
    boundaries, so exact matching misses most real occurrences. ASCII-only keys
    get a boundary guard because short latin strings sit inside longer words;
    Korean keys get none, which is exactly the risk `guarded` trades away.
    """
    body = r"\s*".join(re.escape(c) for c in term if not c.isspace())
    bare = term.replace(" ", "")
    if bare.isascii() and bare.isalnum():
        body = r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])"
    return re.compile(body)


def load_rules(pairs_path: Path, mode: str, min_key: int) -> list[tuple[str, str]]:
    pairs = json.loads(pairs_path.read_text(encoding="utf-8"))["pairs"]
    rules = [(p["wrong"], p["right"]) for p in pairs]
    if mode == "guarded":
        rules = [(w, r) for w, r in rules if len(w.replace(" ", "")) >= min_key]
    # Longest key first: otherwise a short key eats the head of a longer one.
    # Length is measured without spaces, because the matcher above ignores them:
    # ordering by raw length ranks `SK 하인` (6) above `SK하인수` (5) and the short
    # key then leaves its tail behind - "SK하이닉스수". The production replacer
    # sorts the same way (upstream correction_dict sorts on the despaced key),
    # so a baseline that ranked differently was measuring a system nobody runs.
    rules.sort(key=lambda wr: (-len(wr[0].replace(" ", "")), wr[0]))
    return rules


def correct(text: str, rules: list[tuple[str, str]], mode: str) -> str:
    for wrong, right in rules:
        if mode == "naive":
            text = text.replace(wrong, right)
        else:
            text = ws_flexible(wrong).sub(right.replace("\\", "\\\\"), text)
    return text


def run(items: list[dict], rules: list[tuple[str, str]], mode: str) -> dict[str, str]:
    return {item["id"]: correct(item["input"], rules, mode) for item in items}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--mode", choices=MODES, default="naive")
    ap.add_argument("--all", action="store_true", help="run every mode")
    ap.add_argument("--eval", type=Path, default=DEFAULT_EVAL, dest="eval_path")
    ap.add_argument("--pairs", type=Path, default=DEFAULT_PAIRS)
    ap.add_argument("--min-key", type=int, default=4, help="guarded mode key floor")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    items = json.loads(args.eval_path.read_text(encoding="utf-8"))["items"]
    modes = MODES if args.all else (args.mode,)

    for mode in modes:
        rules = load_rules(args.pairs, mode, args.min_key)
        preds = run(items, rules, mode)
        out = args.out if (args.out and not args.all) else args.outdir / f"{mode}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(preds, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"{mode:9} {len(rules):3} rules, {len(preds)} predictions -> {out}")


if __name__ == "__main__":
    main()
