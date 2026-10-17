"""Latency vs document length, one line per card, from bench.py results (../data/latency_quadrat_*.jsonl).

Per card (the `gpu` field, so the repeated passes `_r1`, `_r2`, … of one card fold together): the median over passes per
document; documents binned on a log grid of tokens; per bin the median with its 95% bootstrap interval (line + band);
the fit ms = a + b*n + c*n^2 (n = tokens) over every document, least squares on log(ms), with 95%
bootstrap intervals of a, b, c (in the legend and
in the printed table). Light theme, for publication.

    python3 plot.py [results.jsonl ...] [--out ../plots/latency_quadrat.png]
"""
import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
# AI Cordon colours, light theme: accent green, its light step for a second card (the pair checked for colour-blind
# separation); AI Cordon's red stands for injections, so it is not a card colour
COLORS = ["#00864b", "#53bb80"]
BG, INK, MUTED, GRID = "#f2f5f3", "#0f1d16", "#566860", (15 / 255, 29 / 255, 22 / 255, 0.13)
EDGES = np.unique(np.round(np.geomspace(32, 40000, 22)).astype(int))
RNG = np.random.default_rng(7)


def boot_median(x, n=2000):
    b = np.median(RNG.choice(x, (n, len(x))), 1)
    return np.median(x), np.percentile(b, 2.5), np.percentile(b, 97.5)


def qfit(n, ms):
    """ms = a + b*n + c*n^2, least squares on log(ms): every document counts by its relative error."""
    from scipy.optimize import least_squares
    f = lambda p: np.log(np.maximum(p[0] + p[1] * n + p[2] * n ** 2, 1e-3)) - np.log(ms)
    return least_squares(f, x0=[130, 0.25, 5e-6], x_scale=[100, 0.1, 1e-6]).x


def boot_fit(n, ms, k=300):
    p = qfit(n, ms)
    idx = RNG.integers(0, len(n), (k, len(n)))
    B = np.array([qfit(n[i], ms[i]) for i in idx])
    lo, hi = np.percentile(B, [2.5, 97.5], 0)
    return p, lo, hi


def load(files):
    per = defaultdict(lambda: defaultdict(list))                 # gpu -> doc id -> [records]
    for f in files:
        for l in open(f):
            if l.strip():
                r = json.loads(l)
                if r.get("ms") and r.get("n_tokens"):
                    per[r["gpu"]][r["id"]].append(r)
    out = {}
    for gpu, docs in per.items():
        out[gpu] = [dict(id=i, y=R[0].get("y", 0), n=R[0]["n_tokens"], chars=R[0]["chars"], ms=float(np.median([r["ms"] for r in R])),
                         passes=len(R), synthetic=R[0].get("synthetic", False), bin=R[0].get("bin"),
                         peak=max((r.get("peak_gb") or 0) for r in R))
                    for i, R in docs.items()]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--out", default=str(HERE / "results/intent-2.1.1/latency-rtx5060ti.png"))
    a = ap.parse_args()
    files = a.files or sorted(glob.glob(str(HERE / "results/*/*_r*.jsonl")))
    data = load(files)
    from matplotlib import font_manager
    for f in sorted((HERE / "fonts").glob("Inter-*.ttf")):           # Inter (OFL), if put in fonts/; else the default
        font_manager.fontManager.addfont(str(f))
    plt.rcParams["font.family"] = ["Inter", "DejaVu Sans"]           # DejaVu for glyphs outside the subset
    fig, ax = plt.subplots(figsize=(9, 5.6), dpi=160, facecolor=BG)
    ax.set_facecolor(BG)
    table = []
    for c, (gpu, D) in zip(COLORS, sorted(data.items(), key=lambda t: -np.median([d["ms"] for d in t[1]]))):
        n = np.array([d["n"] for d in D], float)
        ms = np.array([d["ms"] for d in D], float)
        syn = np.array([d["synthetic"] for d in D])
        p_, p_lo, p_hi = boot_fit(n, ms)                                      # the whole range
        a0, b, c2 = p_
        ax.scatter(n, ms, s=9, color=c, alpha=0.5, linewidths=0, zorder=2)
        xf = np.geomspace(n.min(), n.max(), 200)
        ax.plot(xf, a0 + b * xf + c2 * xf ** 2, color=c, lw=2.2, zorder=5,
                label=f"{gpu} — ms ≈ {a0:.0f} + {b:.3f}·n + {c2 * 1e6:.1f}·10⁻⁶·n²")
        # the typical document: the median length of the Quadrat documents, its time read off the fit
        # the sample is stratified by length, so its own median is not Quadrat's: take Quadrat's median length in
        # characters (docs_meta.json) and convert with this reader's characters per token on the measured documents
        meta = json.loads((HERE / "docs_meta.json").read_text())
        cpt = float(np.median([d["chars"] / d["n"] for d in D if not d["synthetic"]]))
        n_typ = meta["quadrat_median_chars"] / cpt
        t_typ = a0 + b * n_typ + c2 * n_typ ** 2
        ax.scatter([n_typ], [t_typ], s=70, color=c, edgecolors=BG, linewidths=1.6, zorder=6)
        ax.annotate(f"typical document\n{n_typ:,.0f} tokens → {t_typ:,.0f} ms", (n_typ, t_typ),
                    xytext=(-14, 22), textcoords="offset points", ha="right", va="bottom", fontsize=9, color=INK,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
        pts = []
        for l_, h_ in zip(EDGES, EDGES[1:]):                                  # Quadrat: log bins of tokens
            m = ~syn & (n >= l_) & (n < h_)
            if m.sum() >= 5:
                pts.append((np.median(n[m]), *boot_median(ms[m]), int(l_), int(h_), int(m.sum())))
        for g in sorted({d["bin"] for d in D if d["synthetic"]}, key=lambda g: int(g.split("-")[1][:-1])):
            m = np.array([d["synthetic"] and d["bin"] == g for d in D])        # long: one point per target length
            pts.append((np.median(n[m]), *boot_median(ms[m]), int(n[m].min()), int(n[m].max()), int(m.sum())))
        xs, ys, lo, hi = (np.array([q[i] for q in pts]) for i in range(4))
        for x, med, ql, qh, l_, h_, k in pts:
            table.append((gpu, "all", l_, h_, k, med, ql, qh))
        print(f"{gpu}: {len(D)} documents, passes {sorted({d['passes'] for d in D})}; "
              f"ms = {a0:.1f} [{p_lo[0]:.1f}, {p_hi[0]:.1f}] + {b:.4f} [{p_lo[1]:.4f}, {p_hi[1]:.4f}] * n "
              f"+ {c2:.3e} [{p_lo[2]:.3e}, {p_hi[2]:.3e}] * n^2; "
              f"peak VRAM {max(d['peak'] for d in D):.1f} GB")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("document length, tokens", color=INK)
    ax.set_ylabel("time on the GPU per document, ms", color=INK)
    ax.set_title("AI Cordon Intent 2.1: detection time vs document length", color=INK, fontsize=11, loc="left")
    ax.grid(True, which="major", color=INK, alpha=0.13, lw=0.6, zorder=0)
    ax.grid(True, which="minor", color=INK, alpha=0.06, lw=0.5, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.legend(frameon=False, loc="upper left", fontsize=9, labelcolor=INK)
    fig.text(0.01, 0.012, "Documents: Quadrat-IPI v1.0.2 (up to ~5k tokens); longer ones are several Quadrat documents joined "
             "together.\nHalf of them contain an injection (the time does not depend on it). Dots: documents (median of the "
             "passes).\nLine: least-squares fit, n = document length in tokens. Typical document: the median length of all "
             "79,800 Quadrat documents.\nSetup: one document at a time, as the service runs it; the time of the detector's "
             "model only, network not included.", ha="left", va="bottom", fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, facecolor=BG)
    print(f"-> {a.out}")
    print("| card | documents | tokens | n | median ms | 95% interval |\n|---|---|---|---:|---:|---|")
    for gpu, name, l_, h_, k, med, ql, qh in table:
        print(f"| {gpu} | {name} | {l_}–{h_} | {k} | {med:.0f} | {ql:.0f}–{qh:.0f} |")


if __name__ == "__main__":
    main()
