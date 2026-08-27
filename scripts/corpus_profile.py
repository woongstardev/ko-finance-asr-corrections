#!/usr/bin/env python3
"""Summarise the caption corpus the frequencies are counted over.

    OSS_CORPUS_DIR=/path/to/processed python3 scripts/corpus_profile.py --out profile.json

The snapshot has always published how many videos were scanned and nothing else,
which leaves a reader unable to judge what the frequencies describe: 1,490 videos
could be a week of one channel or a year of forty. This writes the aggregate
shape of that corpus - counts, hours, channels - and nothing that identifies a
video, a channel or a sentence.

**Aggregates only, by policy** (AGENTS.md): no titles, no channel names, no
descriptions, no caption text. The script reads per-video metadata to count
distinct channels and reads transcript timings to total the hours, then throws
both away.

The corpus lives on the upstream host, so its path comes from the environment
(``OSS_CORPUS_DIR`` or ``--corpus``) and never from this repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TRANSCRIPT = "transcript_labeled.json"
BRIEF = "video_brief.json"


def profile(root: Path) -> dict:
    channels: set[str] = set()
    seconds = 0.0
    videos = 0
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        brief = entry / BRIEF
        if brief.exists():
            try:
                source = json.loads(brief.read_text(encoding="utf-8")).get("source") or {}
            except (OSError, ValueError):
                source = {}
            name = source.get("channel")
            if name:
                channels.add(name)          # counted, never stored
        transcript = entry / TRANSCRIPT
        if not transcript.exists():
            continue
        try:
            items = json.loads(transcript.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not items:
            continue
        videos += 1
        # Last segment's end is the transcribed length; close enough to the video
        # length for a corpus profile and far cheaper than probing the media.
        try:
            seconds += float(items[-1].get("end") or 0)
        except (AttributeError, TypeError, ValueError):
            pass
    return {
        "videos": videos,
        "channels": len(channels),
        "hours": round(seconds / 3600, 1),
        "mean_video_minutes": round(seconds / 60 / videos, 1) if videos else None,
        "profiled_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", type=Path, default=os.environ.get("OSS_CORPUS_DIR"),
                    help="transcript tree (default: $OSS_CORPUS_DIR)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not args.corpus:
        sys.exit("set OSS_CORPUS_DIR or pass --corpus; this repository stores no host paths")
    root = Path(args.corpus).expanduser()
    if not root.is_dir():
        sys.exit(f"corpus directory not found: {root}")
    result = profile(root)
    if not result["videos"]:
        sys.exit(f"no transcripts under {root} — refusing to write an empty profile")
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{result['videos']} videos · {result['channels']} channels · "
          f"{result['hours']} hours -> {args.out}")


if __name__ == "__main__":
    main()
