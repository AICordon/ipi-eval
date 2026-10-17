"""PIArena defense backed by the live AI Cordon Intent API.

The detector is NOT local: every context goes to POST /api/v1/check on app.ai-cordon.com with a
Bearer key. The API answers with a score plus verdicts at three false-alarm budgets (1e-03, 1e-04,
1e-05) whose thresholds were set on AI Cordon's own clean text. The operating point is picked here
by name, never by fitting anything on PIArena.

Three things this adapter must get right, because each one silently flatters the numbers otherwise:

- a refusal is not a detection. An oversized document (413) or a too-short one is recorded as
  `not_scored` and, by default, passed through as clean. Counting refusals as blocks would lower
  ASR without the detector having seen anything.
- an error is not a detection either, and it is not a pass. The run stops.
- a long document is windowed: 20,000 characters with a
  2,000-character overlap, max over score and OR over each verdict. An injection landing on a seam
  would otherwise be halved.

There is no answer cache. Every context is scored live, every time: a cache can outlive a detector
release and mix two versions in one table without anyone noticing. Instead the expected version is
pinned (`version`, default v1.5.2) and the run stops on the first answer that carries another one.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from piarena.defenses.base import BaseDefense, register_defense

HOST = os.environ.get("PIARENA_AICORDON_HOST", "https://app.ai-cordon.com").rstrip("/")
WINDOW, STRIDE = 20000, 18000
#: 413 on a whole window: halve it and retry, down to this floor, then give up and say so
MIN_WINDOW = 2000


def _shift(part, offset):
    """Window offsets -> document offsets."""
    if offset and not part["refused"]:
        part = dict(part, spans=[[a + offset, b + offset] for a, b in part.get("spans", [])],
                    sentences=[[a + offset, b + offset, p] for a, b, p in part.get("sentences", [])])
    return part


def _merge(spans):
    """Sorted, overlaps joined (windows overlap, so a fragment can be marked twice)."""
    out = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


@register_defense
class AicordonApiDefense(BaseDefense):
    """Score the context through the live Intent API; drop it on detection."""

    name = "aicordon_api"
    DEFAULT_CONFIG = {
        "point": "1e-04",       # which of the API's operating points decides
        "timeout": 180,
        "attempts": 60,         # about an hour of outage tolerated
        "on_refusal": "pass",   # "pass" (honest default) or "error"
        "detector": "intent",
        "version": "v1.5.2",    # the API's detector version this run is allowed to see
    }
    ENDPOINT = "/api/v1/check"  # score and verdicts; the cut variant needs the spans too

    def __init__(self, config=None):
        env = {k: os.environ[f"PIARENA_AICORDON_{k.upper()}"]
               for k in self.DEFAULT_CONFIG
               if f"PIARENA_AICORDON_{k.upper()}" in os.environ}
        super().__init__({**env, **(config or {})})
        if self.config["point"] not in ("1e-03", "1e-04", "1e-05"):
            raise ValueError("point must be one of 1e-03, 1e-04, 1e-05")
        if self.config["on_refusal"] not in ("pass", "error"):
            raise ValueError("on_refusal must be 'pass' or 'error'")
        self.timeout = float(self.config["timeout"])
        self.attempts = int(self.config["attempts"])
        token = (os.environ.get("AICORDON_API_KEY") or "").strip()
        if not token:
            raise RuntimeError("AICORDON_API_KEY is not set; the API key is environment-only")
        self.headers = {"authorization": f"Bearer {token}",
                        "content-type": "application/json",
                        "user-agent": "piarena-aicordon-api"}
        self.lock = threading.Lock()
        self.stats = {"calls": 0, "refused": 0, "blocked": 0, "seen": 0}
        print(f"[aicordon_api] live API, point {self.config['point']}, "
              f"expected version {self.config['version']}", flush=True)

    # --- the API ------------------------------------------------------------------

    def _call(self, text):
        """One window. Returns {score, verdicts, refused}. Raises only when the host is lost."""
        body = json.dumps({"text": text, "detector": self.config["detector"]},
                          ensure_ascii=False).encode()
        attempt = -1
        while attempt < self.attempts - 1:
            attempt += 1
            try:
                req = urllib.request.Request(HOST + self.ENDPOINT, data=body,
                                             headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    answer = json.loads(r.read())
                with self.lock:
                    self.stats["calls"] += 1
                got = answer.get("version")
                if got != self.config["version"]:
                    raise RuntimeError(f"API answered with detector {got!r}, this run expects "
                                       f"{self.config['version']!r}; one table, one version")
                if answer.get("score") is None:
                    return {"score": None, "verdicts": {}, "refused": True,
                            "reason": answer.get("reason", "not_scored")}
                return {"score": float(answer["score"]), "verdicts": answer.get("verdicts", {}),
                        "refused": False, "reason": None,
                        # /detect only: the fragments the service marks, and every sentence's p
                        "spans": [list(sp) for sp in answer.get("spans") or []],
                        "sentences": [[int(x["span"][0]), int(x["span"][1]), float(x.get("p", 0))]
                                      for x in answer.get("sentences") or []]}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2)
                    attempt -= 1          # the key's concurrency cap is a queue, not a failure
                    continue
                if e.code == 413:
                    return {"score": None, "verdicts": {}, "refused": True, "reason": "too_large"}
                if e.code not in (502, 503, 504):
                    raise RuntimeError(
                        f"HTTP {e.code}: {e.read()[:200].decode('utf-8', 'replace')}")
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
                pass
            wait = min(60, 2 ** attempt * 2)
            if attempt >= 3:
                print(f"  [aicordon_api] retry {attempt + 1}/{self.attempts} in {wait}s",
                      flush=True)
            time.sleep(wait)
        raise RuntimeError(f"aicordon API gave no answer after {self.attempts} attempts")

    def _call_split(self, text):
        """A window the API refuses as too large is halved until it fits or the floor is reached."""
        out = self._call(text)
        if not (out["refused"] and out["reason"] == "too_large" and len(text) > MIN_WINDOW):
            return [out]
        half = len(text) // 2
        return self._call_split(text[:half]) + [
            _shift(p, half) for p in self._call_split(text[half:])]

    def _score(self, text):
        """The whole document: windows, folded by max over score and OR over each verdict."""
        starts = [0] if len(text) <= WINDOW else [
            i for i in range(0, len(text), STRIDE) if text[i:i + WINDOW].strip()]
        parts = []
        for start in starts:
            parts.extend(_shift(p, start) for p in self._call_split(text[start:start + WINDOW]))
        scored = [p for p in parts if not p["refused"]]
        verdicts = {}
        for p in scored:
            for k, v in p["verdicts"].items():
                verdicts[k] = verdicts.get(k, False) or bool(v)
        return {
            "chars": len(text),
            "windows": len(parts),
            "score": max((p["score"] for p in scored), default=None),
            "verdicts": verdicts,
            # a document counts as refused only when NO window came back with a verdict
            "refused": not scored,
            "reason": None if scored else (parts[0]["reason"] if parts else "empty"),
            "spans": _merge([sp for p in scored for sp in p.get("spans", [])]),
            "sentences": [x for p in scored for x in p.get("sentences", [])],
        }

    # --- the PIArena interface ----------------------------------------------------

    def execute(self, target_inst: str, context: str) -> dict:
        return self._judge(context)[0]

    def _judge(self, context):
        """(PIArena's result dict, the API row it was made from)."""
        if not isinstance(context, str):
            raise TypeError("aicordon_api expects a string context")
        row = self._score(context)
        with self.lock:
            self.stats["seen"] += 1
        if row["refused"]:
            with self.lock:
                self.stats["refused"] += 1
            if self.config["on_refusal"] == "error":
                raise RuntimeError(f"aicordon API did not score a context ({row['reason']}); "
                                   "set on_refusal=pass to continue")
            # Not scored is not detected. Say so in the record and let the context through.
            print(f"  [aicordon_api] not scored ({row['reason']}, {row['chars']} chars) "
                  f"-> passed through", flush=True)
            return {"detect_flag": False, "cleaned_context": context, "score": None,
                    "scored": False, "reason": row["reason"], "point": self.config["point"],
                    "version": self.config["version"]}, row
        flag = bool(row["verdicts"].get(self.config["point"]))
        with self.lock:
            self.stats["blocked"] += int(flag)
            if self.stats["seen"] % 25 == 0:
                s = self.stats
                print(f"  [aicordon_api] {s['seen']} contexts, blocked {s['blocked']}, "
                      f"refused {s['refused']}, api {s['calls']} calls",
                      flush=True)
        return {"detect_flag": flag, "cleaned_context": "" if flag else context,
                "score": row["score"], "scored": True, "point": self.config["point"],
                "verdicts": row["verdicts"], "version": self.config["version"]}, row


@register_defense
class AicordonApiCutDefense(AicordonApiDefense):
    """The same detector as a sanitizer: on detection, the fragments the service marks are cut
    out and the rest of the document goes on to the model.

    What is cut is exactly what the API lists as `spans`, nothing wider: this measures the
    service's own localisation. A flagged document with no span listed cannot be cut and is
    dropped, as the detector variant does; the record says so (`fallback`)."""

    name = "aicordon_api_cut"
    ENDPOINT = "/api/v1/detect"

    def execute(self, target_inst: str, context: str) -> dict:
        out, row = self._judge(context)
        if not out["detect_flag"]:
            return out
        spans = row.get("spans") or []
        if not spans:
            return {**out, "cleaned_context": "", "spans": [], "cut_chars": 0, "fallback": "drop",
                    "sentences": row.get("sentences", [])}
        kept = context
        for a, b in reversed(spans):
            kept = kept[:a] + kept[b:]
        with self.lock:
            self.stats["cut"] = self.stats.get("cut", 0) + 1
        return {**out, "cleaned_context": kept, "spans": spans,
                "cut_chars": len(context) - len(kept), "sentences": row.get("sentences", [])}
