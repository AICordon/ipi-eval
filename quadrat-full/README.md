# Quadrat-IPI — all 79,800 rows

> **AI Cordon Intent [2.1](results/intent-2.1.1/) finds 96.4% of injections at 1 false alarm per 1,000 clean documents.** Intent [1.5.2](results/intent-1.5.2/): 81.2%.

**Versions:** [2.1](#result-ai-cordon-intent-21) · [1.5.2](#result-ai-cordon-intent-152)

[Quadrat-IPI](https://huggingface.co/datasets/mihailgribov/quadrat-ipi) is a public set of
indirect prompt injections placed inside real carriers — emails, documents and web pages — next to
clean documents of the same kinds. This directory scores a detector on the whole set, v1.0.2
(16,800 injected rows, 63,000 clean), and reports recall at fixed false-alarm rates set on the set's
own clean rows.

Quadrat-IPI is built by the same author as the AI Cordon detectors. Read the numbers here with
that in mind; the other benchmarks in this repository are third-party.

## Result: AI Cordon Intent 2.1

| false-alarm rate | threshold | recall | false alarms of 63,000 |
|---:|---:|---:|---:|
| 1% | 0.0714 | **99.4%** | 583 |
| 0.1% | 0.890 | **96.4%** | 44 |
| 0.05% | 0.933 | **95.4%** | 24 |
| 0.02% | 0.977 | **94.0%** | 12 |

At the service's own verdict, with no threshold set on this data: recall **94.3%**, 14 false alarms
in 63,000.

Recall by carrier:

| false-alarm rate | email | document | web page |
|---:|---:|---:|---:|
| 1% | 98.8% | 99.8% | 99.6% |
| 0.1% | 93.1% | 98.9% | 97.4% |
| 0.05% | 91.8% | 98.3% | 96.5% |
| 0.02% | 89.7% | 97.5% | 95.1% |

Version v2.1.1, 12 October 2026. 58,930 rows through the live AI Cordon API, 20,870 through the same
build on our own card of the same model; on rows scored both ways the verdicts agree. Every row's
answer, with where it came from, is in `results/intent-2.1.1/scores.jsonl`; the full report in
`results/intent-2.1.1/report.md`.

## Result: AI Cordon Intent 1.5.2

| false-alarm rate | 1% | 0.1% | 0.05% | 0.02% |
|---|---:|---:|---:|---:|
| recall | 89.8% | 81.2% | 78.4% | 72.6% |

At its own verdict: recall 79.3%, 37 false alarms in 63,000. Version v1.5.2, September 2026, the
same way (`results/intent-1.5.2/`).

## The test

- **Data.** `positives.jsonl` and `negatives.jsonl` of Quadrat-IPI v1.0.2, each checked against a
  pinned sha256 before use.
- **Input.** One document per request, as the set writes it.
- **Thresholds.** One per false-alarm rate, set on the 63,000 clean rows: a row counts as caught when
  its score is strictly above the threshold. The detector's own verdict is reported beside it.
- **Not judged.** A document the detector refuses counts as no alarm (score −∞); the report says how
  many there were (one, for 2.1).

## Run it

```sh
export QUADRAT_DATA=<Quadrat-IPI v1.0.2>/data     # the set, from Hugging Face
export AICORDON_API_KEY=aig_...                    # or AICORDON_API_KEYS=k1,k2 to spread the load
./run.sh --status                                  # what is scored, counted from results on disk
./run.sh                                           # score what is missing, then write the report
```

`VERSION` names the detector version the run expects (default v2.1.1); the run stops on the first
answer that carries another one. A full run is about 80,000 requests; Ctrl-C stops it and the same
command continues.
