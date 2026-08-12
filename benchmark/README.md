# Mini benchmark v0

**Task: given a Korean finance sentence containing an ASR misrecognition, fix it — without
touching anything else.**

The second half is the hard half. A system that rewrites aggressively scores well on fixes
and destroys text elsewhere; upstream measurement found that prompt-level instructions to
"be careful" moved error types around without reducing the total. So this benchmark scores
fixes and damage together, and the headline number subtracts one from the other.

Everything here is pure stdlib Python 3.10+. No installation, no network, no dependency on
the upstream pipeline.

```bash
python3 benchmark/make_eval_set.py        # data/pairs.json + traps.json -> eval-set.json
python3 benchmark/baselines.py --all      # reference systems -> predictions/
python3 benchmark/score.py --pred benchmark/predictions/boundary.json
cd benchmark && python3 -m unittest discover    # scorer self-test (10 cases)
```

## The evaluation set (456 items)

No caption text appears anywhere in this benchmark. Source transcripts are not
redistributable and the dataset's hard line excludes them, so every sentence is either a
template fill or hand-authored for this repo.

| Kind | Items | What it is | Correct behaviour |
|---|---|---|---|
| `error` / plain | 267 | Six carrier templates filled with a pair's `wrong` form, 3 per pair | Replace the slot with `right` |
| `error` / spacing | 86 | The same, with the spacing of `wrong` damaged — a space inserted mid-word, or a phrase's space removed | Replace the slot with `right` |
| `clean` | 89 | A template filled with `right` — already correct | Change nothing |
| `trap` | 14 | Hand-authored sentences where a pair's `wrong` string is legitimate Korean (`엔트로피` the physics term, `바위` the rock, `MCD` the McDonald's ticker, `미국 체류`, `AM대역`, a person named `나상은`) | Change nothing |

The spacing variants are not synthetic difficulty for its own sake: YouTube auto-captions
drop the space at event boundaries essentially always, which is why the upstream matcher is
whitespace-flexible. A system that only does exact string matching will miss these, and the
baseline table below shows exactly how much that costs.

Item ids are derived from the pair list sorted by `wrong`, so they stay stable as the
monthly snapshot grows.

## Scoring

Each `error` item has a known gold slot, so two independent things get measured: whether the
slot was fixed, and whether anything outside it moved.

| Outcome | Meaning |
|---|---|
| `fixed` | The slot holds `right` (whitespace inside the slot is ignored — caption spacing is unreliable) |
| `missed` | The slot still holds the misrecognized form |
| `mangled` | The slot holds neither — a confident wrong answer, worse than a miss |
| over-correction | Anything outside the slot changed, **or** any edit at all to a `clean` / `trap` item |

Reported numbers:

- **recall** = fixed / error items
- **over-correction rate** = over-corrected items / all items
- **precision (proxy)** = fixed / (fixed + mangled + over-corrections). A proxy, not a true
  precision — the benchmark only knows about errors it planted, so it cannot see a correct
  edit it did not ask for. The name is inherited from the upstream scorer's `precision_proxy`,
  which is a proxy for the same reason (auditor consensus stands in for a gold answer).
- **net score** = (fixed − over-corrections) / error items. **Quote this one.** It can go
  negative, which is the point: at some level of aggression a corrector is worse than doing
  nothing.

## Baselines

Three ways of using the dataset itself as a correction system (`benchmark/baselines.py`).
None is a proposed method; they exist to give the benchmark a floor and to show what the
penalty measures.

- **naive** — plain substring replacement, all 89 pairs.
- **boundary** — whitespace-flexible matching with a non-alphanumeric guard on ASCII keys.
  This mirrors how the upstream pipeline matches.
- **guarded** — boundary, minus any key shorter than 4 characters (60 of 89 pairs survive).
  Short Korean keys are where blind replacement does its damage, and Korean is agglutinative,
  so there is no word boundary to fall back on.

| System | Recall | plain | spacing | Mangled | Over-corr. | Over-corr. rate | Precision (proxy) | **Net score** |
|---|---|---|---|---|---|---|---|---|
| naive | 75.9% | 267/267 | 1/86 | 1 | 11 | 2.4% | 95.7% | **72.8%** |
| boundary | 100.0% | 267/267 | 86/86 | 0 | 14 | 3.1% | 96.2% | **96.0%** |
| guarded (min key 4) | 68.0% | 180/267 | 60/86 | 0 | 2 | 0.4% | 99.2% | **67.4%** |

Committed results: `benchmark/results/baseline-*.json` (full per-item breakdown).

What the table says:

1. **Whitespace flexibility is worth ~24 points of recall** and costs 3 extra
   over-corrections. On this evaluation set it is clearly the right trade.
2. **Every over-correction came from the trap set** — never from a `clean` item. Direction
   matters: a `wrong → right` rule cannot fire on a sentence that is already correct. The
   `clean` items therefore look like dead weight against dictionary baselines, and are kept
   because a generative system (an LLM asked to "fix the finance terms") absolutely can
   rewrite an already-correct sentence. They are the control that catches that.
3. **A minimum key length buys precision at a steep price**: 32 points of recall to remove
   12 of 14 over-corrections. The two survivors (`엔트로피`, `코스하고`) are ≥4 characters, so
   length alone will never solve this — context will.
4. The one `mangled` case is instructive. On `SK하이하스`, naive replacement applies
   `하스 → 하이닉스` inside a longer key and emits `SK하이하이닉스`. Cascading rules are a real
   failure mode, and a fix-only metric would have scored it as merely a miss.

Ceiling note: the dictionary baselines see the exact pairs the error items were generated
from, so 100% recall on `boundary` measures the eval set's construction, not generalization.
The discriminating signal in v0 is the over-correction axis. See limitations.

## Reporting your own system

Emit a JSON object `{item_id: output_sentence}` (or JSONL of `{"id", "output"}`), then:

```bash
python3 benchmark/score.py --pred mysystem.json --name mysystem \
    --json benchmark/results/mysystem.json \
    --compare benchmark/results/baseline-boundary.json
```

Items with no prediction are scored as left unchanged and reported separately, so partial
runs are visible rather than silently favourable.

## Limitations (v0)

- **In-domain by construction.** Error items are generated from the same 89 pairs a
  dictionary system would use, so a lookup baseline reaches 100% recall. This measures
  robustness and restraint, not the ability to catch unseen misrecognitions. A held-out
  split needs pairs that are verified but withheld from the published snapshot — a v0.2
  question, since the snapshot ships everything verified.
- **No context diversity.** Six templates, one slot each. The slot is always followed by a
  space to avoid Korean particle agreement leaking the answer, which also means no
  particle-attached context is tested. Pairs that are mid-utterance fragments
  (`코스하고 → 코스닥으로`) read unnaturally in a carrier frame. Option (b) from the task —
  LLM-generated carrier sentences with the misrecognition injected — is the v0.2 plan.
- **14 traps is thin.** They are the only discriminating axis right now and were chosen by
  hand from the shipped pairs. Growing the trap set is the cheapest way to make v0.1 harder.
- **No ranking or partial credit.** One slot, one answer. Systems that flag uncertainty
  instead of editing get no credit for the restraint beyond avoiding the penalty.
