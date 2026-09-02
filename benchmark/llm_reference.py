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
import tempfile
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

# One field, because the task has one answer. See grok_argv for why a schema is
# needed at all; SCHEMA_SUFFIX is appended to the system prompt for any CLI
# driven this way, and the manifest's prompt_id records that it was.
GROK_SCHEMA = ('{"type":"object","properties":{"sentence":{"type":"string"}},'
               '"required":["sentence"],"additionalProperties":false}')
SCHEMA_SUFFIX = "\n\nReturn the sentence in the `sentence` field."

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


def claude_argv(prompt: str, model: str, effort: str, budget: float, out: Path) -> list[str]:
    """Flags that make the coding agent behave like a one-shot rewriter.

    --tools ""            no tool use; the model must answer in text
    --safe-mode           no CLAUDE.md, skills, hooks, plugins, MCP - otherwise
                          this repository's own instructions would enter the
                          prompt and the run would not reproduce elsewhere
    --system-prompt       replaces the agent's default system prompt with ours
    --max-budget-usd      hard ceiling; the run stops rather than surprising you
    """
    argv = ["claude", "--print", "--model", model, "--effort", effort,
            "--tools", "", "--safe-mode", "--disable-slash-commands",
            "--no-session-persistence", "--output-format", "json",
            "--system-prompt", SYSTEM_PROMPT]
    if budget:
        argv += ["--max-budget-usd", str(budget)]
    return argv + [prompt]


def claude_parse(proc: subprocess.CompletedProcess, out: Path) -> tuple[str, float, str]:
    payload = json.loads(proc.stdout)
    cost = float(payload.get("total_cost_usd") or 0.0)
    seen = payload.get("model") or ""
    if payload.get("is_error"):
        return "", cost, seen
    return (payload.get("result") or "").strip(), cost, seen


def grok_argv(prompt: str, model: str, effort: str, budget: float, out: Path) -> list[str]:
    # --tools "" is the same idea as Claude's: no tool use, so the model has to
    # answer in text. No --max-turns: the CLI counts the model's own reply as a
    # turn and exits non-zero on the cap, and with tools off there is no loop to
    # cap anyway. --system-prompt-override is the native equivalent of
    # --system-prompt, so this row's prompt reaches the model the same way.
    #
    # --json-schema is not decoration. Without it this CLI narrates before it
    # answers and glues the narration to the sentence ("...원문을 확인합니다.투자자
    # 들이..."), which scores as a mangled item and would understate the model.
    # A one-field schema separates the answer from the agent's voice.
    argv = ["grok", "--permission-mode", "dontAsk", "--tools", "",
            "--json-schema", GROK_SCHEMA,
            "--system-prompt-override", SYSTEM_PROMPT + SCHEMA_SUFFIX]
    if model:
        argv += ["--model", model]
    if effort:
        argv += ["--reasoning-effort", effort]
    return argv + ["-p", prompt]


def grok_parse(proc: subprocess.CompletedProcess, out: Path) -> tuple[str, float, str]:
    payload = json.loads(proc.stdout)
    cost = float(payload.get("total_cost_usd") or 0.0)
    seen = ", ".join((payload.get("modelUsage") or {}).keys())
    text = (payload.get("text") or "").strip()
    try:
        return json.loads(text).get("sentence", "").strip(), cost, seen
    except ValueError:
        # The schema is a request, not a guarantee; a plain answer still counts.
        return text, cost, seen


def codex_argv(prompt: str, model: str, effort: str, budget: float, out: Path) -> list[str]:
    # Codex has no system-prompt flag, so the instructions travel as a preamble
    # (see the CLIS table). --ephemeral, --ignore-rules, a read-only sandbox and a
    # repo-free cwd mean a model that decides to use a tool cannot touch anything.
    #
    # The operator's config is deliberately NOT ignored: a model id like
    # `gpt-5.6-sol` is resolved through the provider table in that config, so
    # --ignore-user-config makes the run fail rather than isolating it. Pinning
    # the model matters more than isolating the config - an unpinned row breaks
    # the first reproducibility rule in benchmark/README.md - so the trade is
    # taken and recorded: a codex row depends on the operator's provider table,
    # and the reasoning effort is pinned here rather than inherited silently.
    argv = ["codex", "exec", "--skip-git-repo-check", "--ephemeral",
            "--ignore-rules", "--sandbox", "read-only",
            "--color", "never", "--output-last-message", str(out)]
    if model:
        argv += ["--model", model, "-c", f"model_reasoning_effort={effort or 'high'}"]
    return argv + [f"{SYSTEM_PROMPT}\n\n{prompt}"]


def codex_parse(proc: subprocess.CompletedProcess, out: Path) -> tuple[str, float, str]:
    # The agent's chatter goes to stdout; the answer is the last message, which
    # the CLI writes to the file we named. Parsing stdout instead would score
    # the transcript rather than the correction.
    text = out.read_text(encoding="utf-8").strip() if out.exists() else ""
    return text, 0.0, ""


def qwen_argv(prompt: str, model: str, effort: str, budget: float, out: Path) -> list[str]:
    argv = ["qwen", "--safe-mode", "--output-format", "json"]
    if model:
        argv += ["--model", model]
    return argv + ["-p", f"{SYSTEM_PROMPT}\n\n{prompt}"]


def qwen_parse(proc: subprocess.CompletedProcess, out: Path) -> tuple[str, float, str]:
    # This CLI prints the whole session as a JSON array of events; the answer is
    # the terminal `result` event. The assistant events before it include the
    # model's thinking, which is not the answer.
    events = json.loads(proc.stdout)
    answer, seen = "", ""
    for event in events if isinstance(events, list) else [events]:
        if not isinstance(event, dict):
            continue
        model = ((event.get("message") or {}).get("model")
                 if isinstance(event.get("message"), dict) else None)
        seen = model or seen
        if event.get("type") == "result" and not event.get("is_error"):
            answer = str(event.get("result") or "").strip()
    return answer, 0.0, seen


# Every CLI this benchmark can drive. They are not interchangeable rows: each is
# a different harness around a different model, and two of them cannot be given
# a system prompt natively, so the instructions arrive as a preamble instead.
# The manifest records which, because "same prompt" is otherwise a claim nobody
# can check. Cost is reported by Claude Code only; the others authenticate with
# a subscription and tell us nothing about spend, which the manifest also says.
CLIS = {
    "claude": {"binary": "claude", "version": ["claude", "--version"],
               "system": "flag", "reports_cost": True,
               "default_model": "claude-opus-5",
               "argv": claude_argv, "parse": claude_parse},
    "grok": {"binary": "grok", "version": ["grok", "--version"],
             "system": "flag", "reports_cost": True, "default_model": "",
             "argv": grok_argv, "parse": grok_parse},
    "codex": {"binary": "codex", "version": ["codex", "--version"],
              "system": "preamble", "reports_cost": False, "default_model": "",
              "argv": codex_argv, "parse": codex_parse},
    "qwen": {"binary": "qwen", "version": ["qwen", "--version"],
             "system": "preamble", "reports_cost": False, "default_model": "",
             "argv": qwen_argv, "parse": qwen_parse},
}


def cli_call(text: str, spec: dict, model: str, effort: str, budget: float,
             timeout: float) -> tuple[str, float, str]:
    """One headless invocation of the chosen CLI. Returns (answer, cost_usd)."""
    with tempfile.TemporaryDirectory(prefix="llm-ref-") as tmp:
        out = Path(tmp) / "last-message.txt"
        argv = spec["argv"](text, model, effort, budget, out)
        proc = subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False, cwd=tmp)
        if proc.returncode != 0:
            raise SystemExit(
                f"{spec['binary']} exited {proc.returncode}: {proc.stderr[:400]}")
        try:
            return spec["parse"](proc, out)
        except (ValueError, KeyError) as e:
            raise SystemExit(
                f"{spec['binary']} output could not be read ({e}); "
                f"first 200 chars: {proc.stdout[:200]!r}") from e


def cli_version(spec: dict) -> str:
    if not shutil.which(spec["binary"]):
        raise SystemExit(
            f"--cli {spec['binary']} needs the `{spec['binary']}` CLI on PATH.")
    out = subprocess.run(spec["version"], capture_output=True, text=True, check=False)
    return (out.stdout.strip() or "unknown").splitlines()[0]


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
                    help="api = ANTHROPIC_API_KEY; cli = a coding CLI's own credential")
    ap.add_argument("--cli", choices=tuple(CLIS), default="claude",
                    help="which CLI the cli transport drives (default: claude)")
    ap.add_argument("--model", default="", help="exact model id, never an alias; "
                    "empty means the CLI's own default, and the manifest says so")
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
    ap.add_argument("--label", default="", help="suffix for the result slug, e.g. heldout")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if args.transport == "api" and not api_key:
        sys.exit("ANTHROPIC_API_KEY is not set. Either export one, or use --transport cli "
                 "to go through the credential the Claude Code CLI already holds.")
    spec = CLIS[args.cli]
    if args.transport == "api" and args.cli != "claude":
        sys.exit("--cli only applies to --transport cli; the api transport is the "
                 "Anthropic Messages API and reaches no other vendor.")
    model = args.model or (spec["default_model"] if args.transport == "cli"
                           else "claude-opus-5")
    if args.transport == "api" and not model:
        sys.exit("--transport api needs an explicit --model")
    harness = cli_version(spec) if args.transport == "cli" else None
    spent = [0.0]
    reported: set[str] = set()

    dataset = json.loads(args.eval_path.read_text(encoding="utf-8"))
    items = dataset["items"][: args.limit] if args.limit else dataset["items"]
    args.outdir.mkdir(parents=True, exist_ok=True)

    def ask(item: dict) -> tuple[str, str]:
        if args.transport == "cli":
            answer, cost, model_seen = cli_call(item["input"], spec, model, args.effort,
                                                args.max_budget_usd, args.timeout)
            spent[0] += cost
            if model_seen:
                # What the CLI says it used. When --model is left empty this is
                # the only record of which model produced the row, and it is not
                # always what the CLI's name suggests.
                reported.add(model_seen)
            return item["id"], answer
        payload = {
            "model": model,
            "max_tokens": args.max_tokens,
            "system": SYSTEM_PROMPT,
            "output_config": {"effort": args.effort},
            "messages": [{"role": "user", "content": item["input"]}],
        }
        return item["id"], answer_of(request(payload, api_key, args.timeout))

    # A label keeps one model's rows apart when the same model is run against
    # different eval sets — the monthly held-out slice is the reason this exists:
    # without it a delta run overwrites the full-set run's predictions and, worse,
    # its manifest, which is the only record of how that row was produced.
    # A cli row is named for its harness as well as its model, because they are
    # not the same measurement: "-cli" stayed as the Claude Code suffix so the
    # rows published before other CLIs existed keep their filenames.
    suffix = {"api": "", "cli": "-cli" if args.cli == "claude" else f"-{args.cli}"}
    slug = (model or args.cli).replace("/", "-") + suffix[args.transport]
    if args.label:
        slug += f"-{args.label}"
    written = []
    for run in range(1, args.runs + 1):
        started = time.time()
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            preds = dict(pool.map(ask, items))
        out = args.outdir / f"llm-{slug}-run{run}.json"
        out.write_text(json.dumps(preds, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        empty = sum(1 for v in preds.values() if not v)
        written.append(out.name)
        cost = (f", ${spent[0]:.2f} spent"
                if args.transport == "cli" and spec["reports_cost"] else "")
        print(f"run {run}/{args.runs}: {len(preds)} items, {empty} empty, "
              f"{time.time() - started:.0f}s{cost} -> {out}")

    manifest = {
        "model": model or f"{args.cli} default",
        "model_reported": sorted(reported) or None,
        "transport": args.transport,
        "cli": args.cli if args.transport == "cli" else None,
        "harness": harness,
        # The exact argv of one call, prompt excluded - the whole point of a
        # manifest is that someone else can reproduce the invocation.
        "cli_argv": (spec["argv"]("<ITEM>", model, args.effort,
                                  args.max_budget_usd, Path("<TMP>"))
                     if args.transport == "cli" else None),
        # Two of the CLIs have no system-prompt flag, so the instructions travel
        # as a preamble on the user turn. Same text, different delivery, and a
        # row that does not say which is not comparable to one that does.
        "system_delivery": spec["system"] if args.transport == "cli" else "api-system-field",
        "measured_cost_usd": (round(spent[0], 4)
                              if args.transport == "cli" and spec["reports_cost"]
                              else None),
        "cost_note": (None if args.transport == "api" or spec["reports_cost"]
                      else f"the {args.cli} CLI does not report per-call cost; "
                           "this row was produced on an existing subscription"),
        "prompt_id": PROMPT_ID + ("+json-schema" if args.transport == "cli" and args.cli == "grok" else ""),
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
