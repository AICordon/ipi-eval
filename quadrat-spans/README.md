# Quadrat-IPI — where the injection is

> **AI Cordon Intent [2.1](results/intent-2.1.1/) points at the injection in 94.3% of injected documents.** When it flags a document, the part it marks overlaps the inserted text by 0.81 (IoU), and 84.4% of flagged documents are located at IoU ≥ 0.5.

Catching an injection is half the job: a user who is told "this document is attacked" also needs to
know which part to remove. Every injected row of
[Quadrat-IPI](https://huggingface.co/datasets/mihailgribov/quadrat-ipi) records the exact characters
that were inserted. This directory sends the 16,800 injected rows of v1.0.2 to a detector and
compares the part it marks with the inserted one, character by character.

Quadrat-IPI is built by the same author as the AI Cordon detectors. Read the numbers here with
that in mind.

## Result: AI Cordon Intent 2.1

| rows | documents | flagged | found | IoU | precision | recall | located, IoU ≥ 0.5 | located, IoU ≥ 0.75 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all injected | 16,800 | 94.4% | 94.3% | 0.767 | 90.6% | 79.4% | 79.6% | 64.1% |
| flagged only | 15,852 | 100% | 99.9% | 0.813 | 90.6% | 82.2% | 84.4% | 68.0% |

By carrier, all injected rows:

| carrier | documents | found | IoU | located, IoU ≥ 0.5 |
|---|---:|---:|---:|---:|
| email | 5,984 | 90.2% | 0.715 | 75.6% |
| document | 5,765 | 97.7% | 0.806 | 83.6% |
| web page | 4,585 | 95.4% | 0.787 | 79.9% |

What is marked is precise (nine in ten marked characters are the injection); what is missed is
mostly the edge of a long injection, not the injection itself: a flagged document whose mark misses
the inserted text entirely is one in a thousand.

Version v2.1.1, 16 October 2026, all rows through the live AI Cordon API, at the service's own
verdict. The breakdown by injection family and the curve for a stricter threshold are in
`results/intent-2.1.1/report.md`; every row's answer in `results/intent-2.1.1/scores.jsonl`.

## The test

- **Data.** `positives.jsonl` of Quadrat-IPI v1.0.2, checked against a pinned sha256 before use; the
  inserted characters are its `inj_span`.
- **Input.** One document per request, as the set writes it; the detector returns its verdict and,
  for a flagged document, the spans it holds responsible.
- **Measures**, at the character level. A document that is not flagged predicts nothing.
  - *found*: the marked part touches the injection;
  - *IoU*: characters in both / characters in either, per document, averaged;
  - *precision* / *recall*: share of marked characters that are the injection / share of the
    injection that is marked, pooled over documents;
  - *located*: flagged and IoU at or above 0.5 (or 0.75).
- **Stricter threshold.** Raising the bar on the score only drops documents, so the report also shows
  what is found and located at each threshold above the service's own, with the false alarms at that
  threshold counted on the 63,000 clean rows of the [whole-set run](../quadrat-full/).

## Run it

```sh
export QUADRAT_DATA=<Quadrat-IPI v1.0.2>/data     # the set, from Hugging Face
export AICORDON_API_KEY=aig_...                    # or AICORDON_API_KEYS=k1,k2 to spread the load
./run.sh --status                                  # what is scored, counted from results on disk
./run.sh                                           # score what is missing, then write the report
```

`VERSION` names the detector version the run expects (default v2.1.1); the run stops on the first
answer that carries another one. Ctrl-C stops it and the same command continues.
