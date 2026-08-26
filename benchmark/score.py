#!/usr/bin/env python3
"""Score a correction system on the ko-finance-asr-corrections mini benchmark.

Pure stdlib - no third-party imports, and deliberately no import of the upstream
ggulmuse pipeline. This is a simplified port of that pipeline's `score_round`
(the upstream production scorer): that one grades a candidate-mining
round against auditor consensus, this one grades a system's rewritten sentences
against a known gold slot. The shared idea is the one that matters - a fix count
alone is not a score, because a system can buy fixes with over-corrections.

    python3 benchmark/score.py --pred predictions.json
    python3 benchmark/score.py --pred out.jsonl --json results/mysystem.json
    python3 benchmark/score.py --pred a.json --compare results/baseline-naive.json

Prediction file: either a JSON object {item_id: output_sentence} or JSONL with
one {"id": ..., "output": ...} per line. Items with no prediction are scored as
left unchanged and reported separately as `missing`.

Per-item outcome
    error items  fixed    the gold slot now holds `right`
                 missed   the gold slot still holds `wrong`
                 mangled  the slot holds neither (a confident wrong answer)
                 ...plus an independent `context_damage` flag when anything
                 outside the slot changed.
    clean/trap   any edit at all is an over-correction; the sentence was
                 already correct.

Headline numbers
    recall               fixed / error items
    over_correction_rate over-corrected items / all items
    precision_proxy      fixed / (fixed + mangled + over-corrections) - a proxy,
                         not a true precision: it has no notion of an error the
                         benchmark did not plant.
    net_score            (fixed - over-corrections) / error items. Can go
                         negative. This is the number to quote.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_EVAL = REPO / "benchmark" / "eval-set.json"

CATEGORIES = ("stock", "term", "number", "other", "trap")


def load_predictions(path: Path) -> dict[str, str]:
    text = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        raw = json.loads(text)
        if "predictions" in raw and isinstance(raw["predictions"], dict):
            raw = raw["predictions"]
        return {str(k): str(v) for k, v in raw.items()}
    preds: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        preds[str(row["id"])] = str(row.get("output", ""))
    return preds


def _squash(text: str) -> str:
    return "".join(text.split())


def _slot_state(item: dict, output: str) -> tuple[str, bool]:
    """Return (outcome, context_damaged) for an error item.

    The slot is known by construction (`span`), so the honest check is whether
    the text around it survived untouched. When it did not, fall back to
    substring presence - less precise, but it still separates "fixed the target
    and broke something else" from "broke something else instead".

    Inside the slot, whitespace is ignored: caption spacing is unreliable to
    begin with, so `SK하이닉스` counts as the same answer as `SK 하이닉스`.
    Outside the slot it is not - moving text around is exactly the damage the
    over-correction penalty is there to catch.
    """
    text, right = item["input"], item["right"]
    # `surface` is what actually sits in the slot; it differs from `wrong` on
    # spacing-damaged items.
    surface = item.get("surface", item["wrong"])
    start, end = item["span"]
    before, after = text[:start], text[end:]

    if output == item["expected"]:
        return "fixed", False

    if output.startswith(before) and output.endswith(after) and len(output) >= start + len(after):
        middle = output[start : len(output) - len(after)] if after else output[start:]
        if _squash(middle) == _squash(right):
            return "fixed", False
        if _squash(middle) == _squash(surface):
            return "missed", False
        return "mangled", False

    flat_out = _squash(output)
    if _squash(right) in flat_out and _squash(surface) not in flat_out:
        return "fixed", True
    if _squash(surface) in flat_out:
        return "missed", True
    return "mangled", True


def score(items: list[dict], preds: dict[str, str]) -> dict:
    tally = {
        "fixed": 0,
        "missed": 0,
        "mangled": 0,
        "over_error_context": 0,
        "over_clean": 0,
        "over_trap": 0,
        "missing": 0,
    }
    by_category: dict[str, dict[str, int]] = {}
    by_variant: dict[str, dict[str, int]] = {}
    per_item: list[dict] = []
    n_error = n_guard = 0

    for item in items:
        cat = item.get("category") or "other"
        bucket = by_category.setdefault(
            cat, {"items": 0, "fixed": 0, "missed": 0, "mangled": 0, "over": 0}
        )
        bucket["items"] += 1

        output = preds.get(item["id"])
        if output is None:
            tally["missing"] += 1
            output = item["input"]

        if item["kind"] == "error":
            n_error += 1
            outcome, damaged = _slot_state(item, output)
            tally[outcome] += 1
            bucket[outcome] += 1
            variant = by_variant.setdefault(
                item.get("variant", "plain"), {"items": 0, "fixed": 0}
            )
            variant["items"] += 1
            variant["fixed"] += outcome == "fixed"
            if damaged:
                tally["over_error_context"] += 1
                bucket["over"] += 1
            per_item.append(
                {"id": item["id"], "outcome": outcome, "context_damage": damaged}
            )
        else:
            n_guard += 1
            changed = output != item["input"]
            if changed:
                key = "over_trap" if item["kind"] == "trap" else "over_clean"
                tally[key] += 1
                bucket["over"] += 1
            per_item.append(
                {
                    "id": item["id"],
                    "outcome": "over_corrected" if changed else "left_alone",
                    "context_damage": changed,
                }
            )

    over_total = (
        tally["over_error_context"] + tally["over_clean"] + tally["over_trap"]
    )
    total_items = n_error + n_guard
    denom = tally["fixed"] + tally["mangled"] + over_total

    return {
        "items": {"total": total_items, "error": n_error, "guard": n_guard},
        "fixed": tally["fixed"],
        "missed": tally["missed"],
        "mangled": tally["mangled"],
        "over_corrections": {
            "total": over_total,
            "error_context": tally["over_error_context"],
            "clean": tally["over_clean"],
            "trap": tally["over_trap"],
        },
        "recall": (tally["fixed"] / n_error) if n_error else 0.0,
        "over_correction_rate": (over_total / total_items) if total_items else 0.0,
        "precision_proxy": (tally["fixed"] / denom) if denom else None,
        "net_score": ((tally["fixed"] - over_total) / n_error) if n_error else 0.0,
        "missing_predictions": tally["missing"],
        "by_category": by_category,
        "by_variant": by_variant,
        "per_item": per_item,
    }


def _pct(x: float | None) -> str:
    return "  n/a " if x is None else f"{x * 100:6.1f}%"


def report(result: dict, name: str, previous: dict | None = None) -> str:
    items = result["items"]
    over = result["over_corrections"]
    lines = [
        f"# {name}",
        f"items: {items['total']} ({items['error']} error, {items['guard']} guard)",
        "",
        f"  fixed              {result['fixed']:5}   recall              {_pct(result['recall'])}",
        f"  missed             {result['missed']:5}   over-correction     {_pct(result['over_correction_rate'])}",
        f"  mangled            {result['mangled']:5}   precision (proxy)   {_pct(result['precision_proxy'])}",
        f"  over-corrections   {over['total']:5}   net score           {_pct(result['net_score'])}",
        f"      of which  error-context {over['error_context']}, clean {over['clean']}, trap {over['trap']}",
        "",
        "  category      items  fixed  missed  mangled  over",
    ]
    for cat in CATEGORIES:
        b = result["by_category"].get(cat)
        if not b:
            continue
        lines.append(
            f"  {cat:<12} {b['items']:6} {b['fixed']:6} {b['missed']:7} "
            f"{b['mangled']:8} {b['over']:5}"
        )
    if result.get("by_variant"):
        lines += ["", "  error variant  items  fixed  recall"]
        for name_, b in sorted(result["by_variant"].items()):
            rate = (b["fixed"] / b["items"]) if b["items"] else 0.0
            lines.append(
                f"  {name_:<13} {b['items']:6} {b['fixed']:6} {_pct(rate)}"
            )
    if result["missing_predictions"]:
        lines.append("")
        lines.append(
            f"  ! {result['missing_predictions']} items had no prediction "
            "(scored as left unchanged)"
        )
    if previous:
        lines += ["", "  delta vs previous run"]
        for key in ("fixed", "missed", "mangled"):
            lines.append(f"    {key:<10} {result[key] - previous.get(key, 0):+d}")
        lines.append(
            f"    {'over':<10} "
            f"{over['total'] - previous.get('over_corrections', {}).get('total', 0):+d}"
        )
        lines.append(
            f"    {'net':<10} "
            f"{(result['net_score'] - previous.get('net_score', 0.0)) * 100:+.1f}pp"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Prediction file: {id: output} JSON, or JSONL of {id, output}.",
    )
    ap.add_argument("--pred", type=Path, required=True, help="predictions file, or - for stdin")
    ap.add_argument("--eval", type=Path, default=DEFAULT_EVAL, dest="eval_path")
    ap.add_argument("--name", default=None, help="label for the report header")
    ap.add_argument("--json", type=Path, default=None, help="write the result here")
    ap.add_argument("--compare", type=Path, default=None, help="previous result json")
    ap.add_argument(
        "--full", action="store_true", help="keep the per-item breakdown in --json"
    )
    args = ap.parse_args()

    eval_set = json.loads(args.eval_path.read_text(encoding="utf-8"))
    preds = load_predictions(args.pred)
    result = score(eval_set["items"], preds)
    previous = (
        json.loads(args.compare.read_text(encoding="utf-8")) if args.compare else None
    )

    name = args.name or args.pred.stem
    print(report(result, name, previous))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(result)
        payload["system"] = name
        if not args.full:
            payload.pop("per_item", None)
        args.json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
