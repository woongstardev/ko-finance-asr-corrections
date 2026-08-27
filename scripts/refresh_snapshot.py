"""One-command snapshot refresh: recount -> export -> diff -> report.

Task 005. The weekly cron runs this in dry-run mode (the default) to *detect*
change; a human runs it with --write once a month to *publish* change. The
split is deliberate: the dataset grows in bursts (audit rounds), not on a
calendar, so weekly runs mostly confirm "nothing new" — that confirmation is
the point (silence and breakage must look different).

Runs on the host that has the upstream checkout and its venv. This script
itself needs only the stdlib; it invokes the upstream venv's python for the
recount and export subprocesses. Point ``GGULMUSE_ROOT`` at that checkout.

    python3 scripts/refresh_snapshot.py              # dry-run: report only
    python3 scripts/refresh_snapshot.py --notify     # dry-run + Telegram on change/failure (cron mode)
    python3 scripts/refresh_snapshot.py --write      # update data/ + CHANGELOG.md (monthly release prep)

Exit codes: 0 = ran fine (changed or not), nonzero = the refresh itself failed
(recount/export crashed, or the exporter met an unmapped evidence source —
that means upstream grew a verification path we have not described publicly,
and publishing on top of it would be wrong).

Reports and state live outside the repo on purpose — they can contain dropped
person names, which never enter this (eventually public) tree. Set
``OSS_REFRESH_REPORT_DIR`` and ``OSS_REFRESH_STATE``; both default to a
per-user state directory, never to a path inside the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GGULMUSE = Path(
    os.environ.get("GGULMUSE_ROOT", str(Path.home() / "projects" / "ggulmuse"))
).expanduser()
# Defaults follow the XDG state convention rather than any one host's layout:
# the previous defaults pointed at a machine that stopped running this in
# 2026-08, and a stale default is worse than none — it writes reports somewhere
# nobody reads. Every path here is outside the repository by construction,
# because reports can name dropped person candidates.
STATE_HOME = Path(
    os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
).expanduser()
REPORT_DIR = Path(
    os.environ.get("OSS_REFRESH_REPORT_DIR", STATE_HOME / "oss-refresh" / "reports")
).expanduser()
STATE_PATH = Path(
    os.environ.get("OSS_REFRESH_STATE", STATE_HOME / "oss-refresh" / "state.json")
).expanduser()
CRED_PATH = Path(
    os.environ.get(
        "OSS_REFRESH_TELEGRAM_ENV",
        str(Path.home() / ".config" / "oss-corrections" / "telegram.env"),
    )
).expanduser()

# Frequency fields drift a little every week just because the corpus grows.
# They are reported, but they alone do not make a snapshot "changed" —
# otherwise every weekly run would cry wolf and the alert would train people
# to ignore it.
FREQUENCY_FIELDS = {"corpus_count", "observed_count"}

HEARTBEAT_SECONDS = 30 * 24 * 3600  # "no change" still gets said out loud monthly


def venv_python() -> Path:
    py = GGULMUSE / ".venv" / "bin" / "python"
    if not py.exists():
        sys.exit(f"upstream venv not found: {py} (set GGULMUSE_ROOT?)")
    return py


def run_step(name: str, cmd: list[str], env: dict | None = None) -> str:
    proc = subprocess.run(
        cmd, cwd=GGULMUSE, capture_output=True, text=True, timeout=1500, env=env
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        sys.exit(f"step failed: {name} (exit {proc.returncode})")
    return proc.stdout


def load_pairs(path: Path) -> dict[tuple[str, str], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {(p["wrong"], p["right"]): p for p in payload["pairs"]}


def diff_pairs(
    old: dict[tuple[str, str], dict], new: dict[tuple[str, str], dict]
) -> dict:
    added = sorted(k for k in new if k not in old)
    removed = sorted(k for k in old if k not in new)
    meta_changed: list[tuple[tuple[str, str], list[str]]] = []
    freq_changed: list[tuple[str, str]] = []
    for k in sorted(set(old) & set(new)):
        fields = [f for f in new[k] if old[k].get(f) != new[k].get(f)]
        meta = [f for f in fields if f not in FREQUENCY_FIELDS]
        if meta:
            meta_changed.append((k, meta))
        elif fields:
            freq_changed.append(k)
    return {
        "unchanged_count": len(set(old) & set(new)) - len(meta_changed),
        "added": added,
        "removed": removed,
        "meta_changed": meta_changed,
        "freq_changed": freq_changed,
    }


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def send_telegram(text: str) -> bool:
    """One-way bot channel. Credentials come from CRED_PATH, never from git."""
    try:
        env = {}
        for line in CRED_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
        token, chat = env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"]
    except (OSError, KeyError):
        print("WARNING: telegram credentials unavailable — not notifying", file=sys.stderr)
        return False
    payload = urllib.parse.urlencode(
        {"chat_id": chat, "text": text, "disable_web_page_preview": "true"}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return bool(json.load(resp).get("ok", False))
    except Exception as exc:
        print(f"WARNING: telegram send failed: {type(exc).__name__}", file=sys.stderr)
        return False


def fmt_pair(k: tuple[str, str]) -> str:
    return f"{k[0]} → {k[1]}"


def check_corpus_coverage(candidate_dir: Path, write: bool) -> str:
    """Did the frequency scan behind this candidate actually reach the corpus?

    2026-08-27: the upstream transcript tree vanished between two runs. The
    recount scanned 0 videos, wrote an all-zero counts artifact over the
    canonical one, and the export carried 132 pairs whose every corpus_count was
    0. Both gates passed — the schema gate because 0 is a legal int (fixed since)
    and the benchmark gate because scoring never reads the counts.

    A collapse is visible only against the previous snapshot, which is why this
    lives here rather than in validate_snapshot.py: half the corpus disappearing
    is as wrong as all of it, and only the published snapshot knows how big the
    corpus was yesterday.
    """
    candidate = json.loads((candidate_dir / "pairs.json").read_text(encoding="utf-8"))
    published = json.loads((REPO / "data" / "pairs.json").read_text(encoding="utf-8"))
    now = (candidate.get("corpus") or {}).get("scanned_videos") or 0
    before = (published.get("corpus") or {}).get("scanned_videos") or 0

    problem = ""
    if now <= 0:
        problem = "the recount reached 0 videos"
    elif before and now < before // 2:
        problem = f"the corpus shrank {before} → {now} videos (more than half)"

    # The counted tree is cumulative and append-only (SCHEMA.md → corpus_count):
    # it never loses a transcript, so any decrease at all means the recount looked
    # at a different tree, not a smaller one. That is the failure a "half the
    # corpus" threshold misses — counting the live worker tree instead of the
    # mirror reads as 1,490 → 1,216 and sails through. There is no override flag,
    # by the same rule as the other gates: a legitimate shrink means the
    # definition changed, and that belongs in a commit, not an environment
    # variable.
    if not problem and before and now < before:
        problem = (f"the corpus went {before} → {now} videos; a cumulative count "
                   "cannot shrink, so this recount counted a different tree")

    if not problem:
        return f"corpus: ok ({now} videos)"
    message = (f"corpus coverage: {problem} — the frequencies in this candidate "
               "come from a scan that did not see the corpus. Check the upstream "
               "transcript tree before retrying")
    if write:
        sys.exit(f"corpus gate failed — snapshot not written: {message}")
    sys.stderr.write(f"WARN: {message}\n")
    return f"corpus: FAILED ({problem})"


def run_gates(candidate_dir: Path, write: bool) -> str:
    """Schema contract + benchmark regression, on the candidate export.

    Dry-runs report; --write stops. The point of running them here rather than
    after copying into data/ is that a failed gate should leave the published
    snapshot untouched, not require a revert.
    """
    mode: list[str] = [] if write else ["--warn-only"]
    summary = [check_corpus_coverage(candidate_dir, write)]
    for name, cmd in (
        ("schema", [sys.executable, str(REPO / "scripts" / "validate_snapshot.py"),
                    "--dir", str(candidate_dir), "--skip-prose",
                    *(["--require-person-list"] if write else []), *mode]),
        ("benchmark", [sys.executable, str(REPO / "scripts" / "benchmark_gate.py"),
                       "--pairs", str(candidate_dir / "pairs.json"), *mode]),
    ):
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        print(proc.stdout, end="")
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        if proc.returncode != 0:
            if write:
                sys.exit(f"{name} gate failed — snapshot not written")
            summary.append(f"{name}: FAILED")
        else:
            hits = sum(1 for l in proc.stderr.splitlines() if l.startswith(("WARN", "FAIL")))
            summary.append(f"{name}: ok" + (f" ({hits} note(s))" if hits else ""))
    return " · ".join(summary)


def render_report(
    today: str, diff: dict, export_report: dict, new_person: list[str], old_count: int,
    new_count: int, gates: str = ""
) -> str:
    lines = [
        f"# oss-refresh dry-run — {today}",
        "",
        f"pairs: {old_count} → {new_count}",
        f"gates: {gates or 'not run'}",
        f"added: {len(diff['added'])} · removed: {len(diff['removed'])} · "
        f"metadata changed: {len(diff['meta_changed'])} · frequency-only drift: {len(diff['freq_changed'])}",
        "",
    ]
    if diff["added"]:
        lines.append("## Added")
        lines += [f"- {fmt_pair(k)}" for k in diff["added"]]
        lines.append("")
    if diff["removed"]:
        lines.append("## Removed")
        lines += [f"- {fmt_pair(k)}" for k in diff["removed"]]
        lines.append("")
    if diff["meta_changed"]:
        lines.append("## Metadata changed")
        lines += [f"- {fmt_pair(k)}: {', '.join(fs)}" for k, fs in diff["meta_changed"]]
        lines.append("")
    if new_person:
        lines.append("## ⚠ NEW person-pair candidates dropped by the filter (human must review)")
        lines += [f"- {s}" for s in new_person]
        lines.append("")
    if export_report.get("review_other"):
        lines.append("## category=other (review before release)")
        lines += [f"- {s}" for s in export_report["review_other"]]
        lines.append("")
    if export_report.get("unknown_source"):
        lines.append("## ✖ unmapped evidence source (refresh treated as FAILURE)")
        lines += [f"- {s}" for s in export_report["unknown_source"]]
        lines.append("")
    return "\n".join(lines) + "\n"


def update_changelog(today: str, diff: dict) -> None:
    """Fold this write's delta into the Unreleased section of CHANGELOG.md."""
    path = REPO / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    marker = "## [Unreleased]"
    if marker not in text:
        sys.exit("CHANGELOG.md has no '## [Unreleased]' section")
    entry_lines = []
    if diff["added"]:
        entry_lines.append("### Added")
        entry_lines += [f"- `{fmt_pair(k)}` ({today})" for k in diff["added"]]
        entry_lines.append("")
    if diff["removed"]:
        entry_lines.append("### Removed")
        entry_lines += [f"- `{fmt_pair(k)}` ({today})" for k in diff["removed"]]
        entry_lines.append("")
    if diff["meta_changed"]:
        entry_lines.append("### Changed")
        # A field added to the schema changes every row at once, and listing 135
        # identical bullets buries the three that are actually about pairs. When a
        # field moved on (almost) every pair, say it once as what it was: a schema
        # addition. The threshold is deliberately not 100% — a handful of rows can
        # legitimately keep a null.
        total = diff.get("unchanged_count", 0) + len(diff["meta_changed"])
        per_field: dict[str, int] = {}
        for _, fields in diff["meta_changed"]:
            for f in fields:
                per_field[f] = per_field.get(f, 0) + 1
        wholesale = {f for f, n in per_field.items() if total and n >= total * 0.9}
        for f in sorted(wholesale):
            entry_lines.append(f"- `{f}` added to every pair ({today})")
        for k, fields in diff["meta_changed"]:
            rest = [f for f in fields if f not in wholesale]
            if rest:
                entry_lines.append(f"- `{fmt_pair(k)}`: {', '.join(rest)} ({today})")
        entry_lines.append("")
    if not entry_lines:
        return
    head, _, tail = text.partition(marker)
    path.write_text(
        head + marker + "\n\n" + "\n".join(entry_lines) + "\n" + tail.lstrip("\n"),
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="recount -> export -> diff -> report")
    ap.add_argument("--write", action="store_true", help="update data/ and CHANGELOG.md (monthly)")
    ap.add_argument("--yes", action="store_true", help="skip the interactive confirmation on --write")
    ap.add_argument("--notify", action="store_true", help="Telegram on change/failure (weekly cron mode)")
    ap.add_argument("--no-recount", action="store_true", help="reuse the existing corpus counts artifact")
    ap.add_argument(
        "--baseline",
        type=Path,
        default=REPO / "data" / "pairs.json",
        help="snapshot to diff against (testing hook; default data/pairs.json)",
    )
    args = ap.parse_args()

    if os.environ.get("OSS_REFRESH_FORCE_FAIL"):
        sys.exit("OSS_REFRESH_FORCE_FAIL is set — failing on purpose (alert-path drill)")

    today = date.today().isoformat()
    py = venv_python()

    try:
        tmp = Path(tempfile.mkdtemp(prefix="oss-refresh-", dir="/tmp"))
        export_env = dict(os.environ)
        if not args.no_recount:
            # Dry-runs recount into scratch: the upstream checkout is a shared
            # working tree and an unattended weekly job must not dirty it.
            # --write refreshes the canonical artifact, which is then committed
            # upstream as part of the monthly procedure.
            recount_cmd = [str(py), "-m", "pipeline.correction_corpus", "--oss-counts"]
            if not args.write:
                counts_path = tmp / "oss-corpus-counts.json"
                recount_cmd += ["--out", str(counts_path)]
                export_env["OSS_COUNTS_PATH"] = str(counts_path)
            out = run_step("recount", recount_cmd)
            print(out, end="")

        # The corpus profile is ours to produce (scripts/corpus_profile.py) and
        # only possible where the corpus is readable, so it refreshes here rather
        # than being carried by hand between snapshots. A failure is not fatal:
        # the profile describes the corpus, and a snapshot without it is still a
        # valid snapshot.
        corpus_dir = os.environ.get("OSS_CORPUS_DIR")
        profile_path = os.environ.get("OSS_CORPUS_PROFILE_PATH")
        if corpus_dir and profile_path:
            proc = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "corpus_profile.py"),
                 "--corpus", corpus_dir, "--out", profile_path],
                cwd=REPO, capture_output=True, text=True,
            )
            print(proc.stdout, end="")
            if proc.returncode != 0:
                sys.stderr.write(f"WARNING: corpus profile failed: {proc.stderr.strip()[:200]}\n")

        export_report_path = tmp / "export-report.json"
        out = run_step(
            "export",
            [
                str(py),
                str(REPO / "scripts" / "export_pairs.py"),
                "--out",
                str(tmp),
                "--report",
                str(export_report_path),
            ],
            env=export_env,
        )
        print(out, end="")
        export_report = json.loads(export_report_path.read_text(encoding="utf-8"))

        if export_report.get("unknown_source"):
            # Publishing pairs whose verification path the public schema cannot
            # name would be a silent contract break — stop the line instead.
            sys.exit("export produced evidence='unknown' pairs — fix EVIDENCE_BY_SOURCE first")

        gates = run_gates(tmp, args.write)

        old = load_pairs(args.baseline)
        new = load_pairs(tmp / "pairs.json")
        diff = diff_pairs(old, new)

        state = load_state()
        seen_person = set(state.get("seen_person", []))
        new_person = [s for s in export_report.get("dropped_person", []) if s not in seen_person]

        report = render_report(today, diff, export_report, new_person, len(old), len(new), gates)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f"{today}.md"
        report_path.write_text(report, encoding="utf-8")
        print(report)
        print(f"report: {report_path}")

        changed = bool(diff["added"] or diff["removed"] or diff["meta_changed"] or new_person)

        if args.notify:
            now = time.time()
            last = float(state.get("last_notified", 0))
            if changed:
                send_telegram(
                    "📊 ko-finance-asr 주간 스냅숏 점검\n"
                    f"+{len(diff['added'])} / -{len(diff['removed'])} / "
                    f"변경 {len(diff['meta_changed'])} · 신규 인물 후보 {len(new_person)}건\n"
                    f"리포트: {report_path}"
                )
                state["last_notified"] = now
            elif now - last > HEARTBEAT_SECONDS:
                send_telegram(
                    "📊 ko-finance-asr 주간 점검 — 이번 달 변화 없음 "
                    f"(쌍 {len(new)}개 유지). 점검 자체는 정상 동작 중."
                )
                state["last_notified"] = now

        if args.write:
            check = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "release_check.py")], cwd=REPO
            )
            if check.returncode != 0:
                sys.exit("release_check failed — fix findings before writing the snapshot")
            if new_person and not args.yes:
                sys.exit(
                    "new person-pair candidates need human review before --write "
                    "(rerun with --yes after reviewing the report)"
                )
            if not args.yes and sys.stdin.isatty():
                answer = input(f"write {len(new)} pairs to data/ ? [y/N] ")
                if answer.strip().lower() != "y":
                    sys.exit("aborted")
            for name in ("pairs.json", "pairs.csv"):
                shutil.copy2(tmp / name, REPO / "data" / name)
            update_changelog(today, diff)
            print("data/ and CHANGELOG.md updated — review, commit, and (monthly) tag")

        # Person candidates count as "seen" only once a human had the chance to
        # see them in a report; recording them here is what makes next week's
        # report highlight only what is genuinely new.
        state["seen_person"] = sorted(
            seen_person | set(export_report.get("dropped_person", []))
        )
        state["last_run"] = today
        state["changed"] = changed
        save_state(state)
    except SystemExit as exc:
        if args.notify and exc.code not in (0, None):
            send_telegram(f"⚠️ ko-finance-asr 주간 스냅숏 점검 실패: {exc.code}")
        raise


if __name__ == "__main__":
    main()
