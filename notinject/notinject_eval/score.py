"""Scoring: one request per prompt, each answer appended to `scores.jsonl` the moment it arrives.

The state is read back from that file, so a stopped run continues where it stopped: ids already on
disk are not asked again. Ctrl-C is an ordinary stop -- requests in flight finish and are written.

A run directory holds the answers of ONE detector version. The service can be released in the
middle of a run; the pin stops the run on the first answer that carries another version, and that
answer is not written.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .data import Prompt

SCORES = "scores.jsonl"


class VersionMismatch(RuntimeError):
    """An answer came from a detector version other than the one this run holds."""


class Pin:
    """The one detector version a run may see; unset, it takes the first it meets."""

    def __init__(self, version: str | None = None):
        self.version = version or None
        self._lock = threading.Lock()

    def check(self, got: str | None) -> None:
        if not got:
            return
        with self._lock:
            if self.version is None:
                self.version = got
            elif got.lstrip("v") != self.version.lstrip("v"):   # one service writes v2.1.1, another 2.1.1
                raise VersionMismatch(
                    f"the detector answered as {got!r}, this run holds {self.version!r}: "
                    f"one run directory, one version. Start a new directory for {got!r}")


class Pace:
    """At most `rate` requests per second across all threads: the service limits each key (2/s at
    the time of writing), and a request it turns away costs a retry with backoff."""

    def __init__(self, rate: float | None):
        self.gap = 1.0 / rate if rate and rate > 0 else 0.0
        self.next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        if not self.gap:
            return
        with self._lock:
            now = time.monotonic()
            at = max(now, self.next)
            self.next = at + self.gap
        if at > now:
            time.sleep(at - now)


def load(out_dir: Path) -> dict[str, dict]:
    """The records on disk, by id; a torn last line is skipped."""
    path = Path(out_dir) / SCORES
    have: dict[str, dict] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if isinstance(r, dict) and "id" in r:
                    have[r["id"]] = r
    return have


def versions(have: dict[str, dict]) -> set[str]:
    return {r.get("version") or "" for r in have.values()} - {""}


def status(prompts: list[Prompt], have: dict[str, dict]) -> list[tuple[str, int, int, int]]:
    """(split, on disk, total, not judged) -- from the result on disk."""
    out = []
    for split in ("one", "two", "three"):
        docs = [p for p in prompts if p.split == split]
        on = [have[p.id] for p in docs if p.id in have]
        out.append((f"{split} word{'s' if split != 'one' else ''}", len(on), len(docs),
                    sum(not r.get("judged") for r in on)))
    return out


def run(items: list[Prompt], det, out_dir: Path, workers: int = 4, pin: Pin | None = None,
        limit: int | None = None, every: int = 50, rate: float | None = None) -> tuple[int, int, bool]:
    """Score what is not on disk yet. Returns (written, failed, stopped).

    A failed request is not written, so the next run asks it again. Raises VersionMismatch."""
    pin, pace = pin or Pin(), Pace(rate)
    out_dir.mkdir(parents=True, exist_ok=True)
    have = load(out_dir)
    todo = [e for e in items if e.id not in have]
    if limit:
        todo = todo[:limit]
    print(f"{len(have):,}/{len(items):,} on disk, {len(todo):,} to ask, {workers} at a time"
          + (f", at most {rate:g}/s" if rate else ""), flush=True)
    if not todo:
        return 0, 0, False

    stop, lock = threading.Event(), threading.Lock()
    n = {"written": 0, "failed": 0}
    mismatch: list[VersionMismatch] = []
    t0 = time.time()

    def one(e: Prompt) -> None:
        if stop.is_set():
            return
        pace.wait()
        if stop.is_set():
            return
        try:
            rec = det.judge(e.text, e.id)
            pin.check(rec.get("version"))
        except VersionMismatch as exc:
            mismatch.append(exc)
            stop.set()
            return
        except Exception as exc:                             # noqa: BLE001 - asked again next run
            with lock:
                n["failed"] += 1
                print(f"  {e.id}: {exc}", flush=True)
            return
        with lock:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n["written"] += 1
            k = n["written"]
            if k % every == 0 or k == len(todo):
                rate = k / max(1e-9, time.time() - t0)
                left = (len(todo) - k) / max(1e-9, rate)
                print(f"  {len(have) + k:,}/{len(items):,}  {rate:.1f}/s  ~{left / 60:.0f} min left"
                      f"  failed {n['failed']}", flush=True)

    with (out_dir / SCORES).open("a", encoding="utf-8") as fh, ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(one, e) for e in todo]
        try:
            for f in futures:
                while not f.done():
                    time.sleep(0.2)                          # a plain wait keeps Ctrl-C deliverable
        except KeyboardInterrupt:
            stop.set()
            print("\nstopping after the requests in flight...", flush=True)
            for f in futures:
                f.cancel()
    if mismatch:
        raise mismatch[0]
    return n["written"], n["failed"], stop.is_set()
