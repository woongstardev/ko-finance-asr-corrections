#!/usr/bin/env python3
"""Regression tests for the release gates: every rule, one synthetic violation each.

    python3 scripts/test_gates.py

Standard library only, and no corpus or database — each test builds a small
snapshot in a temp directory, breaks exactly one thing, and asserts the gate
says so. The rules these cover were each added after something went wrong; the
tests exist so the fixes cannot quietly regress:

  * all-zero frequencies and a zero video count (2026-08-27: the corpus was
    unreachable, the recount wrote zeroes, and every gate passed the result)
  * a cumulative corpus that shrinks (counting a different tree reads as a small
    drop, which a "more than half" threshold sails past)
  * schema contract: types, enums, primary key, csv agreement, sort order
  * withdrawn history: a pair cannot be both withdrawn and shipped
  * the derived biasing list drifting from the pairs it is derived from
"""

from __future__ import annotations

import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VALIDATE = REPO / "scripts" / "validate_snapshot.py"

PAIR = {
    "wrong": "변합기", "right": "변압기", "corpus_count": 469, "right_count": 120,
    "observed_count": 3, "tier": "B", "evidence": "auditor-consensus",
    "category": "term", "ticker": None, "market": None,
    "auditor_models": ["a/b", "c/d"], "approved_at": "2026-08-12T03:44:01+00:00",
    "word_boundary": True, "apply_scope": "unique",
}
SECOND = {**PAIR, "wrong": "업항", "right": "업황", "corpus_count": 413, "right_count": 91}


def snapshot(pairs: list[dict]) -> dict:
    return {
        "dataset": "ko-finance-asr-corrections",
        "exported_at": "2026-08-27T00:00:00Z",
        "pair_count": len(pairs),
        "corpus": {"scanned_videos": 1490, "counted_at": "2026-08-27T00:00:00Z",
                   "channels": 43, "hours": 672.3, "mean_video_minutes": 27.1},
        "pairs": pairs,
    }


def write(directory: Path, payload: dict, *, withdrawn: dict | None = None,
          biasing: list[str] | None = None) -> None:
    (directory / "pairs.json").write_text(json.dumps(payload, ensure_ascii=False),
                                          encoding="utf-8")
    rows = [{**p, "auditor_models": ";".join(p["auditor_models"])} for p in payload["pairs"]]
    with (directory / "pairs.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if withdrawn is not None:
        (directory / "withdrawn.json").write_text(json.dumps(withdrawn, ensure_ascii=False),
                                                  encoding="utf-8")
    if biasing is not None:
        (directory / "biasing-list.txt").write_text(
            "# header\n" + "\n".join(f"{t}\t1" for t in biasing) + "\n", encoding="utf-8")


def validate(directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATE), "--dir", str(directory), "--skip-prose"],
        capture_output=True, text=True, cwd=REPO,
    )


class GateTests(unittest.TestCase):
    def check(self, mutate, expect: str | None, **files) -> None:
        """Apply one mutation to a valid snapshot and assert what the gate says."""
        payload = snapshot([copy.deepcopy(PAIR), copy.deepcopy(SECOND)])
        mutate(payload)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write(directory, payload, **files)
            result = validate(directory)
        if expect is None:
            self.assertEqual(result.returncode, 0, result.stderr)
            return
        self.assertNotEqual(result.returncode, 0, "gate accepted a broken snapshot")
        self.assertIn(expect, result.stderr)

    def test_valid_snapshot_passes(self):
        self.check(lambda p: None, None)

    def test_all_frequencies_zero(self):
        def zero(payload):
            for pair in payload["pairs"]:
                pair["corpus_count"] = 0
        self.check(zero, "every corpus_count is 0")

    def test_zero_videos_with_counts(self):
        self.check(lambda p: p["corpus"].update(scanned_videos=0),
                   "frequency scan reached no transcripts")

    def test_unknown_enum_value(self):
        self.check(lambda p: p["pairs"][0].update(evidence="unknown"),
                   "not a category")

    def test_duplicate_primary_key(self):
        self.check(lambda p: p["pairs"].append(copy.deepcopy(p["pairs"][0])),
                   "duplicate primary key")

    def test_wrong_equals_right(self):
        self.check(lambda p: p["pairs"][0].update(right=p["pairs"][0]["wrong"]),
                   "corrects nothing")

    def test_pair_count_mismatch(self):
        self.check(lambda p: p.update(pair_count=99), "pair_count 99")

    def test_sort_order(self):
        self.check(lambda p: p["pairs"].reverse(), "not in the exporter's sort order")

    def test_bad_field_type(self):
        self.check(lambda p: p["pairs"][0].update(corpus_count="469"), "expected")

    def test_withdrawn_pair_also_shipped(self):
        entry = {
            "wrong": PAIR["wrong"], "right": PAIR["right"], "withdrawn_at": "2026-08-27",
            "reason": "over-correction", "evidence_kind": "corpus-counterexample",
            "corpus_count": 10, "justified_matches": 2, "replaced_by": [],
            "shipped_in": [], "why": "x",
        }
        self.check(lambda p: None, "cannot be both",
                   withdrawn={"withdrawn": [entry]})

    def test_withdrawn_justified_exceeds_total(self):
        entry = {
            "wrong": "없는", "right": "없음", "withdrawn_at": "2026-08-27",
            "reason": "artifact", "evidence_kind": "audit", "corpus_count": 5,
            "justified_matches": 50, "replaced_by": [], "shipped_in": [], "why": "x",
        }
        self.check(lambda p: None, "exceeds corpus_count",
                   withdrawn={"withdrawn": [entry]})

    def test_biasing_list_drift(self):
        self.check(lambda p: None, "out of date with pairs.json",
                   biasing=[PAIR["right"]])

    def test_biasing_list_in_sync(self):
        self.check(lambda p: None, None, biasing=[PAIR["right"], SECOND["right"]])


class CorpusCoverageTests(unittest.TestCase):
    """The gate in refresh_snapshot, which needs the published snapshot to compare."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "refresh_snapshot", REPO / "scripts" / "refresh_snapshot.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        published = json.loads((REPO / "data" / "pairs.json").read_text(encoding="utf-8"))
        self.published = (published.get("corpus") or {}).get("scanned_videos") or 0

    def candidate(self, videos: int, tmp: str) -> Path:
        directory = Path(tmp)
        (directory / "pairs.json").write_text(
            json.dumps({"corpus": {"scanned_videos": videos}}), encoding="utf-8")
        return directory

    def test_growth_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.module.check_corpus_coverage(
                self.candidate(self.published + 10, tmp), write=True)
        self.assertIn("ok", summary)

    def test_zero_videos_stops_the_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.module.check_corpus_coverage(self.candidate(0, tmp), write=True)

    def test_any_shrink_stops_the_write(self):
        """A cumulative corpus cannot shrink; a small drop means a different tree."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                self.module.check_corpus_coverage(
                    self.candidate(self.published - 1, tmp), write=True)

    def test_dry_run_reports_instead_of_exiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = self.module.check_corpus_coverage(self.candidate(0, tmp), write=False)
        self.assertIn("FAILED", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
