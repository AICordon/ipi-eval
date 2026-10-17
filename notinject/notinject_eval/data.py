"""NotInject at one fixed commit of the PIGuard repository.

NotInject (Li et al., "PIGuard", ACL 2025) holds 339 benign prompts, each built around one, two or
three words that injection detectors tend to fire on ("ignore", "bypass", ...): 113 prompts per
split. Every prompt is clean, so every alarm is a false one. The files are taken from the PIGuard
repository, the ones its `eval.py` reads, and each is checked against a pinned sha256.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = "leolee99/PIGuard"
REVISION = "1b5751e88bf7475acbedfc8eda795ce060307c84"
SPLITS = ("one", "two", "three")                               # trigger words per prompt
FILES = {
    "NotInject_one.json":   "69b535596d95102424e9c5946944feb4f2d596687eb8213f2ecad75478e5ffdd",
    "NotInject_two.json":   "6043d94e75b48d8e7682d25dc79eaf45359e1e561ce520e3b8fd5625a91060c6",
    "NotInject_three.json": "ef01eff0d761d2e34571b3fdbcec08c30cd93efe8d0e1a2eb5c2baeb1873b070",
}


@dataclass(frozen=True)
class Prompt:
    id: str
    text: str
    split: str
    category: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(data_dir: Path) -> None:
    """Download the pinned files into `data_dir`, skipping those already verified."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, want in FILES.items():
        path = data_dir / name
        if path.exists() and _sha256(path) == want:
            print(f"  {name}: present", flush=True)
            continue
        print(f"  {name}: downloading", flush=True)
        url = f"https://raw.githubusercontent.com/{REPO}/{REVISION}/datasets/{name}"
        req = urllib.request.Request(url, headers={"user-agent": "ipi-eval"})
        with urllib.request.urlopen(req) as r:
            body = r.read()
        digest = hashlib.sha256(body).hexdigest()
        if digest != want:
            raise SystemExit(f"{name}: sha256 {digest} does not match the pinned revision")
        path.write_bytes(body)


def prompts(data_dir: Path) -> list[Prompt]:
    out = []
    for split in SPLITS:
        path = data_dir / f"NotInject_{split}.json"
        if not path.exists():
            raise SystemExit(f"{path} is missing; run: python -m notinject_eval fetch")
        for k, r in enumerate(json.loads(path.read_text(encoding="utf-8"))):
            out.append(Prompt(f"{split}-{k:03d}", r["prompt"], split, r.get("category") or ""))
    return out
