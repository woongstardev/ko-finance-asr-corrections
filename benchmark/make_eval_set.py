#!/usr/bin/env python3
"""Build the v0 evaluation set from data/pairs.json + benchmark/traps.json.

Pure stdlib. No caption text is read or emitted: every sentence is a template
authored for this benchmark, filled with a pair's surface form.

    python3 benchmark/make_eval_set.py [--out benchmark/eval-set.json]

Item kinds
    error  a template filled with `wrong`; the system is expected to output the
           same sentence with `right` in that slot and nothing else changed.
           One error item per pair carries a spacing-damaged surface instead of
           the clean one (variant "spacing"), because auto-captions routinely
           drop or insert a space inside a phrase - matching that only works if
           the system is whitespace-flexible.
    clean  the same template family filled with `right`; already correct, so any
           edit is an over-correction.
    trap   a hand-authored sentence (benchmark/traps.json) in which some pair's
           `wrong` string occurs as legitimate Korean; any edit is an
           over-correction.

Stability across snapshots
--------------------------
The eval set is **append-only**. Ids come from the pair's `wrong` form rather
than its position, and every item that already exists in the previous eval set
is copied across verbatim; only pairs new to the snapshot generate new items.

Both halves are needed. Positional ids looked stable while only frequencies
drifted and came apart the moment a pair was inserted mid-sort - inserting one
pair reassigned 40 ids to different content and rewrote the carrier sentence of
40 more. Either failure makes "did this snapshot only add items?" unanswerable,
and that question is a release gate (scripts/benchmark_gate.py). Copying forward
also means a committed prediction file stays valid as the snapshot grows, which
is what lets an expensive LLM run outlive one release.

Pass --no-carry-over to rebuild every item from scratch; that is a benchmark
version bump, not a refresh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAIRS = REPO / "data" / "pairs.json"
TRAPS = REPO / "benchmark" / "traps.json"
DEFAULT_OUT = REPO / "benchmark" / "eval-set.json"

# Carrier frames. The slot is always followed by a space, so the sentence stays
# grammatical whether the surface form ends in a vowel or a consonant - Korean
# particle agreement would otherwise leak the answer.
FRAMES = [
    "{w} 관련해서 궁금한 부분이 있습니다.",
    "요즘 {w} 쪽 흐름이 어떻습니까?",
    "오늘 방송에서는 {w} 이야기를 해보겠습니다.",
    "어제 시장에서 {w} 언급이 많았습니다.",
    "{w} 부분은 조금 더 지켜봐야 합니다.",
    "투자자들이 {w} 이슈에 주목하고 있습니다.",
]
ERRORS_PER_PAIR = 3
ID_DIGEST_BYTES = 3  # 6 hex chars; collisions are checked for, not assumed away


def pair_slug(wrong: str) -> str:
    """Stable per-pair id fragment. Depends on the pair, never on the ordering."""
    return hashlib.blake2s(wrong.encode("utf-8"), digest_size=ID_DIGEST_BYTES).hexdigest()


def spacing_variant(wrong: str) -> str | None:
    """Damage the spacing of `wrong` the way an auto-caption would.

    A phrase that already contains a space loses it; a solid one gets a space
    inserted at its midpoint. Returns None when the form is too short to damage
    without destroying it.
    """
    if " " in wrong:
        return wrong.replace(" ", "")
    bare = wrong.strip()
    if len(bare) < 3:
        return None
    mid = len(bare) // 2
    return bare[:mid] + " " + bare[mid:]


def _error_item(item_id: str, frame: str, surface: str, pair: dict, variant: str) -> dict:
    wrong, right = pair["wrong"], pair["right"]
    text = frame.format(w=surface)
    start = text.index(surface)
    return {
        "id": item_id,
        "kind": "error",
        "variant": variant,
        "input": text,
        "expected": text[:start] + right + text[start + len(surface) :],
        "span": [start, start + len(surface)],
        "surface": surface,
        "wrong": wrong,
        "right": right,
        "category": pair.get("category") or "other",
        "tier": pair.get("tier"),
    }


def build(pairs: list[dict], traps: list[dict],
          previous: dict[str, dict] | None = None) -> list[dict]:
    previous = previous or {}
    items: list[dict] = []
    ordered = sorted(pairs, key=lambda p: (p["wrong"], p["right"]))

    slugs: dict[str, str] = {}
    for pair in ordered:
        wrong, right = pair["wrong"], pair["right"]
        category = pair.get("category") or "other"
        slug = pair_slug(wrong)
        if slugs.setdefault(slug, wrong) != wrong:
            raise SystemExit(
                f"id collision: {wrong!r} and {slugs[slug]!r} both hash to {slug}; "
                "raise ID_DIGEST_BYTES"
            )

        # The frame is picked from the pair, not from its position, for the same
        # reason the id is: a positional pick silently rewrites earlier items'
        # sentences when a pair is inserted ahead of them.
        base = int(slug, 16)

        def carried(item_id: str) -> dict | None:
            """The previous item, when it is still about this exact pair.

            Guarded on (wrong, right): if upstream changed the correction, the
            pair is a different pair under the schema's primary key and its
            items have to be regenerated rather than inherited.
            """
            old = previous.get(item_id)
            if old and old.get("wrong") == wrong and old.get("right") == right:
                return old
            return None

        for k in range(ERRORS_PER_PAIR):
            item_id = f"err-{slug}-{k}"
            reuse = carried(item_id)
            frame = FRAMES[(base + k) % len(FRAMES)]
            items.append(reuse or _error_item(item_id, frame, wrong, pair, "plain"))

        damaged = spacing_variant(wrong)
        if damaged:
            item_id = f"err-{slug}-s"
            reuse = carried(item_id)
            frame = FRAMES[(base + ERRORS_PER_PAIR + 1) % len(FRAMES)]
            items.append(reuse or _error_item(item_id, frame, damaged, pair, "spacing"))

        clean_frame = FRAMES[(base + ERRORS_PER_PAIR) % len(FRAMES)]
        clean_text = clean_frame.format(w=right)
        reuse = carried(f"cln-{slug}")
        items.append(
            reuse
            or {
                "id": f"cln-{slug}",
                "kind": "clean",
                "input": clean_text,
                "expected": clean_text,
                "wrong": wrong,
                "right": right,
                "category": category,
                "tier": pair.get("tier"),
            }
        )

    for trap in traps:
        items.append(
            {
                "id": trap["id"],
                "kind": "trap",
                "input": trap["text"],
                "expected": trap["text"],
                "triggers": trap.get("triggers", []),
                "category": "trap",
                "why": trap.get("why", ""),
            }
        )

    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pairs", type=Path, default=PAIRS)
    ap.add_argument("--traps", type=Path, default=TRAPS)
    ap.add_argument("--previous", type=Path, default=DEFAULT_OUT,
                    help="eval set to carry existing items over from")
    ap.add_argument("--no-carry-over", action="store_true",
                    help="rebuild every item from scratch (a benchmark version bump)")
    args = ap.parse_args()

    dataset = json.loads(args.pairs.read_text(encoding="utf-8"))
    traps = json.loads(args.traps.read_text(encoding="utf-8"))["traps"]
    previous: dict[str, dict] = {}
    if not args.no_carry_over and args.previous.exists():
        previous = {
            i["id"]: i
            for i in json.loads(args.previous.read_text(encoding="utf-8"))["items"]
        }
    items = build(dataset["pairs"], traps, previous)

    counts: dict[str, int] = {}
    for item in items:
        key = item["kind"]
        if key == "error":
            key = f"error:{item['variant']}"
        counts[key] = counts.get(key, 0) + 1

    payload = {
        "benchmark": "ko-finance-asr-corrections/mini-v0.2",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pairs_exported_at": dataset.get("exported_at"),
        "pair_count": dataset.get("pair_count"),
        "item_counts": counts,
        "frames": FRAMES,
        "note": (
            "Synthetic sentences only. No YouTube caption text is included; "
            "error/clean items are template fills and traps are hand-authored."
        ),
        "items": items,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{sum(counts.values())} items -> {args.out}")
    for kind, n in sorted(counts.items()):
        print(f"  {kind:6} {n}")


if __name__ == "__main__":
    main()
