#!/usr/bin/env bash
# The 16,800 injected rows of Quadrat-IPI v1.0.2 through one detector: does it point at the injection? For tmux.
#
#   ./run.sh --status        what is scored, counted from results on disk
#   ./run.sh                 score what is missing, then write the report
#
#   data:      QUADRAT_DATA=<Quadrat-IPI v1.0.2>/data            (required)
#   detector:  DETECTOR=intent (default) | intent:<name>
#   version:   VERSION=v2.1.1 (default)               the run stops on another one
#   API key:   AICORDON_API_KEY, or `aicordon login`; AICORDON_API_KEYS=k1,k2 spreads the load (2 req/s per key)
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-python3}
DETECTOR=${DETECTOR:-intent}
VERSION=${VERSION-v2.1.1}
RUN=${RUN:-$HERE/results/${DETECTOR%%:*}${VERSION:+-${VERSION#v}}}
NAME=${NAME:-AI Cordon Intent${VERSION:+ ${VERSION#v}}}
: "${QUADRAT_DATA:?set QUADRAT_DATA to the data/ directory of Quadrat-IPI v1.0.2}"
export QUADRAT_DATA PYTHONUNBUFFERED=1
# several keys: the first one also answers the key check below
[ -n "${AICORDON_API_KEYS:-}" ] && [ -z "${AICORDON_API_KEY:-}" ] && export AICORDON_API_KEY=${AICORDON_API_KEYS%%,*}
cd "$HERE"

say() { printf '\n\033[1m=== %s · %s ===\033[0m\n' "$(date +%H:%M:%S)" "$*"; }
st() { "$PY" quadrat_spans.py status --out "$RUN"; }

say "state"
st
[ "${1:-}" = "--status" ] && exit 0

"$PY" - <<'PYEOF' || exit 2
import importlib.util, sys
if importlib.util.find_spec("aicordon") is None:
    sys.exit("aicordon is not installed: pip install aicordon")
try:
    from aicordon import intent
    intent.load
except (ImportError, AttributeError):
    sys.exit("needs aicordon >= 1.3 with the `intent` client: pip install -U aicordon")
from aicordon.intent import credentials as c
if not c.find_key():
    sys.exit(c.NO_KEY_HINT)
PYEOF

say "scoring"
"$PY" quadrat_spans.py score --out "$RUN" --detector "$DETECTOR" ${VERSION:+--version $VERSION} --workers "${WORKERS:-1}"
code=$?
if [ "$code" = 130 ]; then say "stopped"; st; echo; echo "continue: $0"; exit 130; fi

say "report"
"$PY" quadrat_spans.py report --out "$RUN" --name "$NAME"
say "done (scoring exit $code)"
exit $code
