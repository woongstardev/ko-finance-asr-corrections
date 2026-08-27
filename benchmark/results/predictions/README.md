# Committed LLM predictions

Model outputs, one file per run, so an LLM row in the benchmark tables can be **rescored
without re-running the model**. Everything here is synthetic: the inputs are template-filled
sentences from `eval-set.json`, so no caption text, no transcript, and nothing identifying a
video or a person passes through.

The dictionary baselines' predictions are *not* here — those regenerate in under a second
(`python3 benchmark/baselines.py --all`), so committing them would be storing what a command
can rebuild. An LLM run cannot be rebuilt: it costs an API call per item, the models drift,
and the current Claude models expose no temperature to pin, which is exactly why the row is
reported as a mean over three runs.

| Files | Eval set | Cost when produced |
|---|---|---|
| `llm-claude-opus-5-cli-run{1,2,3}.json` | `mini-v0.2`, 482 items | $9.35, 2026-08-23 |
| `llm-claude-opus-5-cli-heldout-run{1,2,3}.json` | held-out slice, 220 items | $3.56, 2026-08-27 |

To rescore, pair a prediction file with the eval set it was produced against. The held-out
slice is the items in `eval-set.json` at `mini-v0.3` that are absent from it at `mini-v0.2`,
and the `mini-v0.2` file is `git show 87aed71:benchmark/eval-set.json`:

```bash
python3 benchmark/score.py \
    --pred benchmark/results/predictions/llm-claude-opus-5-cli-run1.json \
    --eval <(git show 87aed71:benchmark/eval-set.json) \
    --name replay
```

Verified 2026-08-28: replaying run 1 reproduces the committed result exactly — recall 0.6402,
net 0.6119, 114 mangled.
