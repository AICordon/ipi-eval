"""The LLMail-Inject release at one fixed commit, and the two sides of Table 3 read from it.

Nothing is bundled here: `fetch` downloads the files from Hugging Face and checks each against a
pinned sha256 before it is used.

- Attacks: every distinct email that made the assistant actually call its `send_email` tool
  (`reason: "api_triggered"` in the labelled files). It is the only part of the release labelled by
  what happened rather than by an LLM annotator. The files key entries by the full email text, so a
  text is one attack however many times it was sent; a text sent in both phases counts in both.
- Benign: the 203 synthetic business emails the authors released for false-alarm testing, all 203
  as the file holds them (160 distinct texts).
"""
from __future__ import annotations

import hashlib
import json
import random
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = "microsoft/llmail-inject-challenge"
REVISION = "1063bdf01ec8762b812d5e06ee768a06faa5a6f7"          # dataset commit of 2025-05-16
FILES = {
    "labelled_unique_submissions_phase1.json":
        "691dfa1595d2bd0e731069f233bd5448f7af1c0ebd9732bc6f12dd6cee446586",
    "labelled_unique_submissions_phase2.json":
        "f89af984e345430c3b357903890e30867bf4676f4ef10c138cc7bad218e890b8",
    "emails_for_fp_tests.json":
        "4ddd950b5dbaa8548f5597c886d8e09a051ba07f80a9291fdcca9c2397d22abe",
}
PHASES = (1, 2)


@dataclass(frozen=True)
class Email:
    id: str
    text: str
    label: int                                               # 1 an attack, 0 a benign email
    phases: tuple[int, ...] = ()                             # attacks only


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(data_dir: Path) -> None:
    """Download the pinned files into `data_dir`, skipping those already verified."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, want in FILES.items():
        path = data_dir / name
        if path.exists() and _sha256(path) == want:
            print(f"  {name}: present", flush=True)
            continue
        print(f"  {name}: downloading", flush=True)
        url = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/data/{name}"
        part = path.with_name(name + ".part")
        req = urllib.request.Request(url, headers={"user-agent": "ipi-eval"})
        with urllib.request.urlopen(req) as r, part.open("wb") as f:
            total, got, shown = int(r.headers.get("content-length") or 0), 0, 0
            while chunk := r.read(1 << 20):
                f.write(chunk)
                got += len(chunk)
                if total > (64 << 20) and got * 10 // total > shown:
                    shown = got * 10 // total
                    print(f"    {got >> 20}/{total >> 20} MiB", flush=True)
        digest = _sha256(part)
        if digest != want:
            part.unlink()
            raise SystemExit(f"{name}: sha256 {digest} does not match the pinned revision")
        part.rename(path)


def _read(data_dir: Path, name: str):
    path = data_dir / name
    if not path.exists():
        raise SystemExit(f"{path} is missing; run: python -m llmail_eval fetch")
    return json.loads(path.read_text(encoding="utf-8"))


def attack_id(text: str) -> str:
    return "a-" + hashlib.sha1(text.encode()).hexdigest()[:16]


def attacks(data_dir: Path) -> list[Email]:
    phases: dict[str, list[int]] = {}
    for phase in PHASES:
        for text, label in _read(data_dir, f"labelled_unique_submissions_phase{phase}.json").items():
            if label.get("reason") == "api_triggered":
                phases.setdefault(text, []).append(phase)
    return sorted((Email(attack_id(t), t, 1, tuple(p)) for t, p in phases.items()),
                  key=lambda e: e.id)


def benign(data_dir: Path) -> list[Email]:
    return [Email(f"n-{k:03d}", t, 0)
            for k, t in enumerate(_read(data_dir, "emails_for_fp_tests.json"))]


def emails(data_dir: Path) -> list[Email]:
    """Benign first: the threshold depends on them. Attacks shuffled with a fixed seed, so a run
    stopped halfway covers both phases in proportion."""
    shuffled = attacks(data_dir)
    random.Random(0).shuffle(shuffled)
    return benign(data_dir) + shuffled
