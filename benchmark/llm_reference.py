#!/usr/bin/env python3
"""Run the benchmark against an LLM and write predictions + a run manifest.

    python3 benchmark/llm_reference.py --transport cli --runs 3   # Claude Code CLI
    export ANTHROPIC_API_KEY=... && python3 benchmark/llm_reference.py --runs 3   # API
    python3 benchmark/score.py --pred benchmark/predictions/llm-claude-opus-5-run1.json \
        --name llm-claude-opus-5 --json benchmark/results/llm-claude-opus-5-run1.json

Standard library only, like the rest of the benchmark - deliberately, even
though an official SDK exists. `benchmark/` and `scripts/` take no third-party
imports (CONTRIBUTING.md), so this script speaks the Messages API over urllib
rather than adding a dependency to a repository whose selling point is that it
has none. The scorer never needs network access; this script is the only thing
here that does, and re-running it is optional because the results it produces
are committed.

Two transports, because access to a model is not the same thing as an API key:

  api  POST /v1/messages with ANTHROPIC_API_KEY. The plain reading of the number.
  cli  Shell out to the Claude Code CLI (`claude -p`), which authenticates with
       whatever credential that CLI already holds. Same model, different harness
       - it is a coding agent invoked with its tools switched off and its
       default system prompt replaced - so a row produced this way is labelled
       with its transport and CLI version. The two are not interchangeable in a
       results table.

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
import shutil
import subprocess
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


def cli_flags(model: str, effort: str, budget: float) -> list[str]:
    """Flags that make the coding agent behave like a one-shot rewriter.

    --tools ""            no tool use; the model must answer in text
    --safe-mode           no CLAUDE.md, skills, hooks, plugins, MCP - otherwise
                          this repository's own instructions would enter the
                          prompt and the run would not reproduce elsewhere
    --system-prompt       replaces the agent's default system prompt with ours
    --max-budget-usd      hard ceiling; the run stops rather than surprising you
    """
    flags = [
        "--print",
        "--model", model,
        "--effort", effort,
        "--tools", "",
        "--safe-mode",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--output-format", "json",
        "--system-prompt", SYSTEM_PROMPT,
    ]
    if budget:
        flags += ["--max-budget-usd", str(budget)]
    return flags


def cli_call(text: str, flags: list[str], timeout: float) -> tuple[str, float]:
    """One `claude -p` invocation. Returns (answer, cost_usd)."""
    proc = subprocess.run(
        ["claude", *flags, text],
        capture_output=True, text=True, timeout=timeout, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"claude CLI exited {proc.returncode}: {proc.stderr[:400]}")
    payload = json.loads(proc.stdout)
    cost = float(payload.get("total_cost_usd") or 0.0)
    if payload.get("is_error"):
        return "", cost
    return (payload.get("result") or "").strip(), cost


def cli_version() -> str:
    if not shutil.which("claude"):
        raise SystemExit("--transport cli needs the `claude` CLI on PATH.")
    out = subprocess.run(["claude", "--version"], capture_output=True, text=True, check=False)
    return out.stdout.strip() or "unknown"


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
    ap.add_argument("--transport", choices=("api", "cli"), default="api",
                    help="api = ANTHROPIC_API_KEY; cli = the Claude Code CLI's own credential")
    ap.add_argument("--model", default="claude-opus-5", help="exact model id, never an alias")
    ap.add_argument("--effort", default="medium",
                    choices=("low", "medium", "high", "xhigh", "max"))
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--runs", type=int, default=3, help="a single run is not a measurement")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--limit", type=int, default=0, help="first N items only, for a smoke test")
    ap.add_argument("--max-budget-usd", type=float, default=0.0,
                    help="cli transport only: hard per-call spend ceiling")
    ap.add_argument("--eval", type=Path, default=DEFAULT_EVAL, dest="eval_path")
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if args.transport == "api" and not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Either export one, or use --transport cli "
                 "to go through the credential the Claude Code CLI already holds.")
    harness = cli_version() if args.transport == "cli" else None
    flags = cli_flags(args.model, args.effort, args.max_budget_usd)
    spent = [0.0]

    dataset = json.loads(args.eval_path.read_text(encoding="utf-8"))
    items = dataset["items"][: args.limit] if args.limit else dataset["items"]
    args.outdir.mkdir(parents=True, exist_ok=True)

    def ask(item: dict) -> tuple[str, str]:
        if args.transport == "cli":
            answer, cost = cli_call(item["input"], flags, args.timeout)
            spent[0] += cost
            return item["id"], answer
        payload = {
            "model": args.model,
            "max_tokens": args.max_tokens,
            "system": SYSTEM_PROMPT,
            "output_config": {"effort": args.effort},
            "messages": [{"role": "user", "content": item["input"]}],
        }
        return item["id"], answer_of(request(payload, api_key, args.timeout))

    slug = args.model.replace("/", "-") + ("-cli" if args.transport == "cli" else "")
    written = []
    for run in range(1, args.runs + 1):
        started = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            preds = dict(pool.map(ask, items))
        out = args.outdir / f"llm-{slug}-run{run}.json"
        out.write_text(json.dumps(preds, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        empty = sum(1 for v in preds.values() if not v)
        written.append(out.name)
        cost = f", ${spent[0]:.2f} spent" if args.transport == "cli" else ""
        print(f"run {run}/{args.runs}: {len(preds)} items, {empty} empty, "
              f"{time.time() - started:.0f}s{cost} -> {out}")

    manifest = {
        "model": args.model,
        "transport": args.transport,
        "harness": harness,
        "cli_flags": flags if args.transport == "cli" else None,
        "measured_cost_usd": round(spent[0], 4) if args.transport == "cli" else None,
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
    # The manifest belongs with the committed results, not with predictions/,
    # which is gitignored - a result whose provenance was not committed is not
    # reproducible by anyone else.
    man_path = REPO / "benchmark" / "results" / f"llm-{slug}-manifest.json"
    man_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"manifest -> {man_path}")


if __name__ == "__main__":
    main()
