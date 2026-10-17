"""The detector under test, through the `aicordon` package -- the same client a user installs.

    intent            the AI Cordon API (key: AICORDON_API_KEY, or `aicordon login`)
    intent:<name>     another detector offered by the service

The client retries 429, 5xx and dropped connections itself. A document the service does not judge
(too short, 413 too large) comes back as `judged=False` with the reason; it is recorded and never
read as a clean verdict.
"""
from __future__ import annotations


class Intent:
    def __init__(self, detector: str = "intent", base_url: str | None = None,
                 timeout: float = 120.0, max_retries: int = 5) -> None:
        try:
            from aicordon import intent
            intent.load                                      # the lazy attribute exists from 1.3 on
        except (ImportError, AttributeError):
            raise SystemExit("needs aicordon >= 1.3 with the `intent` client: pip install -U aicordon")
        self.det = intent.load(base_url=base_url, detector=detector, timeout=timeout,
                               max_retries=max_retries, workers=1)
        self.det.available()
        self.name = detector

    @property
    def version(self) -> str:
        return self.det.version

    def describe(self) -> dict:
        return self.det.describe()

    def judge(self, text: str, doc_id: str) -> dict:
        """The record written for one prompt."""
        a = self.det.assess(text, doc_id=doc_id)
        r = {"id": doc_id, "judged": a.judged, "score": a.score, "flagged": bool(a.flagged),
             "version": a.version or ""}
        if a.verdicts:
            r["verdicts"] = dict(a.verdicts)
        if a.threshold is not None:
            r["threshold"] = a.threshold
        if a.reason:
            r["reason"] = a.reason
        return r


def make(spec: str, base_url: str | None = None) -> Intent:
    kind, _, rest = spec.partition(":")
    if kind != "intent":
        raise SystemExit(f"unknown detector: {spec} (intent, intent:<name>)")
    return Intent(detector=rest or "intent", base_url=base_url)
