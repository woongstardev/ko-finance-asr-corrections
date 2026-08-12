"""Export verified confusion pairs from the production dictionary into data/.

Must run on Orbit with the ggulmuse venv (needs DB env + registry):

    cd $GGULMUSE_ROOT && .venv/bin/python \
        /path/to/ko-finance-asr-corrections/scripts/export_pairs.py

Hard lines (AGENTS.md): ships only enabled tier A/B pairs; person-name pairs and
anything whose `wrong` or `right` resolves to a person in the registry are dropped.
Internal-only fields (`reason`, `approved_by`, `source`) never leave the pipeline.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

GGULMUSE = Path.home() / "projects" / "ggulmuse"
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GGULMUSE))

from pipeline.correction_cycle import verified_kind  # noqa: E402
from pipeline.correction_store import load_dictionary_rows  # noqa: E402
from pipeline.registry import get_registry  # noqa: E402

OSS_COUNTS_PATH = GGULMUSE / "pipeline" / "data" / "oss-corpus-counts.json"

PUBLIC_FIELDS = [
    "wrong",
    "right",
    "corpus_count",
    "observed_count",
    "tier",
    "category",
    "auditor_models",
    "approved_at",
    "word_boundary",
    "apply_scope",
]


def categorize(right: str, kind: str | None) -> str:
    if kind in ("stock", "term"):
        return kind
    if any(ch.isdigit() for ch in right):
        return "number"
    return "other"


def load_exclusions() -> set[str]:
    path = REPO / "scripts" / "person-exclusions.txt"
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def load_corpus_counts() -> tuple[dict[str, int], dict]:
    """ggulmuse an upstream pipeline task 산출물. 없으면 corpus_count는 null로 배포된다."""
    if not OSS_COUNTS_PATH.exists():
        return {}, {}
    payload = json.loads(OSS_COUNTS_PATH.read_text(encoding="utf-8"))
    meta = {
        "scanned_videos": payload.get("scanned_videos"),
        "counted_at": payload.get("generated_at"),
    }
    return payload.get("counts", {}), meta


def main() -> None:
    registry = get_registry()
    rows = load_dictionary_rows()
    exclusions = load_exclusions()
    corpus_counts, corpus_meta = load_corpus_counts()

    shipped: list[dict] = []
    dropped_person: list[str] = []
    review_other: list[str] = []

    for e in rows:
        if not e.enabled or e.tier not in ("A", "B"):
            continue
        kind = verified_kind(e.right, registry)
        # A person match on either side excludes the pair — real names never ship.
        if (
            kind == "person"
            or registry.person(e.wrong)
            or registry.person(e.right)
            or e.wrong in exclusions
        ):
            dropped_person.append(f"{e.wrong}→{e.right} ({e.tier})")
            continue
        category = categorize(e.right, kind)
        if category == "other":
            review_other.append(f"{e.wrong}→{e.right} ({e.tier})")
        shipped.append(
            {
                "wrong": e.wrong,
                "right": e.right,
                "corpus_count": corpus_counts.get(e.wrong),
                "observed_count": e.observed_count,
                "tier": e.tier,
                "category": category,
                "auditor_models": list(e.auditor_models or []),
                "approved_at": e.approved_at or None,
                "word_boundary": e.word_boundary,
                "apply_scope": e.apply_scope,
            }
        )

    shipped.sort(
        key=lambda r: (-(r["corpus_count"] or 0), -(r["observed_count"] or 0), r["wrong"])
    )

    data_dir = REPO / "data"
    data_dir.mkdir(exist_ok=True)
    payload = {
        "dataset": "ko-finance-asr-corrections",
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pair_count": len(shipped),
        "corpus": corpus_meta or None,
        "pairs": shipped,
    }
    (data_dir / "pairs.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (data_dir / "pairs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PUBLIC_FIELDS)
        writer.writeheader()
        for r in shipped:
            row = dict(r)
            row["auditor_models"] = ";".join(row["auditor_models"])
            writer.writerow(row)

    print(f"shipped: {len(shipped)}")
    print(f"dropped (person): {len(dropped_person)}")
    for line in dropped_person:
        print(f"  - {line}")
    print(f"category=other (review before release): {len(review_other)}")
    for line in review_other:
        print(f"  - {line}")


if __name__ == "__main__":
    main()
