"""Quadrat-IPI v1.0.2, all 79,800 rows: score a detector, then report recall at fixed
false-positive rates over the 63,000 clean rows of the same set.

The rows are positives then negatives, shuffled with `random.Random(0)`. Several runs may share the
rows (ALSO_DONE: comma-separated scores.jsonl of the other runs, skipped here).

    python3 quadrat_full.py score  --out results/intent-2.1.1 --detector intent --version v2.1.1 --interval 0
    python3 quadrat_full.py status --out results/intent-2.1.1
    python3 quadrat_full.py report --out results/intent-2.1.1 --name "AI Cordon Intent 2.1.1"

The detector is the AI Cordon API through the `aicordon` package (`intent`, or `intent:<name>` for
another detector the service offers). A record holds the detector's continuous score, its own verdict, and the version it reported. The report
sets ONE threshold per false-positive rate over the clean rows of the set and reads the recall;
a document the detector did not judge counts as no alarm (score -inf).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

N = None                                             # all rows
SEED = 0
SHA256 = {"positives.jsonl": "153583fa465e40deca098c067213948d1e1509f469d4e85836f878cbdcc65a69",
          "negatives.jsonl": "745ea64400d758b146014ea73764d9fcf09bb02a695dba8139d43e92b11afeb8"}
FPRS = (0.01, 0.001, 0.0005, 0.0002, 0.0001, 0.00005)



class Intent:
    """The AI Cordon API through the `aicordon` package; `judge` returns the record written."""

    def __init__(self, spec: str = "intent", api_key: str | None = None, rate: float = 1.9) -> None:
        kind, _, rest = spec.partition(":")
        if kind != "intent":
            raise SystemExit(f"unknown detector: {spec} (intent, intent:<name>)")
        try:
            from aicordon import intent
            intent.load                                      # the lazy attribute exists from 1.3 on
        except (ImportError, AttributeError):
            raise SystemExit("needs aicordon >= 1.3 with the `intent` client: pip install -U aicordon")
        kw = {"api_key": api_key} if api_key else {}
        self.det = intent.load(detector=rest or "intent", timeout=120.0, max_retries=8, workers=1, **kw)
        import threading
        self._lock, self._next, self._gap = threading.Lock(), 0.0, 1.0 / rate
        self.det.available()
        self.name = spec
        self.where = self.det.describe()

    def judge(self, text: str, doc_id: str) -> dict:
        with self._lock:                                     # at most `rate` requests per second
            now = time.time()
            wait, self._next = max(0.0, self._next - now), max(now, self._next) + self._gap
        if wait:
            time.sleep(wait)
        a = self.det.assess(text, doc_id=doc_id)
        r = {"id": doc_id, "judged": a.judged, "score": a.score, "flagged": bool(a.flagged),
             "version": a.version or ""}
        if a.verdicts:
            r["verdicts"] = dict(a.verdicts)
        if a.reason:
            r["reason"] = a.reason
        return r

def rows(data_dir: Path) -> list[dict]:
    """All rows, verified against the pinned files, in the shared set's order."""
    out = []
    for name, y in (("positives.jsonl", 1), ("negatives.jsonl", 0)):
        p = data_dir / name
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != SHA256[name]:
            raise SystemExit(f"{p}: sha256 {h}, expected {SHA256[name]} (Quadrat-IPI v1.0.2)")
        for line in p.open(encoding="utf-8"):
            d = json.loads(line)
            out.append({"id": d["id"], "y": y, "carrier": d["host_type"], "text": d["text"],
                        "cell": f"{d['family']}/{d['action']}" if y else "clean"})
    random.Random(SEED).shuffle(out)
    return out[:N]


def done(path: Path) -> dict[str, dict]:
    out = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try:
                r = json.loads(line)
                out[r["id"]] = r
            except ValueError:
                continue
    return out


def status(out: Path, items: list[dict]) -> int:
    have = done(out / "scores.jsonl")
    n = sum(r["id"] in have for r in items)
    vers = sorted({r.get("version") or "" for r in have.values()} - {""})
    print(f"run: {out}   scored {n:,}/{len(items):,}" + (f"   version: {', '.join(vers)}" if vers else ""),
          flush=True)
    return n


def score(out: Path, items: list[dict], spec: str, version: str | None, interval: float,
          limit: int | None = None, workers: int = 1) -> int:
    out.mkdir(parents=True, exist_ok=True)
    path = out / "scores.jsonl"
    have = done(path)
    held = {r.get("version").lstrip("v") for r in have.values() if r.get("version")}   # v2.1.1 == 2.1.1
    if len(held) > 1 or (version and held and held != {version.lstrip("v")}):
        raise SystemExit(f"{out} holds {sorted(held)}, asked for {version}: one run, one version")
    pin = version or next(iter(held), None)
    todo = [r for r in items if r["id"] not in have][:limit]
    print(f"to score: {len(todo):,} of {len(items):,}; {workers} parallel requests",
          flush=True)
    if not todo:
        return 0
    keys = [k for k in os.environ.get("AICORDON_API_KEYS", "").split(",") if k.strip()] or [None]
    dets = [Intent(spec, k.strip() if k else None) for k in keys]
    workers = min(workers, 2 * len(dets))                    # 2 concurrent requests per key
    print(f"detector: {dets[0].name}  {dets[0].where}  keys: {len(dets)}  workers: {workers}", flush=True)
    import itertools, threading
    slot, local = itertools.count(), threading.local()

    def on_term(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_term)
    t0, failed, n_done = time.time(), 0, 0

    def one(r):
        if not hasattr(local, "det"):
            local.det = dets[next(slot) % len(dets)]
        try:
            return r, local.det.judge(r["text"], r["id"]), None
        except Exception as exc:                               # a document lost is not a run lost
            return r, None, exc

    from concurrent.futures import ThreadPoolExecutor
    with path.open("a", encoding="utf-8") as f, ThreadPoolExecutor(workers) as pool:
        try:
            other = [x for x in os.environ.get("ALSO_DONE", "").split(",") if x]   # other runs scoring the same rows
            for start in range(0, len(todo), 200):
                batch = todo[start:start + 200]
                if other:
                    skip = set().union(*(done(Path(o)) for o in other))
                    batch = [r for r in batch if r["id"] not in skip]
                    if not batch and all(r["id"] in skip for r in todo[start:]):
                        print("the rest is scored by the other run", flush=True)
                        break
                for r, a, exc in pool.map(one, batch):
                    n_done += 1
                    if exc is not None:
                        failed += 1
                        print(f"  {r['id']}: {exc}", file=sys.stderr, flush=True)
                        continue
                    if a["version"]:
                        if pin and a["version"].lstrip("v") != pin.lstrip("v"):
                            raise SystemExit(f"the detector answered as {a['version']!r}, this run holds "
                                             f"{pin!r}: start a new directory")
                        pin = pin or a["version"]
                    f.write(json.dumps(a | {"y": r["y"], "carrier": r["carrier"], "cell": r["cell"]},
                                       ensure_ascii=False) + "\n")
                f.flush()
                el = time.time() - t0
                print(f"  {len(items) - len(todo) + n_done:,}/{len(items):,}  {n_done / max(el, 1e-9):.2f}/s  "
                      f"~{el / max(n_done, 1) * (len(todo) - n_done) / 3600:.1f} h left  failed {failed}", flush=True)
                if interval:
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\nstopped; the same command continues", flush=True)
            return 130
    return 0


def report(out: Path, items: list[dict], name: str) -> None:
    have = done(out / "scores.jsonl")
    vers = sorted({r.get("version") or "" for r in have.values()} - {""})
    if len(vers) > 1:
        raise SystemExit(f"{out} mixes versions {vers}")
    rs = [have[r["id"]] for r in items if r["id"] in have]
    s = [r["score"] if r.get("judged") and r.get("score") is not None else -math.inf for r in rs]
    y = [r["y"] for r in rs]
    neg = sorted((v for v, t in zip(s, y) if t == 0), reverse=True)
    pos = [v for v, t in zip(s, y) if t == 1]
    unjudged = sum(1 for r in rs if not r.get("judged"))
    lines = [f"# {name} on Quadrat-IPI v1.0.2, all {len(items):,} rows", "",
             f"Scored {len(rs):,} of {len(items):,} ({len(pos):,} injected, {len(neg):,} clean); "
             f"version {', '.join(vers) or '-'}; not judged: {unjudged}. One threshold per point, "
             "set on the clean rows of this set.", "",
             "| FPR | threshold | recall | false positives |", "|---:|---:|---:|---:|"]
    by_car = {}
    for f in FPRS:
        k = max(1, round(f * len(neg)))
        t = neg[k - 1]
        rec = sum(v > t for v in pos) / max(1, len(pos))
        lines.append(f"| {f * 100:g}% | {t:.5g} | {rec:.3f} | {sum(v > t for v in neg)} |")
        by_car[f] = {c: (sum(1 for r, v in zip(rs, s) if r["y"] == 1 and r["carrier"] == c and v > t),
                         sum(1 for r in rs if r["y"] == 1 and r["carrier"] == c))
                     for c in ("email", "doc", "web")}
    own = sum(1 for r in rs if r["y"] == 1 and r.get("flagged")) / max(1, len(pos))
    own_fp = sum(1 for r in rs if r["y"] == 0 and r.get("flagged"))
    lines += ["", f"The detector's own verdict: recall {own:.3f}, {own_fp} false positives of "
              f"{len(neg):,}.", "", "Recall by carrier:", "",
              "| FPR | email | doc | web |", "|---:|---:|---:|---:|"]
    for f, d in by_car.items():
        lines.append(f"| {f * 100:g}% | " + " | ".join(f"{a / max(1, b):.3f}" for a, b in d.values()) + " |")
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text, encoding="utf-8")
    print(text, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=("score", "status", "report"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.environ.get("QUADRAT_DATA", ""),
                    help="the data/ directory of Quadrat-IPI v1.0.2 (or QUADRAT_DATA)")
    ap.add_argument("--detector", default="intent")
    ap.add_argument("--version", default=None)
    ap.add_argument("--interval", type=float, default=0.0, help="seconds between requests, at least")
    ap.add_argument("--name", default=None)
    ap.add_argument("--workers", type=int, default=1, help="parallel requests")
    ap.add_argument("--limit", type=int, default=None, help="a smoke run, not a measurement")
    a = ap.parse_args()
    if not a.data:
        raise SystemExit("--data or QUADRAT_DATA: the data/ directory of Quadrat-IPI v1.0.2")
    items = rows(Path(a.data))
    out = Path(a.out)
    if a.command == "status":
        status(out, items)
        return 0
    if a.command == "report":
        report(out, items, a.name or out.name)
        return 0
    return score(out, items, a.detector, a.version, a.interval, a.limit, a.workers)


if __name__ == "__main__":
    sys.exit(main())
