#!/usr/bin/env python3
"""Derive a contextual-biasing vocabulary from the snapshot.

    python3 scripts/make_biasing_list.py            # rewrites data/biasing-list.txt

The pairs say which finance terms this ASR system gets wrong and how often. The
same information, reduced to the verified forms alone, is directly consumable by
a recognizer: Whisper takes it as `initial_prompt`, trie-based context biasing
takes it as a phrase list, and a rescorer takes it as a lexicon boost. That is a
different audience from the dictionary consumers this repository started with,
and it costs one derived file.

Derived, never authored: regenerate it rather than editing it, the same rule
`data/` follows. Terms are ordered by how often the misrecognition was observed,
so a consumer that can only afford the first N takes the N that matter most.
Note the ordering caveat for prompt-style use: Whisper reads only the tail of a
long prompt, so a consumer truncating to fit should keep the *head* of this file
and reverse it, not slice the end.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAIRS = REPO / "data" / "pairs.json"
OUT = REPO / "data" / "biasing-list.txt"


def main() -> None:
    payload = json.loads(PAIRS.read_text(encoding="utf-8"))
    weight: dict[str, int] = {}
    for pair in payload["pairs"]:
        term = pair["right"]
        weight[term] = weight.get(term, 0) + (pair.get("corpus_count") or 0)
    terms = sorted(weight.items(), key=lambda kv: (-kv[1], kv[0]))
    corpus = payload.get("corpus") or {}
    header = [
        "# Verified finance terms this ASR system misrecognises, most-damaged first.",
        f"# Derived from ko-finance-asr-corrections {payload.get('exported_at')} "
        f"({payload.get('pair_count')} pairs, {corpus.get('scanned_videos')} videos).",
        "# One term per line; the trailing number is how often its misrecognitions were",
        "# observed in the corpus, not how often the term itself appeared.",
    ]
    body = [f"{term}\t{count}" for term, count in terms]
    OUT.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    print(f"{len(terms)} terms -> {OUT}")


if __name__ == "__main__":
    main()
