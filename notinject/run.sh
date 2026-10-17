#!/usr/bin/env bash
# One measurement: NotInject by the PIGuard protocol, through the `aicordon` package. Made for a tmux
# window -- the log is the monitor, so it goes to the console unbuffered.
#
#   ./run.sh --status          what is scored already, then exit
#   ./run.sh                   score everything missing, then write the report
#
# The state is counted from results/<run>/scores.jsonl, not from this log. Ctrl-C stops it: what was
# answered stays, and the same command continues from there.
#
#   API key:  AICORDON_API_KEY, `aicordon login`, or a line AICORDON_API_KEY=... in ./.env
#   version:  VERSION=v2.1.1          the detector version this run expects; it stops on the
#                                     first answer that carries another one
#   run dir:  RUN=results/<name>      (default: results/<detector>-<version>)
#   address:  BASE_URL=...            (default: the package's own)
#   parallel: WORKERS=2               requests in flight; the service allows 2 at a time per key
#   rate:     RATE=2                  requests per second at most; the service limits each key
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
DETECTOR=${DETECTOR:-intent}
VERSION=${VERSION-v2.1.1}
RUN=${RUN:-$HERE/results/${DETECTOR%%:*}${VERSION:+-${VERSION#v}}}
WORKERS=${WORKERS:-2}
RATE=${RATE:-2}
NAME=${NAME:-AI Cordon Intent${VERSION:+ ${VERSION#v}}}
PIN=${VERSION:+--version $VERSION}
BASE=${BASE_URL:+--base-url $BASE_URL}

STATUS_ONLY=0
for arg in "$@"; do
    case "$arg" in
        --status) STATUS_ONLY=1 ;;
        -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
        *) echo "unknown argument: $arg (see --help)"; exit 2 ;;
    esac
done

cd "$HERE"
export PYTHONUNBUFFERED=1

if [ "$STATUS_ONLY" = 1 ]; then
    "$PY" -m notinject_eval status --out "$RUN"
    exit 0
fi

# --- preconditions --------------------------------------------------------------------------- #
if [ -z "${AICORDON_API_KEY:-}" ] && [ -f "$HERE/.env" ]; then
    AICORDON_API_KEY=$(grep -E '^[[:space:]]*(export[[:space:]]+)?AICORDON_API_KEY=' "$HERE/.env" \
        | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//")
    [ -n "$AICORDON_API_KEY" ] && export AICORDON_API_KEY
fi
"$PY" - <<'PYEOF' || exit 2
import sys
try:
    from aicordon import intent
    intent.load
except (ImportError, AttributeError):
    sys.exit("needs aicordon >= 1.3 with the `intent` client: pip install -U aicordon")
from aicordon.intent import credentials as c
if not c.find_key():
    sys.exit(c.NO_KEY_HINT)
PYEOF

LOCK="$RUN/.lock"
mkdir -p "$RUN"
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
    echo "another run on $RUN is live (pid $(cat "$LOCK")); stop it first"; exit 1
fi
echo $$ > "$LOCK"

say() { printf '\n\033[1m=== %s · %s ===\033[0m\n' "$(date +%H:%M:%S)" "$*"; }
on_stop() { say "stopped"; "$PY" -m notinject_eval status --out "$RUN"; echo;
            echo "continue: $0"; rm -f "$LOCK"; exit 130; }
trap on_stop INT TERM
trap 'rm -f "$LOCK"' EXIT

say "dataset"
"$PY" -m notinject_eval fetch || exit 2

say "state before the run"
"$PY" -m notinject_eval status --out "$RUN"

say "scoring"
"$PY" -m notinject_eval score --out "$RUN" --detector "$DETECTOR" --workers "$WORKERS" --rate "$RATE" $BASE $PIN
code=$?
[ "$code" = 130 ] && on_stop

say "report"
"$PY" -m notinject_eval report --out "$RUN" --name "$NAME" || true
say "done (scoring exit $code)"
exit $code
