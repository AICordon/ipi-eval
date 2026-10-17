"""The defense board as figures: SVG files computed from the records, no packages needed.

  board.svg     one row per defense, three panels: ASR under `direct`, ASR under `combined`,
                utility on clean documents
  tradeoff.svg  the same defenses as points: attacks that succeed against utility kept

Every figure is written for both themes (`prefers-color-scheme`), parsed as XML before it is
saved, and carries its numbers as text, so nothing is readable by colour alone.

Usage: python3 figures.py [--results results/intent-1.5.2] [--theme auto|light|dark]
"""
import argparse
import pathlib
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

import report

ROOT = pathlib.Path(__file__).resolve().parent
WIDTH = 980
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
INK = {
    "light": {"surface": "#fcfcfb", "text": "#0b0b0b", "text2": "#52514e", "muted": "#898781",
              "grid": "#e1e0d9", "axis": "#c3c2b7", "accent": "#2a78d6", "rest": "#898781"},
    "dark": {"surface": "#1a1a19", "text": "#ffffff", "text2": "#c3c2b7", "muted": "#898781",
             "grid": "#2c2c2a", "axis": "#383835", "accent": "#3987e5", "rest": "#898781"},
}
OURS = "ours"
NOTE = ("AI Cordon Intent and “this run” are measured with PIArena's own pipeline; the other "
        "rows are the numbers PIArena publishes.",
        "PIArena's third attack, the adaptive “strategy” search, is not measured for "
        "AI Cordon Intent and is not in this figure.")


def style(theme):
    def block(ink):
        return (f".bg{{fill:{ink['surface']}}} .t{{fill:{ink['text']}}} "
                f".t2{{fill:{ink['text2']}}} .m{{fill:{ink['muted']}}} "
                f".grid{{stroke:{ink['grid']}}} .axis{{stroke:{ink['axis']}}} "
                f".accent{{fill:{ink['accent']}}} .rest{{fill:{ink['rest']}}} "
                f".ring{{stroke:{ink['surface']}}} .lead{{stroke:{ink['axis']}}}")
    base = (f"text{{font-family:{FONT};font-size:13px}} .h{{font-size:17px;font-weight:600}} "
            ".good{fill:url(#good)} .goodtext{fill:#0ca30c} "
            ".b{font-weight:600} .s{font-size:12px} .n{font-variant-numeric:tabular-nums} "
            ".grid,.axis,.lead{stroke-width:1;fill:none} .ring{stroke-width:2}")
    if theme == "auto":
        return (base + " " + block(INK["light"])
                + " @media (prefers-color-scheme:dark){" + block(INK["dark"]) + "}")
    return base + " " + block(INK[theme])


def svg(width, height, body, theme, title, desc):
    out = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" role="img" aria-labelledby="ft fd">'
           f'<title id="ft">{escape(title)}</title><desc id="fd">{escape(desc)}</desc>'
           f'<style>{style(theme)}</style>'
           f'<rect class="bg" width="{width}" height="{height}"/>' + "".join(body) + "</svg>")
    ET.fromstring(out)            # an SVG in <img> is XML: one slip and nothing renders
    return out


def text(x, y, s, cls="t2", anchor="start"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}">'
            f'{escape(str(s))}</text>')


def bar(x, y, w, h, cls, tip):
    """A bar growing right from x: square at the baseline, 4px rounded at the data end."""
    r = min(4, w / 2, h / 2)
    d = (f"M{x:.1f},{y:.1f} h{w - r:.1f} a{r},{r} 0 0 1 {r},{r} v{h - 2 * r:.1f} "
         f"a{r},{r} 0 0 1 -{r},{r} h-{w - r:.1f} z")
    return f'<path d="{d}" class="{cls}"><title>{escape(tip)}</title></path>'


def board_rows(results):
    """The rows of the defense board, as `report.py` computes them, sorted by mean ASR."""
    runs = report.load_runs(results)
    theirs = report.load_theirs()
    done = [ds for ds in report.DATASETS
            if all((ds, at, df) in runs for at in report.ATTACKS for df in ("none", report.OURS))]
    if not done:
        raise SystemExit(f"no complete dataset in {results}")
    versions = sorted({str(r["defense"].get("version")) for (_, _, df), v in runs.items()
                       if df == report.OURS for r in v})
    if len(versions) != 1:
        raise SystemExit(f"{results} mixes detector versions {versions}")

    def ours(at, df, field):
        return report.mean([100 * report.mean([float(r[field]) for r in runs[(ds, at, df)]])
                            for ds in done])

    def pub(at, df, i):
        return report.mean([theirs.get((report.DATASETS[ds][0], at, df), (None, None))[i]
                            for ds in done])

    rows = [{"key": OURS, "name": f"AI Cordon Intent {versions[0].lstrip('v')}",
             "utility": ours("none", report.OURS, "utility"),
             "direct": ours("direct", report.OURS, "asr"),
             "combined": ours("combined", report.OURS, "asr")},
            {"key": "none-run", "name": "No defense, this run",
             "utility": ours("none", "none", "utility"),
             "direct": ours("direct", "none", "asr"),
             "combined": ours("combined", "none", "asr")}]
    for df in sorted({k[2] for k in theirs}):
        rows.append({"key": df,
                     "name": "No defense, published" if df == "none" else report.DISPLAY.get(df, df),
                     "utility": pub("none", df, 0), "direct": pub("direct", df, 1),
                     "combined": pub("combined", df, 1)})
    for r in rows:
        r["mean"] = report.mean([r["direct"], r["combined"]])
    rows.sort(key=lambda r: r["mean"])
    return rows, len(done), versions[0]


def board(rows, n_sets, theme):
    label_w, gap, top, row_h, thick = 214, 34, 116, 30, 14
    panel_w = (WIDTH - 24 - label_w - 2 * gap - 44) / 3
    panels = [("direct", "Attack succeeded, direct", "lower is better"),
              ("combined", "Attack succeeded, combined", "lower is better"),
              ("utility", "Utility on clean documents", "higher is better")]
    height = top + row_h * len(rows) + 40 + 50
    body = [text(24, height - 38, NOTE[0], "m s"), text(24, height - 20, NOTE[1], "m s"),
            text(24, 34, "Defenses in PIArena: attacks that succeed and utility that is kept",
                 "t h"),
            text(24, 56, f"Percent, mean over {n_sets} datasets. Backend model and judge "
                         "Qwen3-4B. Rows ordered by mean attack success.", "t2")]
    for p, (field, head, hint) in enumerate(panels):
        x0 = 24 + label_w + p * (panel_w + gap)
        body.append(text(x0, top - 22, head, "t b"))
        body.append(text(x0, top - 6, hint, "m s"))
        for tick in (0, 25, 50, 75, 100):
            x = x0 + panel_w * tick / 100
            body.append(f'<line class="{"axis" if tick == 0 else "grid"}" x1="{x:.1f}" '
                        f'y1="{top}" x2="{x:.1f}" y2="{top + row_h * len(rows)}"/>')
            body.append(text(x, top + row_h * len(rows) + 18, tick, "m s n", "middle"))
    for i, r in enumerate(rows):
        y = top + i * row_h
        ours = r["key"] == OURS
        body.append(text(24 + label_w - 14, y + row_h / 2 + 4.5, r["name"],
                         "t b" if ours else "t2", "end"))
        for p, (field, head, _) in enumerate(panels):
            x0 = 24 + label_w + p * (panel_w + gap)
            v = r[field]
            w = panel_w * v / 100
            tip = f"{r['name']}: {head.lower()} {v:.1f}%"
            if w >= 1:
                body.append(bar(x0, y + (row_h - thick) / 2, w, thick,
                                "accent" if ours else "rest", tip))
            body.append(text(x0 + max(w, 0) + 6, y + row_h / 2 + 4.5, f"{v:.1f}",
                             "t b n" if ours else "t2 n"))
    desc = "; ".join(f"{r['name']}: direct {r['direct']:.1f}, combined {r['combined']:.1f}, "
                     f"clean utility {r['utility']:.1f}" for r in rows)
    return svg(WIDTH, height, body, theme, "Defenses in PIArena", desc)


def tradeoff(rows, n_sets, theme):
    left, right, top, plot_h, x_max = 74, 40, 100, 440, 80
    plot_w = WIDTH - left - right
    height = top + plot_h + 64 + 50

    def X(v):
        return left + plot_w * v / x_max

    def Y(v):
        return top + plot_h * (1 - v / 100)

    body = [text(24, height - 38, NOTE[0], "m s"), text(24, height - 20, NOTE[1], "m s"),
            text(24, 34, "Defenses in PIArena: what gets through against what still works",
                 "t h"),
            text(24, 56, f"Percent, mean over {n_sets} datasets. Attack success is the mean of "
                         "the direct and the combined attack. Green marks the good corner.",
                 "t2"),
            # the wash: one hue, densest at the goal, gone before the middle of the plot
            '<defs><linearGradient id="good" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#0ca30c" stop-opacity="0.22"/>'
            '<stop offset="0.55" stop-color="#0ca30c" stop-opacity="0"/></linearGradient></defs>',
            f'<rect class="good" x="{left}" y="{top}" width="{plot_w}" height="{plot_h}"/>']
    for tick in range(0, x_max + 1, 20):
        body.append(f'<line class="{"axis" if tick == 0 else "grid"}" x1="{X(tick):.1f}" '
                    f'y1="{top}" x2="{X(tick):.1f}" y2="{top + plot_h}"/>')
        body.append(text(X(tick), top + plot_h + 20, tick, "m s n", "middle"))
    for tick in (0, 25, 50, 75, 100):
        body.append(f'<line class="{"axis" if tick == 0 else "grid"}" x1="{left}" '
                    f'y1="{Y(tick):.1f}" x2="{left + plot_w}" y2="{Y(tick):.1f}"/>')
        body.append(text(left - 10, Y(tick) + 4, tick, "m s n", "end"))
    body.append(text(left + plot_w, top + plot_h + 44,
                     "Attacks that succeeded, %   ◄ fewer is better", "t2", "end"))
    body.append(text(left, top - 12, "Utility on clean documents, %   ▲ more is better", "t2"))
    body.append(text(left + 14, top + 22, "the goal: nothing gets through, all utility kept",
                     "goodtext b s"))

    # where each label goes: (dx, dy, anchor); chosen so that no two labels meet
    place = {OURS: (12, -12, "start"), "pisanitizer": (12, 19, "start"),
             "attentiontracker": (12, 4, "start"), "secalign": (12, 4, "start"),
             "datasentinel": (12, 4, "start"), "piguard": (12, -2, "start"),
             "promptguard": (12, 4, "start"), "datafilter": (12, 10, "start"),
             "promptarmor": (0, 24, "middle"), "none-run": (0, -14, "middle")}
    pts = [r for r in rows if r["key"] != "none"]        # the published twin shares the label
    twin = next((r for r in rows if r["key"] == "none"), None)
    for r in sorted(pts, key=lambda r: r["key"] == OURS):
        ours = r["key"] == OURS
        x, y = X(r["mean"]), Y(r["utility"])
        tip = (f"{r['name']}: attacks succeeded {r['mean']:.1f}% "
               f"(direct {r['direct']:.1f}, combined {r['combined']:.1f}), "
               f"clean utility {r['utility']:.1f}%")
        if r["key"] == "none-run" and twin:
            body.append(f'<circle class="rest ring" cx="{X(twin["mean"]):.1f}" '
                        f'cy="{Y(twin["utility"]):.1f}" r="5"><title>'
                        f'{escape("No defense, published: attacks succeeded %.1f%%, clean utility %.1f%%" % (twin["mean"], twin["utility"]))}'
                        '</title></circle>')
        body.append(f'<circle class="{"accent" if ours else "rest"} ring" cx="{x:.1f}" '
                    f'cy="{y:.1f}" r="{7 if ours else 5}"><title>{escape(tip)}</title></circle>')
        dx, dy, anchor = place.get(r["key"], (12, 4, "start"))
        name = "No defense, this run and published" if r["key"] == "none-run" else r["name"]
        body.append(text(x + dx, y + dy, name, "t b" if ours else "t2", anchor))
        if ours:
            body.append(text(x + dx, y + dy - 16,
                             f"{r['mean']:.1f}% get through, utility {r['utility']:.1f}%",
                             "t2 s n", anchor))
    desc = "; ".join(f"{r['name']}: attacks succeeded {r['mean']:.1f}, clean utility "
                     f"{r['utility']:.1f}" for r in rows)
    return svg(WIDTH, height, body, theme, "Attack success against utility", desc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=None)
    ap.add_argument("--theme", default="auto", choices=("auto", "light", "dark"))
    ap.add_argument("--suffix", default="", help="added to the file names, e.g. -light")
    ap.add_argument("--out", default=None, help="where to write (default <results>/figures)")
    a = ap.parse_args()
    if a.results:
        results = pathlib.Path(a.results)
    else:
        held = sorted(p for p in (ROOT / "results").glob("intent-*") if p.is_dir())
        if len(held) != 1:
            raise SystemExit("--results is required, one of: "
                             + ", ".join(str(p.relative_to(ROOT)) for p in held))
        results = held[0]
    rows, n_sets, _ = board_rows(results)
    out = pathlib.Path(a.out) if a.out else results / "figures"
    out.mkdir(parents=True, exist_ok=True)
    for name, fig in (("board", board), ("tradeoff", tradeoff)):
        path = out / f"{name}{a.suffix}.svg"
        path.write_text(fig(rows, n_sets, a.theme), encoding="utf-8")
        print(f"written: {path}")


if __name__ == "__main__":
    main()
