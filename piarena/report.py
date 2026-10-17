"""AI Cordon Intent next to the defenses PIArena publishes, from the records in results/.

Only datasets where all six combinations are complete are counted, and every published defense
is averaged over that SAME set of datasets - a partial run never compares thirteen of their sets
to nine of ours. Averages are over datasets, as PIArena's leaderboard computes them; the pooled
line counts samples and carries a 95% Wilson interval.

One results directory holds one detector version; the report names it in the title and refuses
a directory that mixes two.

Usage: python3 report.py [--results results/intent-1.5.2] [--write]
"""
import argparse
import io
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
LLM_THEIRS = "qwen3-4b"
OURS = "aicordon_api"
OURS_NAME = "AI Cordon Intent"
CUT = "aicordon_api_cut"
CUT_NAME = "AI Cordon Intent, cut"
SANITIZERS = ("pisanitizer", "datafilter", "promptarmor")
ATTACKS = ("none", "direct", "combined")
# dataset file name -> (the key PIArena uses in its results.json, number of samples)
DATASETS = {
    "squad_v2": ("squad_v2", 200), "dolly_closed_qa": ("dolly_qa", 200),
    "dolly_information_extraction": ("dolly_ie", 200), "dolly_summarization": ("dolly_summ", 200),
    "nq_rag": ("nq_rag", 100), "msmarco_rag": ("msmarco_rag", 100),
    "hotpotqa_rag": ("hotpotqa_rag", 100), "hotpotqa_long": ("hotpotqa_long", 100),
    "qasper_long": ("qasper", 100), "gov_report_long": ("govreport", 100),
    "multi_news_long": ("multinews", 100),
    "passage_retrieval_en_long": ("passage_retrieval", 100), "lcc_long": ("lcc", 100),
}
DISPLAY = {"none": "No defense", "pisanitizer": "PISanitizer", "secalign": "SecAlign++",
           "datafilter": "DataFilter", "promptarmor": "PromptArmor",
           "datasentinel": "DataSentinel", "promptguard": "PromptGuard",
           "attentiontracker": "Attn.Tracker", "piguard": "PIGuard"}


def load_runs(results):
    runs = {}
    for ds, (_, n) in DATASETS.items():
        for at in ATTACKS:
            for df in ("none", OURS, CUT):
                f = results / "runs" / f"{ds}-{at}-{df}.jsonl"
                if not f.exists():
                    continue
                rows = [json.loads(line) for line in open(f, encoding="utf-8") if line.strip()]
                if len(rows) == n:
                    runs[(ds, at, df)] = rows
    return runs


def load_theirs():
    checkout = ROOT / "upstream" / "website" / "data" / "results.json"
    path = checkout if checkout.exists() else ROOT / "reference" / "piarena-results.json"
    rows = json.load(open(path))["results"]
    return {(r["dataset"], r["attack"], r["defense"]): (r["utility"], r["asr"])
            for r in rows if r["llm"] == LLM_THEIRS}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def wilson(k, n, z=1.96):
    """The observed rate and the half-width of its 95% Wilson interval, in percent."""
    if not n:
        return None, None
    p = k / n
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * p, 100 * half


def fmt(x):
    return "-" if x is None else f"{x:.1f}"


def table(out, head, rows, right_from=1):
    print("| " + " | ".join(head) + " |", file=out)
    print("|" + "|".join("---" if i < right_from else "---:" for i in range(len(head))) + "|",
          file=out)
    for r in rows:
        print("| " + " | ".join(r) + " |", file=out)
    print(file=out)


def build(results, out):
    runs = load_runs(results)
    theirs = load_theirs()
    util = {k: 100 * mean([r["utility"] for r in v]) for k, v in runs.items()}
    asr = {k: 100 * mean([float(r["asr"]) for r in v]) for k, v in runs.items()}
    done = [ds for ds in DATASETS
            if all((ds, at, df) in runs for at in ATTACKS for df in ("none", OURS))]
    missing = [ds for ds in DATASETS if ds not in done]
    versions = sorted({str(r["defense"].get("version")) for (_, _, df), v in runs.items()
                       if df == OURS for r in v})
    points = sorted({str(r["defense"].get("point")) for (_, _, df), v in runs.items()
                     if df == OURS for r in v})
    if len(versions) > 1:
        raise SystemExit(f"{results} mixes detector versions {versions}: "
                         "these numbers would describe no single detector")
    print(f"# {OURS_NAME} {', '.join(v.lstrip('v') for v in versions)} in PIArena\n", file=out)
    print(f"Datasets complete: {len(done)} of {len(DATASETS)}"
          + (f" (not yet: {', '.join(missing)})" if missing else "") + ".  ", file=out)
    print(f"Detector: {OURS_NAME} {', '.join(versions)}, operating point {', '.join(points)}.  ",
          file=out)
    print("Backend LLM and judge: Qwen/Qwen3-4B-Instruct-2507.\n", file=out)
    if not done:
        return

    print(f"### Defense board, {len(done)} datasets\n", file=out)
    board = []
    for df in sorted({k[2] for k in theirs}):
        def col(at, i):
            return mean([theirs.get((DATASETS[ds][0], at, df), (None, None))[i] for ds in done])
        board.append((DISPLAY.get(df, df) + (" (published)" if df == "none" else ""),
                      col("none", 0), col("direct", 1), col("combined", 1)))
    board.append((f"**{OURS_NAME}**", mean([util[(ds, "none", OURS)] for ds in done]),
                  mean([asr[(ds, "direct", OURS)] for ds in done]),
                  mean([asr[(ds, "combined", OURS)] for ds in done])))
    cut_done = [ds for ds in done if all((ds, at, CUT) in runs for at in ATTACKS)]
    if cut_done == done:
        board.append((f"**{CUT_NAME}**", mean([util[(ds, "none", CUT)] for ds in done]),
                      mean([asr[(ds, "direct", CUT)] for ds in done]),
                      mean([asr[(ds, "combined", CUT)] for ds in done])))
    board.append(("No defense (this run)", mean([util[(ds, "none", "none")] for ds in done]),
                  mean([asr[(ds, "direct", "none")] for ds in done]),
                  mean([asr[(ds, "combined", "none")] for ds in done])))
    board.sort(key=lambda r: mean([r[2], r[3]]))
    table(out, ["Defense", "Clean utility", "ASR direct", "ASR combined", "ASR mean"],
          [[name, fmt(cu), fmt(d), fmt(c), fmt(mean([d, c]))] for name, cu, d, c in board])
    print("Lower ASR is better, higher utility is better. Every row is the mean over the same "
          f"{len(done)} datasets. Published rows: PIArena `website/data/results.json`.\n",
          file=out)

    def by_convention(at, field):
        """PIArena's detection defenses answer a blocked document with a fixed warning, which
        scores no utility and no attack. Here the model is asked over an empty document
        instead; this recomputes the row the other way."""
        return mean([100 * mean([0.0 if r["defense"].get("detect_flag") else float(r[field])
                                 for r in runs[(ds, at, OURS)]]) for ds in done])

    cu, d_, c_ = (by_convention("none", "utility"), by_convention("direct", "asr"),
                  by_convention("combined", "asr"))
    print("A blocked document is answered here by the model over an empty document; PIArena's "
          "own detection defenses answer it with a fixed warning. Counted their way, the "
          f"{OURS_NAME} row reads: clean utility {fmt(cu)}, ASR direct {fmt(d_)}, "
          f"ASR combined {fmt(c_)}, mean {fmt(mean([d_, c_]))}.\n", file=out)

    if cut_done == done:
        print("### The cut variant: utility under attack\n", file=out)
        print(f"{CUT_NAME} cuts the fragments the service marks out of a flagged document and "
              "passes the rest to the model, as PIArena's sanitizers do; their published utility "
              "under attack is the comparison. The detector variant above drops the whole "
              "document instead.\n", file=out)
        rows = []
        for df in SANITIZERS:
            rows.append([DISPLAY.get(df, df)] + [
                fmt(mean([theirs.get((DATASETS[ds][0], at, df), (None, None))[i] for ds in done]))
                for at in ATTACKS[1:] for i in (0, 1)])
        rows.append([f"**{CUT_NAME}**"] + [fmt(mean([(util if i == 0 else asr)[(ds, at, CUT)]
                                                     for ds in done]))
                                           for at in ATTACKS[1:] for i in (0, 1)])
        rows.append(["No defense (this run)"] + [fmt(mean([(util if i == 0 else asr)[(ds, at, "none")]
                                                           for ds in done]))
                                                 for at in ATTACKS[1:] for i in (0, 1)])
        table(out, ["Defense", "Utility, direct", "ASR direct", "Utility, combined",
                    "ASR combined"], rows)
        flagged = [r for ds in done for at in ATTACKS for r in runs[(ds, at, CUT)]
                   if r["defense"].get("detect_flag")]
        dropped = sum(r["defense"].get("fallback") == "drop" for r in flagged)
        chars = [r["defense"].get("cut_chars") or 0 for r in flagged
                 if r["defense"].get("fallback") != "drop"]
        print(f"Flagged documents: {len(flagged)}; cut: {len(flagged) - dropped}, dropped for "
              f"want of a span: {dropped}. Characters cut per document: median "
              f"{sorted(chars)[len(chars) // 2] if chars else 0:,}.\n", file=out)
    elif cut_done:
        print(f"(cut variant: {len(cut_done)} of {len(done)} datasets complete, not shown)\n",
              file=out)

    print("### Pooled over samples\n", file=out)
    rows = []
    for at in ATTACKS[1:]:
        for df, name in ((OURS, OURS_NAME), ("none", "No defense (this run)")):
            flat = [r for ds in done for r in runs[(ds, at, df)]]
            k = sum(r["asr"] for r in flat)
            c, h = wilson(k, len(flat))
            rows.append([at, name, f"{k} / {len(flat)}", f"{c:.1f} ± {h:.1f}"])
    table(out, ["Attack", "Defense", "Attacks that succeeded", "ASR, %"], rows, right_from=2)
    clean = [r for ds in done for r in runs[(ds, "none", OURS)]]
    k = sum(bool(r["defense"].get("detect_flag")) for r in clean)
    c, h = wilson(k, len(clean))
    refused = sum(not r["defense"].get("scored", True)
                  for (_, _, df), v in runs.items() if df == OURS for r in v)
    print(f"Clean documents blocked: {k} / {len(clean)} ({c:.2f} ± {h:.2f} %). "
          f"Documents the API did not score (passed through as clean): {refused}.\n", file=out)

    print("### The pipeline check: no defense, this run / published\n", file=out)
    rows = []
    for ds in done:
        key = DATASETS[ds][0]
        row = [ds]
        for at in ATTACKS:
            row.append(f"{fmt(util[(ds, at, 'none')])} / "
                       f"{fmt(theirs.get((key, at, 'none'), (None, None))[0])}")
        for at in ATTACKS[1:]:
            row.append(f"{fmt(asr[(ds, at, 'none')])} / "
                       f"{fmt(theirs.get((key, at, 'none'), (None, None))[1])}")
        rows.append(row)
    table(out, ["Dataset", "Utility, clean", "Utility, direct", "Utility, combined",
                "ASR direct", "ASR combined"], rows)

    print(f"### {OURS_NAME} per dataset\n", file=out)
    rows = []
    for ds in done:
        row = [ds, fmt(util[(ds, "none", OURS)])]
        for at in ATTACKS:
            v = runs[(ds, at, OURS)]
            row.append(f"{sum(bool(r['defense'].get('detect_flag')) for r in v)} / {len(v)}")
        row += [fmt(asr[(ds, "direct", OURS)]), fmt(asr[(ds, "combined", OURS)])]
        rows.append(row)
    table(out, ["Dataset", "Clean utility", "Blocked, clean", "Blocked, direct",
                "Blocked, combined", "ASR direct", "ASR combined"], rows)


def cut(text, n=220):
    text = " ".join(str(text or "").split()).replace("|", "\\|")
    return text if len(text) <= n else text[:n - 1] + "…"


def build_misses(results, out):
    """Every case a reader would ask for first: what got through, and what was blocked in vain."""
    runs = load_runs(results)
    done = [ds for ds in DATASETS
            if all((ds, at, df) in runs for at in ATTACKS for df in ("none", OURS))]
    versions = sorted({str(r["defense"].get("version")) for (_, _, df), v in runs.items()
                       if df == OURS for r in v})
    print(f"# {OURS_NAME} {', '.join(v.lstrip('v') for v in versions)} in PIArena: "
          "the cases\n", file=out)
    print(f"Over the {len(done)} complete datasets. Each row is one sample; "
          "`python3 show.py <dataset> <attack> <idx>` prints the document, the detector's "
          "answer and the model's response.\n", file=out)
    for at in ATTACKS[1:]:
        got = [(ds, r) for ds in done for r in runs[(ds, at, OURS)] if r["asr"]]
        total = sum(len(runs[(ds, at, OURS)]) for ds in done)
        print(f"## Attack `{at}`: {len(got)} of {total} succeeded\n", file=out)
        if not got:
            continue
        table(out, ["Dataset", "idx", "Category", "Score", "Blocked", "At 1e-03",
                    "Injected instruction"],
              [[ds, str(r["idx"]), str(r["category"]),
                "-" if r["defense"].get("score") is None else f"{r['defense']['score']:.3f}",
                "yes" if r["defense"].get("detect_flag") else "no",
                "caught" if r["defense"].get("verdicts", {}).get("1e-03") else "missed",
                cut(r.get("injected_task"))] for ds, r in got], right_from=99)
    blocked = [(ds, r) for ds in done for r in runs[(ds, "none", OURS)]
               if r["defense"].get("detect_flag")]
    total = sum(len(runs[(ds, "none", OURS)]) for ds in done)
    print(f"## Clean documents blocked: {len(blocked)} of {total}\n", file=out)
    if blocked:
        table(out, ["Dataset", "idx", "Score", "Characters"],
              [[ds, str(r["idx"]), f"{r['defense']['score']:.3f}", f"{r['input_chars']:,}"]
               for ds, r in blocked], right_from=99)
    unscored = [(ds, at, r) for ds in done for at in ATTACKS for r in runs[(ds, at, OURS)]
                if not r["defense"].get("scored", True)]
    print(f"## Documents the detector did not score: {len(unscored)}\n", file=out)
    print("They are passed through as clean and count as such in every number.\n", file=out)
    if unscored:
        table(out, ["Dataset", "Attack", "idx", "Reason", "Characters"],
              [[ds, at, str(r["idx"]), str(r["defense"].get("reason")), f"{r['input_chars']:,}"]
               for ds, at, r in unscored], right_from=99)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=None,
                    help="results/intent-<version>; may be omitted while there is only one")
    ap.add_argument("--write", action="store_true",
                    help="also write <results>/table.md and <results>/cases.md")
    a = ap.parse_args()
    if a.results:
        results = pathlib.Path(a.results)
    else:
        held = sorted(p for p in (ROOT / "results").glob("intent-*") if p.is_dir())
        if len(held) != 1:
            raise SystemExit("--results is required, one of: "
                             + ", ".join(str(p.relative_to(ROOT)) for p in held))
        results = held[0]
    buf = io.StringIO()
    build(results, buf)
    sys.stdout.write(buf.getvalue())
    if a.write:
        (results / "table.md").write_text(buf.getvalue(), encoding="utf-8")
        cases = io.StringIO()
        build_misses(results, cases)
        (results / "cases.md").write_text(cases.getvalue(), encoding="utf-8")


if __name__ == "__main__":
    main()
