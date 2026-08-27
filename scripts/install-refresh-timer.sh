#!/bin/sh
# Install the weekly snapshot dry-run as a systemd user timer.
#
#   sh scripts/install-refresh-timer.sh          # install and start
#   sh scripts/install-refresh-timer.sh --remove # stop and uninstall
#
# The dry-run recounts into a scratch directory and never writes to data/ or to
# the upstream checkout, so it is safe to run unattended. Publishing stays a
# once-a-month human step (AGENTS.md) because a person has to review dropped
# person-name candidates before anything ships.
#
# Everything is derived from where this checkout actually lives or from the
# environment at install time, so the units carry no path this script did not
# compute. Host-specific values are passed in rather than baked in:
#
#   GGULMUSE_ROOT=... GGULMUSE_DATA_DIR=... OSS_CORPUS_DIR=... \
#     OSS_REFRESH_TELEGRAM_ENV=... sh scripts/install-refresh-timer.sh
#
# Requires `loginctl enable-linger $USER` for the timer to fire without an
# active login session.
set -eu

REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
NAME=oss-corrections-refresh

if [ "${1:-}" = "--remove" ]; then
    systemctl --user disable --now "$NAME.timer" 2>/dev/null || true
    rm -f "$UNIT_DIR/$NAME.service" "$UNIT_DIR/$NAME.timer"
    systemctl --user daemon-reload
    echo "removed $NAME.{service,timer}"
    exit 0
fi

mkdir -p "$UNIT_DIR"

# Only pass through what the caller actually set — an empty Environment= line
# would be a syntax error, and a guessed default would be someone else's layout.
ENV_LINES=""
# GGULMUSE_DATA_DIR points the upstream recount at the corpus (it lives outside
# the upstream checkout since 2026-08); OSS_CORPUS_DIR and OSS_CORPUS_PROFILE_PATH
# feed the corpus profile. Without the first of these the recount scans nothing,
# writes zeroes, and the gates stop the release - which is the safe failure, but
# a weekly job that always fails is a broken detector.
for var in GGULMUSE_ROOT GGULMUSE_DATA_DIR OSS_REFRESH_REPORT_DIR OSS_REFRESH_STATE \
           OSS_REFRESH_TELEGRAM_ENV OSS_CORPUS_DIR OSS_CORPUS_PROFILE_PATH; do
    eval "value=\${$var:-}"
    [ -n "$value" ] && ENV_LINES="${ENV_LINES}Environment=$var=$value
"
done
ENV_LINES=${ENV_LINES%%
}

cat > "$UNIT_DIR/$NAME.service" <<EOF
[Unit]
Description=ko-finance-asr-corrections weekly snapshot dry-run
Documentation=file://$REPO/AGENTS.md

[Service]
Type=oneshot
WorkingDirectory=$REPO
ExecStart=$(command -v python3) $REPO/scripts/refresh_snapshot.py --notify
# Reports name dropped person-name candidates, so they stay outside the repo.
# Telegram credentials are optional: without them the run still produces its
# report and says so, rather than failing.
$ENV_LINES
TimeoutStartSec=1800
EOF

cat > "$UNIT_DIR/$NAME.timer" <<EOF
[Unit]
Description=Weekly ko-finance-asr-corrections snapshot dry-run

[Timer]
OnCalendar=Mon 07:20
# A missed week is run at the next opportunity: the point of this timer is that
# silence and breakage look different, which a skipped run would undo.
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "$NAME.timer"
systemctl --user list-timers "$NAME.timer" --all --no-pager
