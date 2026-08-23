#!/usr/bin/env python3
"""Rank shipped pairs by over-correction risk, so trap authoring follows the data.

    python3 benchmark/mine_traps.py              # human-readable report
    python3 benchmark/mine_traps.py --json       # machine-readable

Pure stdlib, no network, no caption text. This script does *not* write traps:
it mines candidates and the risk reason, and a person writes the sentence
(benchmark/traps.json). Automating the sentence would put unreviewed Korean
into the benchmark, and a trap that reads wrong is worse than no trap.

Why a ranking and not a generator
---------------------------------
The productive question is "which shipped key can fire inside ordinary Korean?"
Answering it mechanically would need a Korean lexicon, which this benchmark
deliberately does not carry (stdlib only, no corpus, no caption text). What a
machine *can* do is narrow 89 pairs down to the ones where that is plausible,
and say why. Four risk classes, in descending order of how reliably they bite:

  cross-pair   Another pair's key sits inside this pair's key or corrected form.
               Exact, no judgement needed: replacement order decides whether the
               result is right, missed, or mangled.
  spanning     Whitespace-flexible matching joins across a space, so a key can
               match text that has a word boundary in the middle of it
               ("미국 체류" -> 미국체). Every split point is listed as a shape
               for a human to accept or reject.
  ascii        A pure-ASCII key collides with real tickers and acronyms, which
               is exactly where a finance corpus is dense.
  short        Keys under 4 characters. Korean is agglutinative, so a short key
               has no boundary to hide behind — this is the class the `guarded`
               baseline drops wholesale.

A pair can be in several classes; the report lists each class separately and
the coverage summary counts a key as covered if any trap triggers on it.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAIRS = REPO / "data" / "pairs.json"
TRAPS = REPO / "benchmark" / "traps.json"

SHORT_KEY_MAX = 3  # `guarded` baseline drops keys shorter than 4 characters.


def cross_pair(pairs: list[dict]) -> list[dict]:
    """Containments between pairs. Exact — these need no human judgement.

    right_embedded  A.wrong inside B.right: correct text that A damages.
    chain           A.wrong inside B.wrong: A fires inside B's error first and
                    the result is neither wrong nor right (a `mangled` outcome).
    retrigger       B.wrong inside A.right: B fires on A's own output, so a
                    correct replacement is immediately damaged.
    """
    found = []
    for a in pairs:
        for b in pairs:
            if a is b:
                continue
            if a["wrong"] != b["right"] and a["wrong"] in b["right"]:
                found.append({"kind": "right_embedded", "key": a["wrong"],
                              "inside": b["right"], "other": b["wrong"]})
            if a["wrong"] != b["wrong"] and a["wrong"] in b["wrong"]:
                found.append({"kind": "chain", "key": a["wrong"],
                              "inside": b["wrong"], "other": b["right"]})
            if b["wrong"] != a["right"] and b["wrong"] in a["right"]:
                found.append({"kind": "retrigger", "key": b["wrong"],
                              "inside": a["right"], "other": a["wrong"]})
    seen, unique = set(), []
    for f in found:
        sig = (f["kind"], f["key"], f["inside"])
        if sig not in seen:
            seen.add(sig)
            unique.append(f)
    return sorted(unique, key=lambda f: (f["kind"], f["key"]))


def spanning_shapes(key: str) -> list[str]:
    """Every way a word boundary could fall inside `key`.

    The upstream matcher is whitespace-flexible, so text with a space at any of
    these points still matches. Splits that leave a one-character fragment on
    either side are kept: Korean has plenty of one-syllable words (형, 고, 률),
    and those are precisely the accidents that bite.
    """
    if " " in key:
        return [key]
    return [f"{key[:i]} {key[i:]}" for i in range(1, len(key))]


def build_report(pairs: list[dict], traps: list[dict]) -> dict:
    covered = {t for trap in traps for t in trap.get("triggers", [])}
    by_key = {p["wrong"]: p for p in pairs}

    classes: dict[str, list[dict]] = {"cross_pair": [], "spanning": [], "ascii": [], "short": []}

    for f in cross_pair(pairs):
        pair = by_key.get(f["key"], {})
        classes["cross_pair"].append({**f, "covered": f["key"] in covered,
                                      "corpus_count": pair.get("corpus_count")})

    for p in sorted(pairs, key=lambda p: (len(p["wrong"]), p["wrong"])):
        key = p["wrong"]
        entry = {"key": key, "right": p["right"], "category": p.get("category"),
                 "corpus_count": p.get("corpus_count"), "covered": key in covered}
        if len(key) >= 2:
            classes["spanning"].append({**entry, "shapes": spanning_shapes(key)})
        if key.isascii():
            classes["ascii"].append(entry)
        if len(key) <= SHORT_KEY_MAX:
            classes["short"].append(entry)

    risky = {e["key"] for c in classes.values() for e in c}
    return {
        "pair_count": len(pairs),
        "trap_count": len(traps),
        "covered_keys": sorted(covered),
        "uncovered_risky_keys": sorted(risky - covered),
        "classes": classes,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pairs", type=Path, default=PAIRS)
    ap.add_argument("--traps", type=Path, default=TRAPS)
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args()

    pairs = json.loads(args.pairs.read_text(encoding="utf-8"))["pairs"]
    traps = json.loads(args.traps.read_text(encoding="utf-8"))["traps"]
    report = build_report(pairs, traps)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return

    print(f"{report['pair_count']} pairs, {report['trap_count']} traps\n")

    cross = report["classes"]["cross_pair"]
    print(f"== cross-pair containment: {len(cross)} ==")
    if not cross:
        print("  (none — see benchmark/README.md; this class is empty at this snapshot size)")
    for f in cross:
        flag = "covered" if f["covered"] else "UNCOVERED"
        print(f"  [{f['kind']:<14}] {f['key']} inside {f['inside']}  ({flag})")

    for name in ("ascii", "short"):
        rows = report["classes"][name]
        print(f"\n== {name} keys: {len(rows)} ==")
        for e in rows:
            flag = "covered" if e["covered"] else "UNCOVERED"
            print(f"  {e['key']:<10} -> {e['right']:<14} x{e['corpus_count']:<4} {flag}")

    span = [e for e in report["classes"]["spanning"] if not e["covered"]]
    print(f"\n== spanning shapes, uncovered only: {len(span)} ==")
    for e in span:
        print(f"  {e['key']:<12} -> {e['right']:<14} " + " | ".join(e["shapes"]))

    print(f"\nuncovered risky keys: {len(report['uncovered_risky_keys'])}")


if __name__ == "__main__":
    main()
