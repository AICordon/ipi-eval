"""    python -m llmail_eval fetch                            download the pinned dataset files
    python -m llmail_eval score --out DIR                 ask the detector, continue where it stopped
                        [--version v1.5.2]               stop if the detector answers as another
    python -m llmail_eval status --out DIR                what is scored, counted from the result
    python -m llmail_eval report --out DIR --name NAME    Table 3 with the detector's row
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
from pathlib import Path

from . import data, report, score

HERE = Path(__file__).resolve().parent.parent


def _print_status(out: Path, emails: list[data.Email]) -> None:
    have = score.load(out)
    seen = sorted(score.versions(have))
    print(f"run: {out}" + (f"   detector version: {', '.join(seen)}" if seen else "")
          + ("   MIXED VERSIONS" if len(seen) > 1 else ""), flush=True)
    for name, on, total, unjudged in score.status(emails, have):
        left = total - on
        state = "complete" if not left else f"{left:,} left"
        extra = f", {unjudged} not judged" if unjudged else ""
        print(f"  {name:<8} {on:>7,} / {total:<7,} {state}{extra}", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="llmail_eval", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("fetch", "score", "status", "report"))
    ap.add_argument("--out", type=Path, help="the run directory, for example results/intent-1.5.2")
    ap.add_argument("--data", type=Path, default=HERE / "data", help="where the dataset files live")
    ap.add_argument("--detector", default="intent", help="intent | intent:<name>")
    ap.add_argument("--base-url", default=None, help="the API root, if not the package default")
    ap.add_argument("--workers", type=int, default=2,
                    help="requests in flight (the service allows 2 at a time per key)")
    ap.add_argument("--rate", type=float, default=2.0,
                    help="at most this many requests per second (the service limits each key; 0: no limit)")
    ap.add_argument("--limit", type=int, default=None,
                    help="score at most this many emails (a smoke run, not a measurement)")
    ap.add_argument("--version", default=None,
                    help="the detector version this run expects, for example v1.5.2")
    ap.add_argument("--name", default=None, help="the row label in the report")
    a = ap.parse_args(argv)

    if a.command == "fetch":
        data.fetch(a.data)
        print(f"attacks: {len(data.attacks(a.data)):,}, benign: {len(data.benign(a.data))}")
        return 0

    if not a.out:
        raise SystemExit("--out is required: the run directory, for example results/intent-1.5.2")
    emails = data.emails(a.data)

    if a.command == "status":
        _print_status(a.out, emails)
        return 0

    if a.command == "report":
        res = report.evaluate(emails, score.load(a.out))
        text = report.markdown(a.name or a.out.name, res)
        (a.out / "report.md").write_text(text, encoding="utf-8")
        (a.out / "numbers.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(text)
        print(f"written: {a.out / 'report.md'}, {a.out / 'numbers.json'}", file=sys.stderr)
        return 0

    # score. INT and TERM both stop it the ordinary way, even when started without a terminal.
    signal.signal(signal.SIGINT, signal.default_int_handler)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    held = score.versions(score.load(a.out))
    held = {v.lstrip("v") for v in held}                # v2.1.1 and 2.1.1 are one version
    if len(held) > 1:
        raise SystemExit(f"{a.out} already holds answers of {', '.join(sorted(held))}: "
                         "one run directory, one version")
    if a.version and held and held != {a.version.lstrip("v")}:
        raise SystemExit(f"{a.out} holds answers of {', '.join(held)}, asked for {a.version}: "
                         "start a new run directory for the new version")
    if a.limit:
        print(f"--limit {a.limit}: a smoke run, not a measurement", flush=True)
    from .detector import make
    det = make(a.detector, base_url=a.base_url)
    for k, v in det.describe().items():
        print(f"  {k}: {v}", flush=True)
    try:
        written, failed, stopped = score.run(emails, det, a.out, workers=a.workers,
                                             pin=score.Pin(a.version or next(iter(held), None)),
                                             limit=a.limit, rate=a.rate)
    except score.VersionMismatch as exc:
        print(f"\nstopped: {exc}", flush=True)
        _print_status(a.out, emails)
        return 3
    print(f"\nwritten {written:,}, failed {failed:,}; service version: {det.version}", flush=True)
    _print_status(a.out, emails)
    if stopped:
        return 130
    return 1 if failed else 0
