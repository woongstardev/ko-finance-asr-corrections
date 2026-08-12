#!/usr/bin/env python3
"""Self-test for the scorer. Pure stdlib: python3 -m unittest discover benchmark

These pin the judgements that are easy to get quietly wrong: a fix that also
damages the sentence is not a clean fix, an already-correct sentence must be
left alone, and a spacing-only difference inside the slot is not a failure.
"""

from __future__ import annotations

import unittest

import score


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


if __name__ == "__main__":
    unittest.main()
