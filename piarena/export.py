"""Turn PIArena's result files into the per-sample records this repository publishes.

PIArena writes one JSON per dataset/attack/defense with the full context of every sample inside.
The records here keep what is needed to check the numbers and to read a case - the verdicts of
the judge, the model's response, what the detector answered, the injected instruction - and
replace the documents, which come from third-party datasets, with their SHA-256. `show.py`
brings a document back from the PIArena checkout. Only complete runs are exported.

The records go to results/intent-<version>/runs/, the version being the one the detector
reported in the answers. A result directory that mixes versions is not exported at all.

Usage: python3 export.py [--src upstream] [--name intent-1.5.2] [--seed 42]
"""
import argparse
import hashlib
import json
import pathlib

from show import WRAP, piarena_utils

ROOT = pathlib.Path(__file__).resolve().parent
LLM_FILE = "Qwen-Qwen3-4B-Instruct-2507"
DATASETS = ("squad_v2", "dolly_closed_qa", "dolly_information_extraction", "dolly_summarization",
            "nq_rag", "msmarco_rag", "hotpotqa_rag", "hotpotqa_long", "qasper_long",
            "gov_report_long", "multi_news_long", "passage_retrieval_en_long", "lcc_long")
ATTACKS = ("none", "direct", "combined")
DEFENSES = ("none", "aicordon_api", "aicordon_api_cut")
DEFENSE_KEYS = ("detect_flag", "scored", "score", "verdicts", "point", "version", "reason",
                "spans", "cut_chars", "fallback", "sentences")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def given(attack, row, saved, inject):
    """The document the defense was given. PIArena keeps it in a side file, which a restarted
    run may rewrite with only the samples it still had to do; the attack is deterministic, so a
    missing document is rebuilt with PIArena's own code. A saved one must agree with the rebuild."""
    if attack == "none":
        return row["context"]
    built = inject(row["context"], WRAP[attack].format(task=row["injected_task"]), "random", 1)
    if saved is not None and saved != built:
        raise SystemExit("a saved injected document differs from the rebuilt one: "
                         "the checkout is not the one the run used")
    return built


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "upstream"))
    ap.add_argument("--name", default="intent-1.5.2",
                    help="the directory under upstream/results/evaluation_results")
    ap.add_argument("--seed", default="42")
    a = ap.parse_args()
    src = pathlib.Path(a.src)
    base = src / "results" / "evaluation_results" / a.name
    seen = set()
    for f in sorted(base.glob(f"*-aicordon_api*-{a.seed}.json")):
        seen |= {str(r.get("defense_result", {}).get("version"))
                 for r in json.load(open(f)).values()}
    if len(seen) != 1:
        raise SystemExit(f"{base} holds answers of {sorted(seen) or 'no detector at all'}: "
                         "one result directory, one detector version")
    version = seen.pop()
    out = ROOT / "results" / f"intent-{version.lstrip('v')}" / "runs"
    out.mkdir(parents=True, exist_ok=True)
    print(f"detector version {version}")
    inject = piarena_utils(src).inject
    rebuilt = 0
    done = skipped = 0
    for ds in DATASETS:
        n = len(json.load(open(src / "datasets" / f"{ds}.json")))
        for at in ATTACKS:
            for df in DEFENSES:
                stem = f"{ds}-{LLM_FILE}-{at}-{df}-{a.seed}.json"
                f = base / stem
                rows = json.load(open(f)) if f.exists() else {}
                if len(rows) < n:
                    if rows or df != "aicordon_api_cut":
                        skipped += 1
                        print(f"  incomplete, not exported: {ds} {at} {df} ({len(rows)}/{n})")
                    continue
                attack_file = base / "tmp_attack_results" / stem
                injected = json.load(open(attack_file)) if attack_file.exists() else {}
                target = out / f"{ds}-{at}-{df}.jsonl"
                with open(target, "w", encoding="utf-8") as fh:
                    for idx in sorted(rows, key=int):
                        r = rows[idx]
                        d = r.get("defense_result", {})
                        saved = injected.get(idx, {}).get("injected_context")
                        rebuilt += at != "none" and saved is None
                        seen = given(at, r, saved, inject)
                        rec = {
                            "idx": int(idx),
                            "category": r.get("category"),
                            "context_sha256": sha(r["context"]),
                            "input_sha256": sha(seen),     # what the defense was given
                            "input_chars": len(seen),
                            "injected_task": r["injected_task"] if at != "none" else None,
                            "utility": float(r["utility"]),
                            "asr": bool(r["asr"]),
                            "response": d.get("response"),
                        }
                        if df != "none":
                            rec["defense"] = {k: d[k] for k in DEFENSE_KEYS if k in d}
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                done += 1
    print(f"exported {done} runs to {out}, skipped {skipped} incomplete; "
          f"{rebuilt} injected documents were rebuilt, the rest read from PIArena's side files")


if __name__ == "__main__":
    main()
