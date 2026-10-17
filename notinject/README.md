# NotInject — does the detector fire on harmless text?

> **AI Cordon Intent [2.1](results/intent-2.1.1/) stays quiet on 82.3% of harmless prompts.** Intent [1.5.2](results/intent-1.5.2/): 88.2%.

**Versions:** [2.1](#result-ai-cordon-intent-21) · [1.5.2](#result-ai-cordon-intent-152)

[NotInject](https://huggingface.co/datasets/leolee99/NotInject) is the over-defense test of
[PIGuard](https://github.com/leolee99/PIGuard) (Li et al., ACL 2025): 339 benign prompts, each
built around one, two or three words that injection detectors tend to fire on — *ignore*,
*bypass*, *override* and the like. Nothing in the set is an attack, so every alarm is a false one.
This directory runs an AI Cordon detector on it through the public API with the `aicordon` package.

## Result: AI Cordon Intent 2.1

**Over-defense accuracy 82.3%**, the share of prompts that raise no alarm, averaged over the three
splits as PIGuard reports it. Higher is better.

| trigger words | prompts | quiet | not judged |
|---|---:|---:|---:|
| one | 113 | 86.7% ± 6.3 | 0 |
| two | 113 | 94.7% ± 4.3 | 0 |
| three | 113 | 65.5% ± 8.6 | 0 |
| **all** | **339** | **82.3% ± 4.1** | 0 |

By PIGuard's four topics, at the default point: common queries 89.7%, multilingual 85.7%, technique
queries 66.7%, virtual creation 85.7%. NotInject's prompts are requests addressed to an assistant.
Intent reads documents, and inside a document a request that tells the model what to do is what it
is built to flag; most of its alarms here are of that kind.

The live AI Cordon API, version v2.1.1, 12 October 2026. The answer to every prompt is in
`results/intent-2.1.1/scores.jsonl`, the full report in `results/intent-2.1.1/report.md`.

## Result: AI Cordon Intent 1.5.2

**Over-defense accuracy 88.2%**, the share of prompts that raise no alarm, averaged over the three
splits as PIGuard reports it. Higher is better.

| trigger words | prompts | quiet | not judged |
|---|---:|---:|---:|
| one | 113 | 92.9% ± 4.9 | 16 |
| two | 113 | 95.6% ± 4.0 | 8 |
| three | 113 | 76.1% ± 7.8 | 4 |
| **all** | **339** | **88.2% ± 3.4** | 28 |

The same prompts at every operating point the service publishes. The default is `1e-04`; a
stricter point trades recall for fewer alarms:

| operating point | one | two | three | mean |
|---|---:|---:|---:|---:|
| 1e-03 | 85.0% | 91.2% | 72.6% | 82.9% |
| **1e-04** (default) | **92.9%** | **95.6%** | **76.1%** | **88.2%** |
| 1e-05 | 95.6% | 97.3% | 84.1% | 92.3% |

By PIGuard's four topics, at the default point: common queries 92.9%, multilingual 95.2%,
technique queries 82.8%, virtual creation 71.4%.

NotInject is not in Intent 1.5.2's training or calibration data in any form. Version 1.5.2 was
chosen among 12 candidate builds on four public benchmarks, this one among them, which is a mild
fit to the test.

The live AI Cordon API, version v1.5.2, 30 September 2026. ± is the half-width of the 95% Wilson
interval. The answer to every prompt is in `results/intent-1.5.2/scores.jsonl`, the full report
in `results/intent-1.5.2/report.md`.

## The test

- **Data.** The three files PIGuard's `eval.py` reads, `datasets/NotInject_{one,two,three}.json`
  at commit `1b5751e8` of `leolee99/PIGuard`, each checked against a pinned sha256.
- **Input.** One prompt per request, as the file writes it.
- **Verdict.** The detector's own decision at the operating point it serves its users. Nothing is
  tuned on NotInject; the other operating points are printed beside it, not chosen among.
- **Metric.** The share of prompts with no alarm, per split, and their mean.
- **Not judged.** A prompt too short for the detector to judge gets no verdict, which a user of
  the service sees as no alarm; it counts as quiet here and each table says how many there were.
  28 of the 339 prompts are that short.

## Run it

Python 3.10+ and `aicordon >= 1.3`. An API key from <https://app.ai-cordon.com>:
`AICORDON_API_KEY`, `aicordon login`, or a line in `./.env`.

```sh
./run.sh --status          # what is scored, counted from results/<run>/scores.jsonl
./run.sh                   # fetch, score what is missing, write the report
```

339 requests, about three minutes. Ctrl-C is an ordinary stop and the same command continues;
the run pins the detector version (`VERSION=v1.5.2` by default) and stops on the first answer of
another one. By hand:

```sh
python -m notinject_eval fetch
python -m notinject_eval score --out results/intent-1.5.2 --version v1.5.2
python -m notinject_eval report --out results/intent-1.5.2 --name "AI Cordon Intent 1.5.2"
python -m unittest discover tests
```

## Credit

Cite PIGuard with any number from here: Li et al., *PIGuard: Prompt Injection Guardrail via
Mitigating Overdefense for Free*, ACL 2025. The data is theirs and is fetched from their
repository, not redistributed here.
