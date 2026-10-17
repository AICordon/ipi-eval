"""Latency vs document length on Quadrat-IPI v1.0.2 (docs.jsonl, build_docs.py), one document at a time.

The detector is not public, so this harness times an ENGINE: a Python file next to a local build of the detector that
defines `Engine()` with `device` (the GPU's name), `about` (a line for the log) and `run(text)` -> dict with
`n_tokens`, `ms` (the time of the detector's model for this document), optionally `peak_gb`, `wall_ms`, `error`.
A warm-up pass over a spread of lengths first, so kernel compilation stays out of the numbers. Per document: chars,
tokens, ms, peak VRAM, carrier, label, length bin.

    python3 -u bench.py --engine <engine.py> --out results.jsonl          # resumes; Ctrl-C stops
    python3 bench.py --status --out results.jsonl
"""
import argparse
import json
import os

# before anything imports torch: without expandable segments the allocator fragments on long documents (pass 1 of the
# first local run lost 10 documents of 20k-32k tokens to OOM at 12 of 16 GB); the service sets the same
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
import importlib.util
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default=os.environ.get("LATENCY_ENGINE", ""), help="the engine file (see above)")
    ap.add_argument("--docs", default=str(HERE / "docs.jsonl"))
    ap.add_argument("--out", default=str(HERE / "results.jsonl"))
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="time only this many documents spread over the lengths "
                    "(a trial run; write it to its own --out)")
    ap.add_argument("--seed", type=int, default=0, help="order of this pass (each pass its own shuffle, so drift of "
                    "the card's clocks is not confounded with length)")
    a = ap.parse_args()
    D = [json.loads(l) for l in open(a.docs, encoding="utf-8")]
    if a.limit:
        D = sorted(D, key=lambda d: d["chars"])[:: max(1, len(D) // a.limit)][:a.limit]
    out = Path(a.out).resolve()
    done = {json.loads(l)["id"] for l in open(out)} if out.exists() else set()
    print(f"bench: {len(done)}/{len(D)} documents timed -> {out}", flush=True)
    if a.status:
        return
    todo = [d for d in D if d["id"] not in done]
    if not todo:
        return
    import random
    random.Random(a.seed).shuffle(todo)

    if not a.engine:
        sys.exit("--engine <engine.py> (or LATENCY_ENGINE): the file that runs the detector")
    spec = importlib.util.spec_from_file_location("engine", a.engine)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    E = mod.Engine()
    gpu, run = E.device, E.run
    print(f"GPU {gpu}; {E.about}", flush=True)

    short = sorted((d for d in D if not d.get("synthetic")), key=lambda d: d["chars"])
    for d in short[:: max(1, len(short) // 12)]:                      # warm-up across lengths
        run(d["text"])
    stop = []
    signal.signal(signal.SIGINT, lambda *_: stop.append(1))
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    t_all = time.time()
    with open(out, "a") as f:
        for k, d in enumerate(todo, 1):
            if stop:
                print(f"stopped at {len(done) + k - 1}/{len(D)}; continue: the same command", flush=True)
                sys.exit(130)
            r = run(d["text"])
            rec = dict(id=d["id"], gpu=gpu, chars=d["chars"], carrier=d["carrier"], y=d["y"], bin=d["bin"],
                       synthetic=bool(d.get("synthetic")), **r)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if k % 50 == 0 or k == len(todo) or d.get("synthetic"):
                print(f"  {len(done) + k}/{len(D)}  {d['id']}: {rec['n_tokens']} tokens {rec['ms']} ms "
                      f"peak {rec.get('peak_gb')} GB {rec.get('error') or ''}", flush=True)
    print(f"done in {time.time() - t_all:.0f} s", flush=True)


if __name__ == "__main__":
    main()
