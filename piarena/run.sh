#!/usr/bin/env bash
# PIArena's own loop with AI Cordon Intent standing in as one of its defenses.
#
# Backend LLM and judge are Qwen/Qwen3-4B-Instruct-2507, local, the column of PIArena's defense
# leaderboard. The detector is the live API. 13 datasets x {none, direct, combined} x
# {none, aicordon_api} = 78 runs; DEFENSES="none aicordon_api_cut" adds the sanitizer variant.
#
# Run it inside tmux. Ctrl-C is an ordinary stop: the state is recomputed from the result files,
# and a second launch continues where this one left off, sample by sample.
#
#   ./run.sh --status     state from the result files; changes nothing
#   ./run.sh              run or continue
#
# Environment: AICORDON_API_KEY (or a line in ./.env), PYTHON (default python3),
# PIARENA_AICORDON_POINT (1e-03 | 1e-04 | 1e-05, default 1e-04),
# VERSION (the detector version this run expects, default v1.5.2), SEED (default 42).
# PIArena's result files go to upstream/results/evaluation_results/intent-<version>/, so two
# detector versions never share a directory.
set -u -o pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
SRC=$ROOT/upstream
PY=${PYTHON:-python3}
ENVFILE=$ROOT/.env
MODEL=Qwen/Qwen3-4B-Instruct-2507
PIN=8bd7a89e4a88d64b8354d9aa80a684923be6b795
PATCH=$ROOT/patches/piarena-8bd7a89.patch
SEED=${SEED:-42}
POINT=${PIARENA_AICORDON_POINT:-1e-04}
# The detector version this run is allowed to see. The defense stops on the first answer that
# carries another one, so a release landing in the middle of a run cannot put two detectors in
# one table. For the same reason there is no answer cache.
VERSION=${VERSION:-${PIARENA_AICORDON_VERSION:-v1.5.2}}
NAME=${NAME:-intent-${VERSION#v}}
NEED_MIB=${NEED_MIB:-9000}
LOCK=$ROOT/out/.run.lock

# The 13 datasets of the defense leaderboard. PIArena's three *_knowledge_corruption sets are a
# different scenario (the attack is already inside the context, `injected_task` is empty) and
# have their own attack column; they are not run here.
DATASETS=(squad_v2 dolly_closed_qa dolly_information_extraction dolly_summarization
          gov_report_long hotpotqa_long hotpotqa_rag lcc_long msmarco_rag multi_news_long
          nq_rag passage_retrieval_en_long qasper_long)
ATTACKS=(none direct combined)
# aicordon_api drops a flagged document; aicordon_api_cut cuts the marked fragments out and keeps
# the rest. DEFENSES="none aicordon_api_cut" runs the second; the `none` runs are shared.
read -r -a DEFENSES <<< "${DEFENSES:-none aicordon_api}"

llm_name() { echo "${MODEL//\//-}"; }

state() {
  $PY - "$SRC" "$NAME" "$(llm_name)" "$SEED" "${DATASETS[*]}" "${ATTACKS[*]}" "${DEFENSES[*]}" <<'PYEOF'
import json, pathlib, sys
src, name, llm, seed = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
datasets, attacks, defenses = (a.split() for a in sys.argv[5:8])
base = pathlib.Path(src) / "results" / "evaluation_results" / name
done = todo = partial = 0
lines = []
for ds in datasets:
    n = len(json.load(open(pathlib.Path(src) / "datasets" / f"{ds}.json")))
    row = []
    for at in attacks:
        for df in defenses:
            f = base / f"{ds}-{llm}-{at}-{df}-{seed}.json"
            have = len(json.load(open(f))) if f.exists() else 0
            tag = f"{at[:4]}/{'cut' if df.endswith('_cut') else df[:4]}"
            if have >= n:
                done += 1; row.append(f"{tag}:ok")
            elif have:
                partial += 1; todo += 1; row.append(f"{tag}:{have}/{n}")
            else:
                todo += 1; row.append(f"{tag}:-")
    lines.append(f"  {ds:30s} {' '.join(row)}")
print(f"runs done {done}, left {todo} (of which started {partial})")
print("\n".join(lines))
PYEOF
}

free_mib() { nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1; }

stop() {
  echo
  echo "--- stopped ---"
  state
  echo "continue: $0"
  exit 130
}

[ -d "$SRC/.git" ] || { echo "no PIArena checkout at $SRC; run ./setup.sh first"; exit 1; }
if [ "${1:-}" = "--status" ]; then state; exit 0; fi
trap stop INT TERM

# --- preconditions ------------------------------------------------------------------------------
have=$(git -C "$SRC" rev-parse HEAD)
[ "$have" = "$PIN" ] || { echo "PIArena checkout is $have, expected $PIN; run ./setup.sh"; exit 1; }
git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null || {
  echo "the patch is not applied to the checkout; run ./setup.sh"; exit 1; }
cmp -s "$ROOT/defense_aicordon_api.py" "$SRC/piarena/defenses/defense_aicordon_api.py" || {
  echo "the defense module in the checkout differs from this repository's; run ./setup.sh"; exit 1; }
command -v "$PY" >/dev/null || { echo "no interpreter: $PY (set PYTHON)"; exit 1; }

if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
  echo "another run is live (pid $(cat "$LOCK")); stop it first"; exit 1
fi
mkdir -p "$ROOT/out"; echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

if [ -z "${AICORDON_API_KEY:-}" ] && [ -f "$ENVFILE" ]; then
  AICORDON_API_KEY=$(grep -E '^[[:space:]]*(export[[:space:]]+)?AICORDON_API_KEY=' "$ENVFILE" \
    | tail -1 | cut -d= -f2- | sed -e "s/^[\"']//" -e "s/[\"']$//")
fi
[ -n "${AICORDON_API_KEY:-}" ] || { echo "AICORDON_API_KEY is not set and not in $ENVFILE"; exit 1; }
export AICORDON_API_KEY

missing=$($PY -c "
import importlib
need={'torch':'torch','transformers':'transformers','accelerate':'accelerate',
      'datasets':'datasets','rouge':'rouge','fuzzywuzzy':'fuzzywuzzy',
      'Levenshtein':'python-Levenshtein'}
out=[]
for mod,pkg in need.items():
    try: importlib.import_module(mod)
    except Exception: out.append(pkg)
print(' '.join(out))")
if [ -n "$missing" ]; then
  echo "missing packages: $missing"
  echo "install them first:  $PY -m pip install $missing"
  exit 1
fi

free=$(free_mib)
echo "GPU free: ${free} MiB (the 4B backend wants about ${NEED_MIB})"
[ "$free" -ge "$NEED_MIB" ] || {
  echo "not enough free VRAM; free the card or stop the other process"; exit 1; }

export PIARENA_AICORDON_POINT="$POINT"
export PIARENA_AICORDON_VERSION="$VERSION"
export PIARENA_AICORDON_ON_REFUSAL="${PIARENA_AICORDON_ON_REFUSAL:-pass}"
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
# Less fragmentation when the card is shared.
export PYTORCH_ALLOC_CONF="${PYTORCH_ALLOC_CONF:-expandable_segments:True}"

cd "$SRC" || exit 1
echo "=== PIArena run ==="
echo "  name       $NAME      seed $SEED"
echo "  backend    $MODEL (judge: the same instance)"
echo "  detector   live API $VERSION, operating point $POINT, refusal policy $PIARENA_AICORDON_ON_REFUSAL"
echo
state
echo

total=$(( ${#DATASETS[@]} * ${#ATTACKS[@]} * ${#DEFENSES[@]} ))
k=0
for ds in "${DATASETS[@]}"; do
  for at in "${ATTACKS[@]}"; do
    for df in "${DEFENSES[@]}"; do
      k=$((k + 1))
      out="results/evaluation_results/$NAME/${ds}-$(llm_name)-${at}-${df}-${SEED}.json"
      n=$($PY -c "import json;print(len(json.load(open('datasets/$ds.json'))))")
      have=$($PY -c "
import json,os
p='$out'
print(len(json.load(open(p))) if os.path.exists(p) else 0)" 2>/dev/null || echo 0)
      if [ "$have" -ge "$n" ]; then
        echo "[$k/$total] $ds $at $df - done ($have/$n), skipping"
        continue
      fi
      # An undefended run does not depend on the detector: the one measured for another
      # version (same checkout, same model, same seed) is taken as it is.
      if [ "$df" = none ] && [ "$have" -eq 0 ]; then
        for other in results/evaluation_results/*/"$(basename "$out")"; do
          [ -f "$other" ] && [ "$other" != "$out" ] || continue
          if [ "$($PY -c "import json;print(len(json.load(open('$other'))))")" -ge "$n" ]; then
            mkdir -p "$(dirname "$out")/tmp_attack_results"
            cp "$other" "$out"
            cp "$(dirname "$other")/tmp_attack_results/$(basename "$out")" \
               "$(dirname "$out")/tmp_attack_results/" 2>/dev/null || true
            echo "[$k/$total] $ds $at $df - taken from $(basename "$(dirname "$other")")"
            continue 2
          fi
        done
      fi
      echo "[$k/$total] $ds $at $df - $have/$n done, running"
      # A failed combination is retried once the card has room again: on a shared card another
      # process can take the memory in the middle of a run. main.py resumes per sample, so
      # nothing done is redone. A combination that fails five times stops the run.
      tries=0
      until $PY -u main.py --dataset "datasets/$ds.json" --backend_llm "$MODEL" \
              --attack "$at" --defense "$df" --name "$NAME" --seed "$SEED"; do
        tries=$((tries + 1))
        if [ "$tries" -ge 5 ]; then
          echo "run failed 5 times: $ds $at $df"; state; echo "continue: $0"; exit 1
        fi
        echo "run failed: $ds $at $df (attempt $tries/5), waiting for the card"
        sleep 60
        until [ "$(free_mib)" -ge "$NEED_MIB" ]; do
          echo "  $(date +%H:%M) GPU free $(free_mib) MiB, waiting"
          sleep 60
        done
        echo "  retrying $ds $at $df"
      done
    done
  done
done

echo
echo "=== finished ==="
state
echo "next: $PY $ROOT/export.py --name $NAME && $PY $ROOT/report.py --write"
