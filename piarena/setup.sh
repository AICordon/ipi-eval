#!/usr/bin/env bash
# Prepare the PIArena checkout this harness runs: clone at the pinned commit, install the defense
# module, apply the patch. Idempotent - run it again after pulling this repository.
set -eu -o pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
SRC=$ROOT/upstream
PIN=8bd7a89e4a88d64b8354d9aa80a684923be6b795
PATCH=$ROOT/patches/piarena-8bd7a89.patch

if [ ! -d "$SRC/.git" ]; then
  echo "cloning PIArena into $SRC"
  git clone --quiet https://github.com/sleeepeer/PIArena.git "$SRC"
fi
have=$(git -C "$SRC" rev-parse HEAD)
if [ "$have" != "$PIN" ]; then
  if [ -n "$(git -C "$SRC" status --porcelain --untracked-files=no)" ] && \
     ! git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null; then
    echo "the checkout at $SRC has local changes that are not this harness's patch; not touching it"
    exit 1
  fi
  git -C "$SRC" apply --reverse "$PATCH" 2>/dev/null || true
  git -C "$SRC" fetch --quiet origin "$PIN" 2>/dev/null || git -C "$SRC" fetch --quiet origin
  git -C "$SRC" checkout --quiet "$PIN"
fi
echo "PIArena at $(git -C "$SRC" rev-parse --short HEAD)"

cp "$ROOT/defense_aicordon_api.py" "$SRC/piarena/defenses/defense_aicordon_api.py"
if git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null; then
  echo "patch already applied"
else
  git -C "$SRC" apply --check "$PATCH" || { echo "the patch does not apply to this checkout"; exit 1; }
  git -C "$SRC" apply "$PATCH"
  echo "patch applied: judge reuses the backend model, result files are written atomically,"
  echo "               defenses with missing dependencies are skipped at import"
fi
echo "ready. Next: ./run.sh --status"
