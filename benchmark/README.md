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
python3 scripts/validate_snapshot.py      # schema contract: fields, enums, keys, json<->csv
python3 scripts/benchmark_gate.py         # release gate: eval set grew only, no new cascades
python3 benchmark/mine_traps.py           # rank pairs by over-correction risk (trap candidates)
python3 benchmark/make_eval_set.py        # data/pairs.json + traps.json -> eval-set.json
python3 benchmark/baselines.py --all      # reference systems -> predictions/
python3 benchmark/score.py --pred benchmark/predictions/boundary.json
cd benchmark && python3 -m unittest discover    # scorer self-test (10 cases)
```

An LLM row is the one thing here that touches the network, and it takes either credential
you happen to have:

```bash
python3 benchmark/llm_reference.py --transport cli --runs 3        # Claude Code CLI's own auth
export ANTHROPIC_API_KEY=...                                       # or an API key
python3 benchmark/llm_reference.py --runs 3
```

## The evaluation set (721 items) <!-- stat:eval_items -->

No caption text appears anywhere in this benchmark. Source transcripts are not
redistributable and the dataset's hard line excludes them, so every sentence is either a
template fill or hand-authored for this repo.

| Kind | Items | What it is | Correct behaviour |
|---|---|---|---|
| `error` / plain | 267 | Six carrier templates filled with a pair's `wrong` form, 3 per pair | Replace the slot with `right` |
| `error` / spacing | 86 | The same, with the spacing of `wrong` damaged — a space inserted mid-word, or a phrase's space removed | Replace the slot with `right` |
| `clean` | 89 | A template filled with `right` — already correct | Change nothing |
| `trap` | 47 | <!-- stat:trap_count --> Hand-authored sentences where a pair's `wrong` string is legitimate Korean (`엔트로피` the physics term, `MCD` the McDonald's ticker, `FFC` the flat cable, `블랙락 시티`, `사업 항목`, `지진 난 주`, `아이비리그`, `삼성 자산운용`, `매도 체결`, `단도체` the transmission conductor, `SMP` the electricity price, `MDI` the chemical) | Change nothing |

The spacing variants are not synthetic difficulty for its own sake: YouTube auto-captions
drop the space at event boundaries essentially always, which is why the upstream matcher is
whitespace-flexible. A system that only does exact string matching will miss these, and the
baseline table below shows exactly how much that costs.

The evaluation set is **append-only across snapshots.** Item ids come from the pair's
`wrong` form rather than its position, and `make_eval_set.py` copies every existing item
across verbatim, so a new pair adds items and touches nothing else. That is what makes a
committed prediction file — an expensive LLM run, say — still valid next month, and it is
checked at release time by `scripts/benchmark_gate.py`.

The earlier positional scheme looked stable for as long as only frequencies drifted. It was
not: inserting a single pair reassigned 40 ids to different sentences and rewrote the carrier
sentence of 40 more.

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

- **naive** — plain substring replacement, all 135 pairs.
- **boundary** — whitespace-flexible matching with a non-alphanumeric guard on ASCII keys.
  This mirrors how the upstream pipeline matches.
- **guarded** — boundary, minus any key shorter than 4 characters (83 <!-- stat:guarded_keys -->
  of 135 <!-- stat:pair_count --> pairs survive).
  Short Korean keys are where blind replacement does its damage, and Korean is agglutinative,
  so there is no word boundary to fall back on.

| System | Recall | plain | spacing | Mangled | Over-corr. | Over-corr. rate | Precision (proxy) | **Net score** |
|---|---|---|---|---|---|---|---|---|
| naive | 75.3% | 405/405 | 1/134 | 0 | 24 | 4.5% | 94.4% | **70.9%** |
| boundary | 100.0% | 405/405 | 134/134 | 0 | 41 | 7.6% | 92.9% | **92.4%** |
| guarded (min key 4) | 61.6% | 249/405 | 83/134 | 0 | 15 | 2.8% | 95.7% | **58.8%** |
| Claude Opus 5 (no dictionary) † | 63.8% ±0.3 | — | — | 113.7 | 9.3 | 1.9% | 64.7% | **61.2% ±0.2** |

† Measured on `mini-v0.2` (482 items, 89 pairs) and carried forward unchanged: an LLM row is
tied to the eval set it was produced against, so it moves only when someone pays for another
run. The outputs themselves **are** committed
(`benchmark/results/predictions/`), so the row can be rescored offline even though it cannot
be re-measured for free.
The 207 items added in v0.3 are exactly the pairs the dictionary learned after that run,
which makes them a held-out set for the next LLM row rather than a gap to backfill.

The LLM row is `claude-opus-5` at effort `medium`, given the sentence and no dictionary, mean
over 3 runs (spread is the population standard deviation). Reached through the Claude Code
CLI with tools off and its default system prompt replaced — see "Reproducing an LLM row";
the exact flags, prompt and CLI version are in
`benchmark/results/llm-claude-opus-5-cli-manifest.json`.

Committed results: `benchmark/results/baseline-*.json` and
`benchmark/results/llm-claude-opus-5-cli-run{1,2,3}.json` plus a `-summary.json`
(`benchmark/aggregate_runs.py` produces the mean-and-spread summary from the per-run files).

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
   failure mode, and a fix-only metric would have scored it as merely a miss. **In v0.3 that
   case is gone** — `하스 → 하이닉스` was withdrawn upstream after a full-corpus recheck found
   it firing inside `하이퍼스케일러들`, so naive now mangles nothing. The trap remains in the
   set: it documents a failure mode of the method, which outlives the pair that exposed it.

### Dictionary versus LLM

This is the comparison the benchmark exists to make, and the answer is **the dictionary wins,
and not narrowly** — 88.7% against 61.2% net. Both figures are `mini-v0.2`, scored on the same
482 items: the dictionary's v0.3 score is higher still (93.3%), but quoting it against an LLM
run from a smaller eval set would be comparing two different exams.

The interesting part is that the LLM wins the axis the dictionary was supposed to lose:

- **It over-corrects roughly four times less** — 9.3 against 40. Given a sentence that is
  already correct, or one where a shipped key appears as ordinary Korean, it usually leaves
  the text alone. That is the restraint the penalty was designed to reward, and the LLM has it.
- **It cannot recover the specific term.** 114 of 353 error items came back `mangled` — a
  confident wrong answer rather than a miss. Breaking those down across the three runs:

  | What the model returned instead | Mean items |
  |---|---|
  | A different plausible finance term (`SKS`→`SKC`, `ACBM`→`ABCP`, `AM대`→`M&A`, `머표 법칙`→`무어의 법칙`) | 94.0 |
  | The right term with the wrong stem or particle (`코스하고`→`코스닥`, gold `코스닥으로`) | 20.3 |
  | The sentence reshaped rather than slot-edited | 1.3 |

  Only the first group is a real failure of knowledge, and it is the large one. These are
  misrecognitions whose correction is not inferable from the sentence — you have to have
  *observed* that this channel's captions turn `SK하이닉스` into `SKS`. That observation is
  exactly what the dataset is.

Two caveats, both against the dataset rather than the model. Roughly 20 items per run were
scored wrong for a stem/particle mismatch on fragment pairs (`코스하고 → 코스닥으로`), which the
limitations already flag as reading unnaturally in a carrier frame — the model's answer is
arguably right there and the gold string is the artifact. And on `펀더멘탈 → 펀더멘털`, the
highest-frequency pair, the model declines to edit; since that pair encodes a spelling
standard rather than a mishearing, declining is defensible. Neither changes the direction of
the result, but a reader deserves to know the gap is somewhat smaller than the table says.

Ceiling note: the dictionary baselines see the exact pairs the error items were generated
from, so 100% recall on `boundary` measures the eval set's construction, not generalization.
The discriminating signal is the over-correction axis. See limitations.

### v0 → v0.2 score movement

The trap set grew from 14 to 40 and the eval set from 456 to 482 items, so **v0.2 numbers are
not comparable to v0 numbers.** Both are recorded here rather than quietly overwritten:

| System | v0 (89 pairs, 14 traps) | v0.2 (89, 40 traps) | v0.3 (130, 40 traps) | v0.4 (135, 47 traps) |
|---|---|---|---|---|
| naive | 72.8% | 68.8% | 71.5% | 70.9% |
| boundary | 96.0% | 88.7% | 93.3% | **92.4%** |
| guarded | 67.4% | 63.7% | 57.2% | 58.8% |

v0.2 → v0.3 moves for three reasons at once, and they pull in different directions. 41 net new
pairs enlarge the error set; three unsafe keys were withdrawn or narrowed, which is why
boundary's over-corrections fall 40 → 35 and its net score rises; and `guarded` drops hardest
because the ≥4-character rule now discards 52 of 130 pairs rather than 28 of 89 — the new
pairs are mostly short stock-name fragments. That is the length guard failing on a larger
sample, not a new problem: v0.2 already found that residual false positives come from
whitespace flexibility, which a length floor cannot reach.

Quote the benchmark identifier (`ko-finance-asr-corrections/mini-v0.4`, in `eval-set.json`)
with any number taken from here. A benchmark whose numbers move without a version is worse
than no benchmark.

### What v0.4's traps caught

Seven traps were added from the miner's uncovered list, and six of them damage the boundary
baseline outright:

| Sentence contains | Becomes | Because |
|---|---|---|
| `아이비리그 출신` | `IBM리그 출신` | `아이비 → IBM` fires inside an ordinary word |
| `삼성 자산운용` | `삼성전자산운용` | `삼성자 → 삼성전자` spans the space |
| `매도 체결` | `반도체결` | `매도체 → 반도체` spans the space |
| `단도체보다 복도체` | `반도체보다 복도체` | `단도체` is a transmission-line term, not a misrecognition |
| `SMP가 오르면` | `에스앤피가 오르면` | SMP is Korea's electricity system marginal price |
| `MDI 스프레드` | `엔비디아 스프레드` | MDI is a chemical feedstock |

Two things follow. First, four of the six span a word boundary rather than sitting inside a
long word — the same shape v0.2 identified as the residual failure mode, now with five more
examples. Second, `guarded` scores 15 over-corrections on this set, unchanged from v0.3,
**because its length floor throws all six of these pairs away**. Avoiding a trap by discarding
the pair is not precision; it costs 38.4% recall, which is why the guarded row is the worst
net score in the table despite the best precision.

The seventh trap, `소부장 단위`, passes cleanly. It documents a key that used to span into it
(`소부 장단 → 소부장`) and was replaced upstream by inflected keys; the sentence stays in the
set so the fix stays visible if a base key ever returns.

## Held-out: what happens on pairs the dictionary has not learned yet

Every number above is in-domain by construction — the error sentences are generated from the
same pairs the dictionary looks up, so a lookup scores 100% recall and the benchmark cannot
say whether the method generalises. The v0.3 snapshot made the first honest test possible
without withholding anything: 44 pairs arrived after the committed LLM run, so their 220 items
are a slice **no system in the earlier table had seen** (41 is the net pair growth, three having
been withdrawn in the same snapshot; the slice is built from what arrived, not from the net).

Scored 2026-08-27 on those 220 items (176 error, 44 clean, no traps):

| System | Recall | Over-corrections | **Net score** |
|---|---|---|---|
| Dictionary of the *previous* snapshot (89 pairs, boundary) | 2.3% (4/176) | 0 | **2.3%** |
| Same, keys ≥ 4 chars | 0.0% | 0 | **0.0%** |
| Claude Opus 5, no dictionary, 3 runs | 73.7% ±1.0 | 1.3 (0.6%) | **72.9% ±0.7** |
| Dictionary of the *current* snapshot (130 pairs) | 100.0% | 0 | 100.0% |

**This reverses the in-domain result, and both halves are true.** A dictionary is worth 100%
on the errors it has seen and ~2% on the ones it has not; the model is worth ~73% on anything
that sounds recoverable and cannot be trusted to leave correct text alone forever. They are
not competitors — the dictionary is what verification *produces*, and this row measures the
gap it was built to close. The honest summary of both tables is: **quote the dictionary for
coverage of known errors, and never quote it as evidence that dictionaries generalise.**

Two cautions on reading the LLM row:

- Its recall here (73.7%) is *higher* than its 63.8% on the v0.2 set, which is not improvement
  — the newer pairs are easier. Most are near-miss variants of terms already in the snapshot
  (`단도체`/`매도체`/`반조체`/`밤도체` → `반도체`), and a model recovers those from context.
  Arbitrary mappings like `SKS → SK하이닉스` are what it still cannot do, and the earlier set
  had proportionally more of them.
- 31 of 176 error items still come back mangled — a confident wrong term rather than a miss.
  That failure mode does not shrink with the easier slice.

Reproducing the slice needs no new data: it is the items in `eval-set.json` at `mini-v0.3`
that are absent from the same file at `mini-v0.2`, which `benchmark/heldout_set.py` extracts
from the file's own git history — `--baseline-rev` names an older revision, and with no flags
it takes the newest committed set whose items differ from the current one, which is the
previous snapshot's:

```bash
python3 benchmark/heldout_set.py --out /tmp/heldout.json          # this month's slice
python3 benchmark/baselines.py --mode boundary --eval /tmp/heldout.json \
    --pairs <previous snapshot's data/pairs.json>                 # the dictionary row
python3 benchmark/llm_reference.py --transport cli --eval /tmp/heldout.json \
    --label heldout-YYYY-MM                                       # the model row
```

Score the *previous* snapshot's dictionary against it, never the current one: the current
dictionary contains these pairs and returns 100% by construction, which is the in-domain
number wearing a held-out label.
Results are committed as `benchmark/results/llm-claude-opus-5-cli-heldout-*.json`; the run cost
$3.56 for 3 × 220 items and its manifest records the model id, prompt and flags like any other
LLM row. The model outputs are committed too, in `benchmark/results/predictions/`, so anyone
can rescore this row without an API key — the one thing they cannot do for free is produce a
*new* run of it.

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
- **Name the harness, not just the model.** The `cli` transport reaches the same model
  through the Claude Code CLI — a coding agent, invoked with `--tools ""`, `--safe-mode` and
  its default system prompt replaced. That is close to a bare API call but not identical, so
  the manifest records the transport, the CLI version, and every flag, and the results table
  labels the row. Do not merge a `cli` row and an `api` row into one number.
- **Say what the model may already know.** These pairs are public once this repo is, so a
  model may have memorised the dictionary rather than reasoned about the sentence. The carrier
  sentences are synthetic, so there is no transcript contamination — but pair-knowledge
  contamination is real and belongs in the result's interpretation.

## Limitations (mini-v0.4)

- **In-domain by construction.** Error items are generated from the same pairs a dictionary
  system would use, so a lookup baseline reaches 100% recall on the main table. That measures
  robustness and restraint, not the ability to catch unseen misrecognitions. The held-out row
  above is the answer to it and is not a substitute for it: it covers only the pairs that
  arrived since the last measurement, so it is small, it moves with upstream's promotion rate,
  and it says nothing about the items in the main table.
- **A pair that is wrong in itself is invisible here.** Every error item's expected output is
  built from the pair's own `right`, so a defective correction is graded against its own
  defect and scores full marks. Three pairs that swallow a following particle
  (`시가총이 → 시가총액`, turning "시가총액이 크다" into "시가총액 크다") were found by
  sweeping the corpus, not by this benchmark, and no amount of items would have surfaced them.
  Read the scores as "does the system apply the dictionary well", never as "is the dictionary
  right"; `scripts/counterexample_scan.py` is the tool for the second question.
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
- **One LLM, one prompt, one effort level.** The LLM row is a reference point, not a survey:
  a different prompt (few-shot, or one that tells the model it may decline) would move it, and
  no other model has been run. Read it as "a strong general model, told only what the task is,
  lands here", not as a ceiling for LLMs on this task.
- **`mangled` is stricter than "wrong".** The scorer compares against one gold string, so a
  correction that is defensible but differently spelled, spaced, or inflected counts as a
  confident error. For dictionary systems this never bites; for generative systems it costs
  roughly 20 items per run at this snapshot. See "Dictionary versus LLM".
- **No ranking or partial credit.** One slot, one answer. Systems that flag uncertainty
  instead of editing get no credit for the restraint beyond avoiding the penalty.
