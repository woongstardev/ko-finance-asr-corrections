#!/usr/bin/env python3
"""Self-test for the scorer. Pure stdlib: python3 -m unittest discover benchmark

These pin the judgements that are easy to get quietly wrong: a fix that also
damages the sentence is not a clean fix, an already-correct sentence must be
left alone, and a spacing-only difference inside the slot is not a failure.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import score
import llm_reference


def error_item(item_id="e1", surface="변합기", right="변압기", frame="{w} 관련 이야기입니다."):
    text = frame.format(w=surface)
    start = text.index(surface)
    return {
        "id": item_id,
        "kind": "error",
        "variant": "plain",
        "input": text,
        "expected": text[:start] + right + text[start + len(surface) :],
        "span": [start, start + len(surface)],
        "surface": surface,
        "wrong": "변합기",
        "right": right,
        "category": "term",
    }


def guard_item(item_id="g1", text="엔트로피가 커지는 방향입니다.", kind="trap"):
    return {
        "id": item_id,
        "kind": kind,
        "input": text,
        "expected": text,
        "category": "trap" if kind == "trap" else "term",
    }


class SlotState(unittest.TestCase):
    def test_exact_fix(self):
        item = error_item()
        self.assertEqual(score._slot_state(item, item["expected"]), ("fixed", False))

    def test_untouched_is_missed(self):
        item = error_item()
        self.assertEqual(score._slot_state(item, item["input"]), ("missed", False))

    def test_wrong_answer_in_slot_is_mangled(self):
        item = error_item()
        out = item["input"].replace("변합기", "변전기")
        self.assertEqual(score._slot_state(item, out), ("mangled", False))

    def test_fix_plus_context_damage(self):
        item = error_item()
        out = item["expected"].replace("관련", "관련된")
        self.assertEqual(score._slot_state(item, out), ("fixed", True))

    def test_context_damage_without_fix(self):
        item = error_item()
        out = item["input"].replace("이야기", "얘기")
        self.assertEqual(score._slot_state(item, out), ("missed", True))

    def test_spacing_inside_slot_still_counts_as_fixed(self):
        item = error_item(surface="SK하이하스", right="SK하이닉스")
        out = item["input"].replace("SK하이하스", "SK 하이닉스")
        self.assertEqual(score._slot_state(item, out), ("fixed", False))

    def test_cascading_rules_are_mangled_not_fixed(self):
        item = error_item(surface="SK하이하스", right="SK하이닉스")
        out = item["input"].replace("SK하이하스", "SK하이하이닉스")
        self.assertEqual(score._slot_state(item, out), ("mangled", False))


class Aggregate(unittest.TestCase):
    def test_over_correction_pulls_net_score_down(self):
        items = [error_item(), guard_item()]
        clean = score.score(items, {"e1": items[0]["expected"], "g1": items[1]["input"]})
        self.assertEqual(clean["fixed"], 1)
        self.assertEqual(clean["over_corrections"]["total"], 0)
        self.assertEqual(clean["net_score"], 1.0)

        greedy = score.score(
            items, {"e1": items[0]["expected"], "g1": "앤트로픽가 커지는 방향입니다."}
        )
        self.assertEqual(greedy["fixed"], 1)
        self.assertEqual(greedy["over_corrections"]["trap"], 1)
        self.assertEqual(greedy["net_score"], 0.0)

    def test_missing_prediction_scores_as_unchanged(self):
        result = score.score([error_item()], {})
        self.assertEqual(result["missing_predictions"], 1)
        self.assertEqual(result["missed"], 1)
        self.assertEqual(result["over_corrections"]["total"], 0)

    def test_category_breakdown_counts_every_item(self):
        result = score.score([error_item(), guard_item()], {})
        total = sum(b["items"] for b in result["by_category"].values())
        self.assertEqual(total, 2)


class CliParsers(unittest.TestCase):
    """Each CLI reports its answer in a different shape, and a parser that stops
    understanding one returns an empty string - which the scorer reads as "left
    unchanged", i.e. a silently favourable run on trap items. These fixtures are
    real output shapes, trimmed."""

    class Proc:
        def __init__(self, stdout: str):
            self.stdout = stdout

    def parse(self, cli: str, stdout: str, last_message: str = ""):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "last.txt"
            if last_message:
                out.write_text(last_message, encoding="utf-8")
            return llm_reference.CLIS[cli]["parse"](self.Proc(stdout), out)

    def test_claude(self):
        text, cost, model = self.parse("claude", json.dumps(
            {"result": "투자자들이 엔비디아 이슈에 주목하고 있습니다.",
             "total_cost_usd": 0.0041, "model": "claude-opus-5", "is_error": False}))
        self.assertEqual(text, "투자자들이 엔비디아 이슈에 주목하고 있습니다.")
        self.assertAlmostEqual(cost, 0.0041)
        self.assertEqual(model, "claude-opus-5")

    def test_grok_unwraps_the_schema(self):
        text, cost, model = self.parse("grok", json.dumps(
            {"text": json.dumps({"sentence": "코스피가 올랐습니다."}),
             "total_cost_usd": 0.0076, "modelUsage": {"grok-4.6-build": {}}}))
        self.assertEqual(text, "코스피가 올랐습니다.")
        self.assertAlmostEqual(cost, 0.0076)
        self.assertEqual(model, "grok-4.6-build")

    def test_grok_without_the_schema_still_answers(self):
        text, _, _ = self.parse("grok", json.dumps({"text": "코스피가 올랐습니다."}))
        self.assertEqual(text, "코스피가 올랐습니다.")

    def test_codex_reads_the_last_message_not_the_transcript(self):
        text, _, _ = self.parse("codex", "thinking...\ntool call...\n",
                                last_message="반도체가 올랐습니다.\n")
        self.assertEqual(text, "반도체가 올랐습니다.")

    def test_qwen_takes_the_result_event(self):
        events = [
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"model": "tower-uncensored",
                                              "content": [{"type": "thinking", "thinking": "..."}]}},
            {"type": "result", "subtype": "success", "is_error": False,
             "result": "엔비디아 실적이 나왔습니다."},
        ]
        text, _, model = self.parse("qwen", json.dumps(events))
        self.assertEqual(text, "엔비디아 실적이 나왔습니다.")
        self.assertEqual(model, "tower-uncensored")

    def test_qwen_error_result_is_empty_not_a_pass(self):
        text, _, _ = self.parse("qwen", json.dumps(
            [{"type": "result", "is_error": True, "result": "rate limited"}]))
        self.assertEqual(text, "")


if __name__ == "__main__":
    unittest.main()
