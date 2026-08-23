#!/usr/bin/env python3
"""Run the benchmark against an LLM and write predictions + a run manifest.

    export ANTHROPIC_API_KEY=...
    python3 benchmark/llm_reference.py --runs 3
    python3 benchmark/score.py --pred benchmark/predictions/llm-claude-opus-5-run1.json \
        --name llm-claude-opus-5 --json benchmark/results/llm-claude-opus-5-run1.json

Standard library only, like the rest of the benchmark - deliberately, even
though an official SDK exists. `benchmark/` and `scripts/` take no third-party
imports (CONTRIBUTING.md), so this script speaks the Messages API over urllib
rather than adding a dependency to a repository whose selling point is that it
has none. The scorer never needs network access; this script is the only thing
here that does, and re-running it is optional because the results it produces
are committed.

Reproducibility rules this script enforces (see benchmark/README.md):
  - the exact model id is recorded, never an alias;
  - the prompt and every request parameter are written into the manifest;
  - --runs defaults to 3, because a single LLM run is not a measurement.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_EVAL = REPO / "benchmark" / "eval-set.json"
DEFAULT_OUTDIR = REPO / "benchmark" / "predictions"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# Verbatim in the manifest. Edit this and you have a different system: bump the
# prompt_id so two result files can never be confused for one another.
PROMPT_ID = "fix-only-v1"
SYSTEM_PROMPT = """\
You correct Korean speech-recognition errors in sentences from finance and stock videos.

A sentence may contain a misrecognized stock name, finance term, or number. If it does,
output the sentence with that misrecognition corrected and nothing else changed.

If the sentence is already correct, output it exactly as given. Ordinary Korean words,
place names, product names, and acronyms from other fields are not errors - leave them
alone even when they resemble a finance term.

Output only the sentence. No explanation, no quotes, no formatting."""


def request(payload: dict, api_key: str, timeout: float, attempts: int = 5) -> dict:
    """POST to the Messages API, retrying 429 and 5xx with exponential backoff."""
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(attempts):
        req = urllib.request.Request(
            API_URL,
            data=body,
            headers={
                "content-type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": API_VERSION,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            retryable = e.code == 429 or e.code >= 500
            if not retryable or attempt == attempts - 1:
                detail = e.read().decode("utf-8", "replace")[:400]
                raise SystemExit(f"API error {e.code}: {detail}") from e
            delay = float(e.headers.get("retry-after") or 0) or min(
                2**attempt + random.random(), 60
            )
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
            delay = min(2**attempt + random.random(), 60)
        time.sleep(delay)
    raise SystemExit("unreachable")


def answer_of(response: dict) -> str:
    """The model's sentence, or '' when the turn produced no text.

    A refusal or an empty turn must not be silently scored as 'left unchanged':
    score.py counts a missing prediction separately, so returning '' here keeps
    the failure visible instead of turning it into a free pass on trap items.
    """
    if response.get("stop_reason") == "refusal":
        return ""
    parts = [b.get("text", "") for b in response.get("content", []) if b.get("type") == "text"]
    return "".join(parts).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default="claude-opus-5", help="exact model id, never an alias")
    ap.add_argument("--effort", default="medium",
                    choices=("low", "medium", "high", "xhigh", "max"))
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--runs", type=int, default=3, help="a single run is not a measurement")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--limit", type=int, default=0, help="first N items only, for a smoke test")
    ap.add_argument("--eval", type=Path, default=DEFAULT_EVAL, dest="eval_path")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. This is the only part of the benchmark "
                 "that needs credentials; scoring committed results does not.")

    dataset = json.loads(args.eval_path.read_text(encoding="utf-8"))
    items = dataset["items"][: args.limit] if args.limit else dataset["items"]
    args.outdir.mkdir(parents=True, exist_ok=True)

    def ask(item: dict) -> tuple[str, str]:
        payload = {
            "model": args.model,
            "max_tokens": args.max_tokens,
            "system": SYSTEM_PROMPT,
            "output_config": {"effort": args.effort},
            "messages": [{"role": "user", "content": item["input"]}],
        }
        return item["id"], answer_of(request(payload, api_key, args.timeout))

    slug = args.model.replace("/", "-")
    written = []
    for run in range(1, args.runs + 1):
        started = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            preds = dict(pool.map(ask, items))
        out = args.outdir / f"llm-{slug}-run{run}.json"
        out.write_text(json.dumps(preds, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        empty = sum(1 for v in preds.values() if not v)
        written.append(out.name)
        print(f"run {run}/{args.runs}: {len(preds)} items, {empty} empty, "
              f"{time.time() - started:.0f}s -> {out}")

    manifest = {
        "model": args.model,
        "prompt_id": PROMPT_ID,
        "system_prompt": SYSTEM_PROMPT,
        "request_params": {
            "max_tokens": args.max_tokens,
            "output_config": {"effort": args.effort},
            "anthropic_version": API_VERSION,
        },
        "note": (
            "Current Claude models removed temperature/top_p/top_k, so there is no sampling "
            "knob to pin - run-to-run spread is inherent and is why --runs defaults to 3."
        ),
        "benchmark": dataset.get("benchmark"),
        "eval_items": len(items),
        "runs": args.runs,
        "prediction_files": written,
    }
    man_path = args.outdir / f"llm-{slug}-manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"manifest -> {man_path}")


if __name__ == "__main__":
    main()
