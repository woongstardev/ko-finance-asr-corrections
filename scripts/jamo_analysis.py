#!/usr/bin/env python3
"""What kind of damage does this ASR do, at the jamo level?

    python3 scripts/jamo_analysis.py

Decomposes each pair into Hangul jamo and reports the edit distance and the
dominant operations. Pure stdlib: Hangul syllables are arithmetic, so this needs
no G2P library — which matters, because the Korean G2P packages of the last
several years have a habit of dying with a dependency.

**This is jamo, not pronunciation.** No phonological rules are applied
(assimilation, tensification, liaison), so `국물` decomposes as ㄱㅜㄱㅁㅜㄹ and
not as its spoken [궁물]. A real phonetic index would need those rules and the
result would be a different, larger artifact; this is the honest cheap version.

Output is an analysis rather than a data field. `jamo_distance` would be a pure
function of the primary key, and the same argument that keeps the error rate out
of the schema keeps this out: a stored value that any consumer can recompute is
a value that can disagree with the two columns that determine it.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE, LAST = 0xAC00, 0xD7A3
LEAD = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
VOWEL = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
TAIL = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"


def jamo(text: str) -> list[str]:
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if BASE <= code <= LAST:
            offset = code - BASE
            out.append(LEAD[offset // 588])
            out.append(VOWEL[(offset % 588) // 28])
            tail = TAIL[offset % 28]
            if tail != " ":
                out.append(tail)
        elif not ch.isspace():
            out.append(ch)
    return out


def edits(a: list[str], b: list[str]) -> tuple[int, list[str]]:
    """Levenshtein with a backtrace, reported as coarse operation labels."""
    n, m = len(a), len(b)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        table[i][0] = i
    for j in range(m + 1):
        table[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            table[i][j] = min(table[i - 1][j] + 1, table[i][j - 1] + 1,
                              table[i - 1][j - 1] + cost)
    ops: list[str] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and table[i][j] == table[i - 1][j - 1]:
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and table[i][j] == table[i - 1][j - 1] + 1:
            ops.append(f"sub {a[i - 1]}->{b[j - 1]}")
            i, j = i - 1, j - 1
        elif j > 0 and table[i][j] == table[i][j - 1] + 1:
            ops.append(f"ins {b[j - 1]}")
            j -= 1
        else:
            ops.append(f"del {a[i - 1]}")
            i -= 1
    return table[n][m], ops[::-1]


def main() -> None:
    pairs = json.loads((REPO / "data" / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    distances: Counter[int] = Counter()
    kinds: Counter[str] = Counter()
    single: Counter[str] = Counter()
    for pair in pairs:
        distance, ops = edits(jamo(pair["wrong"]), jamo(pair["right"]))
        distances[distance] += 1
        for op in ops:
            kinds[op.split()[0]] += 1
        if distance == 1 and ops:
            single[ops[0]] += 1

    total = len(pairs)
    print(f"{total} pairs\n")
    print("jamo edit distance:")
    for distance, count in sorted(distances.items()):
        print(f"  {distance:2}: {count:3} pairs  {count / total * 100:4.1f}%")
    print("\noperation mix:")
    for kind, count in kinds.most_common():
        print(f"  {kind:4}: {count}")
    print("\nmost common single-jamo damage:")
    for op, count in single.most_common(8):
        print(f"  {op:14} x{count}")


if __name__ == "__main__":
    main()
