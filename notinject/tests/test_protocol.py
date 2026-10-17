"""The PIGuard protocol on made-up answers: what is quiet, and what an unjudged prompt does."""
import unittest

from notinject_eval import report
from notinject_eval.data import Prompt

PROMPTS = [Prompt(f"{s}-{k}", "x", s, "c") for s in ("one", "two", "three") for k in range(2)]


def rec(id_, flagged, judged=True, v1e3=None):
    r = {"id": id_, "judged": judged, "score": 0.5 if judged else None, "flagged": flagged,
         "version": "v1.5.2"}
    if v1e3 is not None:
        r["verdicts"] = {"1e-03": v1e3, "1e-04": flagged}
    return r


class Protocol(unittest.TestCase):
    def test_quiet_share_per_split_and_the_mean_over_splits(self):
        have = {r["id"]: r for r in [rec("one-0", True), rec("one-1", False), rec("two-0", False),
                                     rec("two-1", False), rec("three-0", True), rec("three-1", True)]}
        res = report.evaluate(PROMPTS, have)
        self.assertEqual([res["splits"][s]["quiet"] for s in ("one", "two", "three")], [1, 2, 0])
        self.assertAlmostEqual(res["mean"], (0.5 + 1.0 + 0.0) / 3)

    def test_an_unjudged_prompt_is_quiet_and_counted(self):
        have = {r["id"]: r for r in [rec(p.id, False) for p in PROMPTS]}
        have["one-0"] = rec("one-0", True, judged=False)          # a flag without a judgment is void
        res = report.evaluate(PROMPTS, have)
        self.assertEqual(res["splits"]["one"]["quiet"], 2)
        self.assertEqual(res["splits"]["one"]["unjudged"], 1)

    def test_other_operating_points_are_read_from_the_verdicts(self):
        have = {r["id"]: r for r in [rec(p.id, False, v1e3=p.split == "one") for p in PROMPTS]}
        res = report.evaluate(PROMPTS, have)
        self.assertEqual(res["splits"]["one"]["quiet_at"]["1e-03"], 0)
        self.assertEqual(res["splits"]["one"]["quiet"], 2)


if __name__ == "__main__":
    unittest.main()
