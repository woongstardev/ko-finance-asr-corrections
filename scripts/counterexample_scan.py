#!/usr/bin/env python3
"""Look for sentences a shipped key would damage, in the corpus it came from.

    OSS_CORPUS_DIR=/path/to/processed python3 scripts/counterexample_scan.py \
        --out ~/.local/state/oss-refresh/reviews/2026-09.md

    # sweep a candidate export before it is published, not after
    OSS_CORPUS_DIR=... python3 scripts/counterexample_scan.py --pairs candidate.json \\
        --out ~/.local/state/oss-refresh/reviews/2026-09-candidate.md

    # once a shape is suspected, count it across the whole corpus
    python3 scripts/counterexample_scan.py --count '아이비=아이비\\s*(들|트)'

Why this exists
---------------
Verification upstream asks "is this correction right?" — this asks the other
question: "where else does this key fire?" They are not the same, and the second
one is only answerable against the corpus. Four pairs were withdrawn or narrowed
on 2026-08-27 because of counterexamples found this way, and the sweep was done
by hand; a check done by hand once is a check that will not happen again.

Two stages, because judgement cannot be automated but counting can. The default
run samples contexts around every match of the riskiest keys so a person can see
what the key actually lands on. `--count` then measures a suspected shape across
every video, which is what a withdrawal recommendation needs — 12 of 19 reads
very differently from 12 of 1,010.

**Output is caption text, so it never goes in the repository.** The script
refuses to write inside this checkout; reviews belong in the state directory
next to the refresh reports, which are private for the same reason.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTEXT_CHARS = 30
SAMPLES_PER_KEY = 12


def ws_flexible(term: str) -> re.Pattern:
    """Whitespace-tolerant match, the same shape the production replacer uses:
    auto-captions lose spaces constantly, so a key must match across them."""
    return re.compile(r"\s*".join(re.escape(ch) for ch in term.replace(" ", "")))


def transcripts(root: Path):
    for entry in sorted(root.iterdir()):
        path = entry / "transcript_labeled.json"
        if path.is_dir() or not path.exists():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in items:
            text = item.get("text") if isinstance(item, dict) else None
            if text:
                yield text


def load_keys(max_len: int, path: Path) -> list[tuple[str, str]]:
    pairs = json.loads(path.read_text(encoding="utf-8"))["pairs"]
    return [(p["wrong"], p["right"]) for p in pairs
            if len(p["wrong"].replace(" ", "")) <= max_len]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", default=os.environ.get("OSS_CORPUS_DIR"))
    ap.add_argument("--out", type=Path, help="write the review sheet here (outside the repo)")
    ap.add_argument("--pairs", type=Path, default=REPO / "data" / "pairs.json",
                    help="pair file to scan; point it at a candidate export to sweep "
                         "before publishing rather than after")
    ap.add_argument("--max-key-length", type=int, default=4,
                    help="only scan keys this short; longer keys rarely land on ordinary text")
    ap.add_argument("--count", action="append", default=[], metavar="KEY=REGEX",
                    help="count how often a suspected harmful shape occurs, corpus-wide")
    args = ap.parse_args()
    if not args.corpus:
        sys.exit("set OSS_CORPUS_DIR or pass --corpus")
    root = Path(args.corpus).expanduser()
    if not root.is_dir():
        sys.exit(f"corpus directory not found: {root}")
    if args.out:
        out = args.out.expanduser().resolve()
        if REPO in out.parents or out == REPO:
            sys.exit(f"refusing to write caption text inside the repository: {out}")

    if args.count:
        shapes = {}
        for spec in args.count:
            key, _, pattern = spec.partition("=")
            shapes[key] = (ws_flexible(key), re.compile(pattern))
        totals = {k: 0 for k in shapes}
        harmful = {k: 0 for k in shapes}
        for text in transcripts(root):
            for key, (base, shape) in shapes.items():
                hits = len(base.findall(text))
                if hits:
                    totals[key] += hits
                    harmful[key] += len(shape.findall(text))
        for key in shapes:
            total, bad = totals[key], harmful[key]
            share = f"{bad / total * 100:.1f}%" if total else "n/a"
            print(f"{key}: {bad} harmful of {total} matches ({share})")
        return

    keys = load_keys(args.max_key_length, args.pairs.expanduser())
    samples: dict[str, list[str]] = {w: [] for w, _ in keys}
    counts: dict[str, int] = {w: 0 for w, _ in keys}
    patterns = {w: ws_flexible(w) for w, _ in keys}
    for text in transcripts(root):
        for wrong, pattern in patterns.items():
            for match in pattern.finditer(text):
                counts[wrong] += 1
                if len(samples[wrong]) < SAMPLES_PER_KEY:
                    start, end = match.span()
                    samples[wrong].append(
                        text[max(0, start - CONTEXT_CHARS):end + CONTEXT_CHARS])

    lines = ["# Counterexample review — keys of "
             f"{args.max_key_length} characters or fewer", "",
             "Caption text. Do not commit this file.", ""]
    for wrong, right in sorted(keys, key=lambda kv: -counts[kv[0]]):
        lines.append(f"## {wrong} → {right} ({counts[wrong]} matches)")
        lines += [f"- …{s.strip()}…" for s in samples[wrong]] or ["- (no matches)"]
        lines.append("")
    report = "\n".join(lines)
    if args.out:
        args.out.expanduser().parent.mkdir(parents=True, exist_ok=True)
        args.out.expanduser().write_text(report, encoding="utf-8")
        print(f"{len(keys)} keys, {sum(counts.values())} matches -> {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
