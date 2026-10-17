"""docs.jsonl for the latency benchmark, from the public Quadrat-IPI v1.0.2 (pinned by sha256 in ipi-eval quadrat-full):
documents stratified by length in characters (PER_BIN per bin, half injected, carriers as they come), plus synthetic
long documents on a grid up to the reader's full window (Quadrat clean documents glued with blank lines) — those are
marked `synthetic` and stay out of any Quadrat statement.

    python3 build_docs.py [--quadrat <Quadrat-IPI v1.0.2>/data]     # -> docs.jsonl
"""
import argparse
import hashlib
import os
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHA256 = {"positives.jsonl": "153583fa465e40deca098c067213948d1e1509f469d4e85836f878cbdcc65a69",
          "negatives.jsonl": "745ea64400d758b146014ea73764d9fcf09bb02a695dba8139d43e92b11afeb8"}
EDGES = [0, 500, 1000, 2000, 3000, 5000, 7500, 10000, 15000, 21000]
PER_BIN = 100
SEED = 2112
SYN_GRID = (6, 8, 12, 16, 20, 24, 28, 32)          # thousand tokens
SYN_PER = 6                                      # 3 clean + 3 injected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quadrat", default=os.environ.get("QUADRAT_DATA", ""), help="<Quadrat-IPI v1.0.2>/data "
                    "(or QUADRAT_DATA); positives.jsonl and negatives.jsonl are checked against their sha256")
    a = ap.parse_args()
    if not a.quadrat:
        raise SystemExit("set --quadrat or QUADRAT_DATA to the data/ directory of Quadrat-IPI v1.0.2")
    q = Path(a.quadrat)
    rows = []
    for name, y in (("positives.jsonl", 1), ("negatives.jsonl", 0)):
        p = q / name
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h != SHA256[name]:
            raise SystemExit(f"{p}: sha256 {h}, expected {SHA256[name]} (Quadrat-IPI v1.0.2)")
        for l in open(p, encoding="utf-8"):
            r = json.loads(l)
            rows.append(dict(id=r["id"], y=y, carrier=r["host_type"], chars=len(r["text"]), text=r["text"]))
    rnd = random.Random(SEED)
    rnd.shuffle(rows)
    out = []
    for lo, hi in zip(EDGES, EDGES[1:]):
        b = [r for r in rows if lo <= r["chars"] < hi]
        pos = [r for r in b if r["y"]][:PER_BIN // 2]
        neg = [r for r in b if not r["y"]][:PER_BIN - len(pos)]
        out += [dict(r, bin=f"{lo}-{hi}") for r in pos + neg]
    # past Quadrat's longest (~4.6k tokens): a grid of target lengths, SYN_PER different documents each, Quadrat clean
    # documents glued with blank lines (~4.4 characters per token on this reader)
    # injected ones: one Quadrat injected document placed at a random position among the clean ones
    clean = [r["text"] for r in rows if not r["y"]]
    inj = [r["text"] for r in rows if r["y"]]
    for k_tok in SYN_GRID:
        for v in range(SYN_PER):
            y = v % 2
            chars = int(k_tok * 1000 * 4.4)
            parts, n = [], 0
            while n < chars:
                t = rnd.choice(clean)
                parts.append(t)
                n += len(t) + 2
            if y:
                parts.insert(rnd.randrange(len(parts) - 1), rnd.choice(inj))
            text = "\n\n".join(parts)
            if len(text) > chars:                      # trim at a document boundary near the target length
                cut = text.rfind("\n\n", 0, chars)
                text = text[:cut if cut > chars // 2 else chars]
            out.append(dict(id=f"synthetic-{k_tok}k-{v}", y=y, carrier="synthetic", chars=len(text), text=text,
                            bin=f"synthetic-{k_tok}k", synthetic=True))
    import statistics
    (HERE / "docs_meta.json").write_text(json.dumps({
        "quadrat_documents": len(rows), "quadrat_median_chars": statistics.median(r["chars"] for r in rows)}))
    with open(HERE / "docs.jsonl", "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(out)} documents -> {HERE / 'docs.jsonl'}")


if __name__ == "__main__":
    main()
