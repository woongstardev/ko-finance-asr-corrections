# Mini benchmark v0.2

**Task: given a Korean finance sentence containing an ASR misrecognition, fix it — without
touching anything else.**

The second half is the hard half. A system that rewrites aggressively scores well on fixes
and destroys text elsewhere; upstream measurement found that prompt-level instructions to
"be careful" moved error types around without reducing the total. So this benchmark scores
fixes and damage together, and the headline number subtracts one from the other.

Everything here is pure stdlib Python 3.10+. No installation, no network, no dependency on
the upstream pipeline.

```bash
python3 benchmark/mine_traps.py           # rank pairs by over-correction risk (trap candidates)
python3 benchmark/make_eval_set.py        # data/pairs.json + traps.json -> eval-set.json
python3 benchmark/baselines.py --all      # reference systems -> predictions/
python3 benchmark/score.py --pred benchmark/predictions/boundary.json
cd benchmark && python3 -m unittest discover    # scorer self-test (10 cases)
```

An LLM row needs credentials and is the one thing here that touches the network:

```bash
export ANTHROPIC_API_KEY=...                    # only this script needs it
python3 benchmark/llm_reference.py --runs 3     # -> predictions/ + a run manifest
```

## The evaluation set (482 items)

No caption text appears anywhere in this benchmark. Source transcripts are not
redistributable and the dataset's hard line excludes them, so every sentence is either a
template fill or hand-authored for this repo.

| Kind | Items | What it is | Correct behaviour |
|---|---|---|---|
| `error` / plain | 267 | Six carrier templates filled with a pair's `wrong` form, 3 per pair | Replace the slot with `right` |
| `error` / spacing | 86 | The same, with the spacing of `wrong` damaged — a space inserted mid-word, or a phrase's space removed | Replace the slot with `right` |
| `clean` | 89 | A template filled with `right` — already correct | Change nothing |
| `trap` | 40 | Hand-authored sentences where a pair's `wrong` string is legitimate Korean (`엔트로피` the physics term, `바위` the rock, `MCD` the McDonald's ticker, `FFC` the flat cable, `블랙락 시티`, `사업 항목`, `지진 난 주`) | Change nothing |

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
| naive | 75.9% | 267/267 | 1/86 | 1 | 25 | 5.2% | 91.2% | **68.8%** |
| boundary | 100.0% | 267/267 | 86/86 | 0 | 40 | 8.3% | 89.8% | **88.7%** |
| guarded (min key 4) | 68.0% | 180/267 | 60/86 | 0 | 15 | 3.1% | 94.1% | **63.7%** |

Committed results: `benchmark/results/baseline-*.json` (full per-item breakdown).

What the table says:

1. **Whitespace flexibility is worth ~24 points of recall** and costs 15 extra
   over-corrections. In v0, with 14 traps, that cost looked like 3 and the trade was
   obviously right; at 40 traps it is a real trade with a visible price. The v0.2 trap set
   was written to probe exactly this, so the movement is a measurement, not a surprise.
2. **Every over-correction came from the trap set** — never from a `clean` item. Direction
   matters: a `wrong → right` rule cannot fire on a sentence that is already correct. The
   `clean` items therefore look like dead weight against dictionary baselines, and are kept
   because a generative system (an LLM asked to "fix the finance terms") absolutely can
   rewrite an already-correct sentence. They are the control that catches that.
3. **A minimum key length buys precision at a steep price**: 32 points of recall to remove
   25 of 40 over-corrections. More useful is *which* 15 survive — every one is ≥4 characters,
   and a third of them (`지진난주`, `올리브형`, `대원전설`, `신형증권`, `마이크로님`) are keys
   that only match because the matcher joins across a space. **Length guards the wrong axis.**
   The residual false positives come from whitespace flexibility, and no key-length floor
   reaches them; context will.
4. The one `mangled` case is instructive. On `SK하이하스`, naive replacement applies
   `하스 → 하이닉스` inside a longer key and emits `SK하이하이닉스`. Cascading rules are a real
   failure mode, and a fix-only metric would have scored it as merely a miss.

Ceiling note: the dictionary baselines see the exact pairs the error items were generated
from, so 100% recall on `boundary` measures the eval set's construction, not generalization.
The discriminating signal is the over-correction axis. See limitations.

### v0 → v0.2 score movement

The trap set grew from 14 to 40 and the eval set from 456 to 482 items, so **v0.2 numbers are
not comparable to v0 numbers.** Both are recorded here rather than quietly overwritten:

| System | Net score v0 (14 traps) | Net score v0.2 (40 traps) |
|---|---|---|
| naive | 72.8% | 68.8% |
| boundary | 96.0% | 88.7% |
| guarded | 67.4% | 63.7% |

Quote the benchmark identifier (`ko-finance-asr-corrections/mini-v0.2`, in `eval-set.json`)
with any number taken from here. A benchmark whose numbers move without a version is worse
than no benchmark.

## How traps are chosen

`benchmark/mine_traps.py` ranks the shipped pairs by over-correction risk and prints the
reason; a person then writes the sentence. The split is deliberate — deciding *which key is
dangerous* is mechanical, deciding *whether a Korean sentence reads naturally* is not, and an
auto-generated trap that reads wrong would quietly poison the benchmark.

Four risk classes, in descending order of how reliably they bite:

| Class | What it finds | At this snapshot |
|---|---|---|
| cross-pair | Another pair's key inside this pair's key or corrected form — replacement order decides between right, missed and mangled | **2 cases**, both chains (`하스` in `SK 하이하스`, `하이네스` in `SK 하이네스`) |
| spanning | Every split point where whitespace-flexible matching could join across a word boundary (`미국 체류` → `미국체`) | The productive class — most v0.2 traps came from here |
| ascii | Pure-ASCII keys, which collide with tickers, brands and acronyms | 12 keys; 5 had a real collision worth writing (`FFC`, `SKS`, `SPB`, plus the two v0 ones) |
| short | Keys under 4 characters — the class `guarded` drops wholesale | 28 keys |

**A negative result worth recording**: the class this benchmark was expected to mine —
another pair's `wrong` sitting inside a pair's *corrected* form, which would let a dictionary
damage its own output — is **empty at 89 pairs**, as is the re-trigger class. The mining code
stays because both classes appear the moment the snapshot grows a variant family, and finding
zero is only informative if you looked.

## Reporting your own system

Emit a JSON object `{item_id: output_sentence}` (or JSONL of `{"id", "output"}`), then:

```bash
python3 benchmark/score.py --pred mysystem.json --name mysystem \
    --json benchmark/results/mysystem.json \
    --compare benchmark/results/baseline-boundary.json
```

Items with no prediction are scored as left unchanged and reported separately, so partial
runs are visible rather than silently favourable.

## Reproducing an LLM row

Dictionary baselines are deterministic and re-run from `data/pairs.json` with nothing
installed. An LLM row is neither, so it ships under stricter rules — a benchmark row nobody
can interrogate is decoration:

- **Pin the exact model version string.** Generic aliases (`latest`, a family name) are not
  acceptable, because the number and the model it describes come apart within weeks.
- **Publish the prompt verbatim** and every request parameter, in the result JSON.
  Note what is *not* pinnable: current Claude models removed `temperature`, `top_p` and
  `top_k` outright, so there is no sampling knob to fix. Run-to-run variation is inherent,
  which is the whole reason for the rule below rather than an argument against it.
- **Never report a single run.** Report the mean and the spread over **N ≥ 3** runs. Fixing
  the temperature does not make an LLM deterministic, and newer models are dropping the
  parameter altogether.
- **The benchmark stays standard-library only.** The caller script may need network access
  and an API key; `score.py` never does. An LLM row exists here as a committed result file
  plus the script that produced it, and re-running it is optional.
- **Say what the model may already know.** These pairs are public once this repo is, so a
  model may have memorised the dictionary rather than reasoned about the sentence. The carrier
  sentences are synthetic, so there is no transcript contamination — but pair-knowledge
  contamination is real and belongs in the result's interpretation.

## Limitations (v0.2)

- **In-domain by construction.** Error items are generated from the same 89 pairs a
  dictionary system would use, so a lookup baseline reaches 100% recall. This measures
  robustness and restraint, not the ability to catch unseen misrecognitions. A held-out
  split needs pairs that are verified but withheld from the published snapshot. **v0.2 does
  not solve this and does not pretend to**: the snapshot ships everything that passes
  verification, so there is nothing held out to test against. Held-out candidates only become
  possible when the upstream goldset starts producing pairs.
- **No context diversity.** Six templates, one slot each. The slot is always followed by a
  space to avoid Korean particle agreement leaking the answer, which also means no
  particle-attached context is tested. Pairs that are mid-utterance fragments
  (`코스하고 → 코스닥으로`) read unnaturally in a carrier frame. v0.2 did not change the
  frames: the trap set was the cheaper source of difficulty, and generated carrier sentences
  would need the same human review the traps got, at 353 items instead of 26.
- **40 traps still under-counts the exposure.** Each trap covers one key in one context, and
  a short key collides in many contexts at once — five v0.2 traps are second contexts for a
  key that already had one, and they fire just as reliably. The trap set is a floor on the
  false-positive surface, never a measurement of it.
- **The traps are adversarial to substring matching by construction.** Every one was checked
  to fire under the `boundary` matcher before being kept, which is why that baseline
  over-corrects on 40 of 40. That makes the trap axis a floor for dictionary systems rather
  than a ranking among them; it discriminates where it is meant to, between systems that use
  context and systems that do not.
- **No LLM row yet.** The table is still three dictionaries, so the question this benchmark
  exists to answer — dictionary versus LLM once over-corrections are counted — is still half
  unanswered. `benchmark/llm_reference.py` implements the protocol above and the run is one
  API key away; until it has been run and the results committed, this limitation stands.
- **No ranking or partial credit.** One slot, one answer. Systems that flag uncertainty
  instead of editing get no credit for the restraint beyond avoiding the penalty.
