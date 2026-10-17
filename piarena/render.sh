#!/usr/bin/env bash
# PNG copies of the figures for slides: light and dark, twice the pixel density.
# Needs google-chrome (or CHROME=...) and ImageMagick's `convert`. The SVG files are the source;
# the PNG files are made from them and can be deleted.
set -eu -o pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
RESULTS=${1:-$HERE/results/intent-1.5.2}
CHROME=${CHROME:-google-chrome}
OUT=$RESULTS/figures
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
cd "$HERE"
for theme in light dark; do
  python3 figures.py --results "$RESULTS" --theme "$theme" --suffix="-$theme" --out "$TMP" >/dev/null
  for name in board tradeoff; do
    svg=$TMP/$name-$theme.svg
    h=$(grep -o 'height="[0-9]*"' "$svg" | head -1 | tr -dc 0-9)   # the root tag comes first
    # headless Chrome keeps part of the window for itself: shoot taller, then cut to size
    "$CHROME" --headless=new --disable-gpu --no-sandbox --hide-scrollbars \
      --force-device-scale-factor=2 --window-size=980,$((h + 200)) \
      --screenshot="$TMP/$name-$theme.png" "file://$svg" >/dev/null 2>&1
    convert "$TMP/$name-$theme.png" -crop "1960x$((h * 2))+0+0" +repage "$OUT/$name-$theme.png"
    echo "written: ${OUT#$HERE/}/$name-$theme.png"
  done
done
