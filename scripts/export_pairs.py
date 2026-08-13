"""Export verified confusion pairs from the production dictionary into data/.

Must run with the upstream pipeline's venv (needs DB env + registry). The
upstream checkout is located via the ``GGULMUSE_ROOT`` environment variable:

    cd "$GGULMUSE_ROOT" && .venv/bin/python \
        /path/to/ko-finance-asr-corrections/scripts/export_pairs.py

Hard lines (AGENTS.md): ships only enabled tier A/B pairs; person-name pairs and
anything whose `wrong` or `right` resolves to a person in the registry are dropped.
Internal-only fields (`reason`, `approved_by`) never leave the pipeline; the
upstream `source` is not exported verbatim either - it is mapped to the public
`evidence` vocabulary so that renaming an internal value cannot silently change
the published schema.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

GGULMUSE = Path(
    os.environ.get("GGULMUSE_ROOT", str(Path.home() / "projects" / "ggulmuse"))
).expanduser()
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GGULMUSE))

from pipeline.correction_cycle import verified_kind  # noqa: E402
from pipeline.correction_store import load_dictionary_rows  # noqa: E402
from pipeline.registry import get_registry  # noqa: E402

# Overridable so a dry-run can recount to a scratch path without dirtying the
# upstream working tree (a shared checkout — see refresh_snapshot.py).
OSS_COUNTS_PATH = Path(
    os.environ.get(
        "OSS_COUNTS_PATH", str(GGULMUSE / "pipeline" / "data" / "oss-corpus-counts.json")
    )
).expanduser()

PUBLIC_FIELDS = [
    "wrong",
    "right",
    "corpus_count",
    "observed_count",
    "tier",
    "evidence",
    "category",
    "auditor_models",
    "approved_at",
    "word_boundary",
    "apply_scope",
]

# Upstream `source` -> published `evidence`. `tier` says how much authority a pair
# carries; `evidence` says how it was verified. They are not the same axis: a pair
# can be human-approved on top of auditor consensus (see 업항 → 업황), and the
# goldset path coming from upstream an upstream pipeline task promotes without consensus at all.
EVIDENCE_BY_SOURCE = {
    "human": "human",
    "auditor": "auditor-consensus",
    "goldset": "goldset-alignment",
}


def categorize(right: str, kind: str | None) -> str:
    if kind in ("stock", "term"):
        return kind
    if any(ch.isdigit() for ch in right):
        return "number"
    return "other"


# The person-exclusion list is private data (it names real people via their
# misrecognized forms), so its home is the upstream private repo, not here.
# The legacy in-repo copy is still honored during the transition; when both
# exist their union applies — dropping a name can only happen deliberately,
# never by picking the wrong file.
EXCLUSION_SOURCES = [
    GGULMUSE / "pipeline" / "data" / "person-exclusions.txt",
    REPO / "scripts" / "person-exclusions.txt",  # legacy, pending upstream move
]


def load_exclusions() -> set[str]:
    names: set[str] = set()
    for path in EXCLUSION_SOURCES:
        if not path.exists():
            continue
        found = {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        print(f"person exclusions: {len(found)} from {path}", file=sys.stderr)
        names |= found
    if not names:
        print(
            "WARNING: no person-exclusion list found — only the registry "
            "person check stands between person names and data/",
            file=sys.stderr,
        )
    return names


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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO / "data",
        help="directory for pairs.json/pairs.csv (default: data/)",
    )
    ap.add_argument(
        "--report",
        type=Path,
        default=None,
        help="also write a machine-readable export report (JSON) here; "
        "contains dropped person names, so keep it out of the public repo",
    )
    args = ap.parse_args()

    registry = get_registry()
    rows = load_dictionary_rows()
    exclusions = load_exclusions()
    corpus_counts, corpus_meta = load_corpus_counts()

    shipped: list[dict] = []
    dropped_person: list[str] = []
    review_other: list[str] = []
    unknown_source: list[str] = []

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
        evidence = EVIDENCE_BY_SOURCE.get(e.source or "")
        if evidence is None:
            # Never guess. An unmapped source means upstream grew a verification
            # path we have not described publicly yet.
            evidence = "unknown"
            unknown_source.append(f"{e.wrong}→{e.right} (source={e.source!r})")
        shipped.append(
            {
                "wrong": e.wrong,
                "right": e.right,
                "corpus_count": corpus_counts.get(e.wrong),
                "observed_count": e.observed_count,
                "tier": e.tier,
                "evidence": evidence,
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

    data_dir = args.out
    data_dir.mkdir(parents=True, exist_ok=True)
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
    if unknown_source:
        print(f"!! unmapped source -> evidence='unknown': {len(unknown_source)}")
        print("   add it to EVIDENCE_BY_SOURCE and document it in docs/SCHEMA.md")
        for line in unknown_source:
            print(f"  - {line}")

    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "shipped": len(shipped),
                    "dropped_person": dropped_person,
                    "review_other": review_other,
                    "unknown_source": unknown_source,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
