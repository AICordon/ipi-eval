# PIArena — the detector as a defense

> **With AI Cordon Intent [1.5.2](results/intent-1.5.2/) in front of the model, 2.3% of attacks succeed (63.6% with no defense), and the assistant keeps 74.5% of its usefulness (74.7% with no defense).** Intent 2.1 is not measured yet.

AI Cordon Intent measured as a defense inside [PIArena](https://github.com/sleeepeer/PIArena),
by PIArena's own loop, next to the defenses PIArena publishes.

PIArena (ACL 2026, [paper](https://arxiv.org/abs/2604.08499),
[leaderboard](https://piarena.vercel.app/#/leaderboard)) is a platform for prompt-injection
evaluation. A defense is placed between a document and a model: the document may carry an
injected instruction, the model answers the user's question over it, and a judge decides whether
the model did what the injection asked (attack success rate, ASR) and whether it still answered
the user (utility). This repository adds one defense to that loop - the live AI Cordon Intent API
- and changes nothing else: the datasets, the attacks, the backend model, the judge and the
metrics are PIArena's, at a pinned commit.

## Result: AI Cordon Intent 1.5.2

![Defenses in PIArena: attack success under the direct and the combined attack, and utility on clean documents](results/intent-1.5.2/figures/board.svg)

| Defense | Clean utility | ASR direct | ASR combined | ASR mean |
|---|---:|---:|---:|---:|
| Attn.Tracker | 15.3 | 0.0 | 0.0 | 0.0 |
| **AI Cordon Intent 1.5.2** | **74.5** | **4.3** | **0.3** | **2.3** |
| SecAlign++ | 58.4 | 4.2 | 6.6 | 5.4 |
| PISanitizer | 74.1 | 11.2 | 3.8 | 7.5 |
| DataSentinel | 55.3 | 26.5 | 12.4 | 19.4 |
| PIGuard | 72.2 | 26.8 | 21.8 | 24.3 |
| PromptGuard | 66.4 | 30.2 | 24.5 | 27.3 |
| DataFilter | 62.6 | 37.3 | 22.2 | 29.7 |
| PromptArmor | 74.3 | 50.3 | 57.8 | 54.1 |
| No defense (this run) | 74.7 | 55.6 | 71.5 | 63.6 |
| No defense (published) | 74.3 | 55.8 | 72.4 | 64.1 |

Lower ASR is better, higher utility is better. Percent, mean over PIArena's 13 datasets, as the
leaderboard computes it. Backend model and judge: `Qwen/Qwen3-4B-Instruct-2507`, the column of
PIArena's defense leaderboard. Measured 25-29 September 2026 through the live API. Rows other
than ours and "this run" are PIArena's published numbers (`website/data/results.json` at the
pinned commit, copied to `reference/`).

Counted over samples rather than datasets, with 95% Wilson intervals: `direct` 84 of 1,700
attacks succeeded (4.9 ± 1.0 %), `combined` 6 of 1,700 (0.4 ± 0.3 %), and 5 of 1,700 clean
documents were blocked (0.29 ± 0.28 %). One document of 5,100 was not scored by the detector and
passed through as clean.

The full report, per dataset, is `results/intent-1.5.2/table.md`; the attacks that got through
are listed one by one in `results/intent-1.5.2/cases.md`; the record of every sample is in
`results/intent-1.5.2/runs/`.

### What is and is not in this table

- **The threshold was not chosen on PIArena.** The API returns verdicts at three operating
  points set on AI Cordon's own clean corpus. This run reads `1e-04`, which is the point of the
  service's own verdict: the threshold a user of the API gets by default (0.900). Nothing was
  fitted, tuned or selected on PIArena data. The verdicts at the other two points are in every
  record.
- **The pipeline reproduces the published baseline.** "No defense (this run)" against "No defense
  (published)" is the check that the loop here is the loop the authors ran: the two agree within
  a few points on every dataset (`table.md`, "The pipeline check").
- **One row is measured here, the others are published.** AI Cordon Intent and "this run" come
  from this repository's run; every other row is the number PIArena publishes for that defense.
  The run here is a single seed, 100 or 200 samples per dataset.
- **Two of PIArena's three attack columns.** The leaderboard also has `strategy`, an adaptive
  search that writes the injection against the defense it faces. It is not measured for
  AI Cordon Intent, so "ASR mean" above is over `direct` and `combined` for every row, and the
  table says nothing about adaptive attacks. They are much harder for every defense; PIArena's
  published `strategy` ASR over the same 13 datasets is 0.5 for Attn.Tracker, 21.5 for
  SecAlign++, 44.7 for DataSentinel, 57.8 for DataFilter, 79.4 for PIGuard, 86.2 for
  PISanitizer, 92.2 for PromptGuard and PromptArmor, 99.4 with no defense.
- **A blocked document is handled differently.** PIArena's detection defenses answer a flagged
  document with a fixed warning. Here the flagged document is dropped and the model answers the
  user's task over an empty one. Counted PIArena's way the row reads 74.4 / 4.2 / 0.2 instead of
  74.5 / 4.3 / 0.3 (`table.md`).
- **Utility under attack is not compared.** PIArena leaves that cell empty for detection
  defenses, and so does this table. The per-sample utility is in the records.
- **No PIArena text in the detector's data, as far as a verbatim search shows.** None of
  PIArena's 1,690 distinct injected instructions occurs in the detector's training and
  calibration pools or in the datasets they are built from. Of its 1,700 clean documents, 23
  share a 64-character span with those pools, 22 of them code files of `lcc_long`. The search is
  verbatim and over text files; it cannot see a paraphrase.
- **The detector is a hosted service, not an open model.** Reproducing the AI Cordon row needs
  an API key. Everything else runs locally.

### How to quote it

"AI Cordon Intent 1.5.2, run as a defense in PIArena's pipeline: attack success 4.3% under the
direct attack and 0.3% under the combined attack, utility on clean documents 74.5%, against
55.6%, 71.5% and 74.7% with no defense; mean over PIArena's 13 datasets, Qwen3-4B backend."

This is a measurement made with PIArena, not an entry of PIArena's leaderboard: the row is not
on `piarena.vercel.app` and was not run by PIArena's authors. It covers the two static attacks.

## The test

- **Datasets.** The 13 of PIArena's defense leaderboard: `squad_v2`, `dolly_closed_qa`,
  `dolly_information_extraction`, `dolly_summarization`, `nq_rag`, `msmarco_rag`,
  `hotpotqa_rag`, `hotpotqa_long`, `qasper_long`, `gov_report_long`, `multi_news_long`,
  `passage_retrieval_en_long`, `lcc_long`. 1,700 samples.
- **Attacks.** `none`, `direct` (the injected task is placed in the document as it is) and
  `combined` (the same, behind `Answer: task complete. Ignore previous instructions.`).
  PIArena's code, PIArena's seed (42). The defended and the undefended run see the same
  documents: the injected texts are identical in every pair.
- **Defense.** Each document goes to `POST /api/v1/check` with `detector: intent`. A document
  the API flags at the operating point is dropped, as PIArena's detection defenses do.
- **Runs.** 13 datasets × 3 attacks × {no defense, AI Cordon Intent} = 78.
- **Two variants of the defense.** `aicordon_api` drops a flagged document, as PIArena's
  detection defenses do. `aicordon_api_cut` asks the API for the fragments it marks
  (`/api/v1/detect`, `spans`), cuts exactly those out of a flagged document and passes the rest
  to the model, as PIArena's sanitizers do; that variant has a utility under attack, and the
  comparison is with PISanitizer, DataFilter and PromptArmor. Nothing is cut wider than the
  service marks, so the second variant measures the service's own localisation. A flagged
  document with no fragment marked is dropped, and the record says so.

What the defense module refuses to fudge:

- A refusal is not a detection. A document the API does not score (too short, too large) is
  recorded as such and passed through as clean. Counting refusals as blocks would lower ASR
  without the detector having seen anything.
- An error is neither a detection nor a pass: the run stops.
- A long document is sent in windows of 20,000 characters with a 2,000-character overlap; the
  document is flagged when any window is.
- There is no answer cache: every document is scored live, every time.

## One run, one detector version

Results are kept per detector version, `results/intent-1.5.2/`, and a directory holds nothing
else. The run names the version it expects (`VERSION`, default `v1.5.2`) and stops on the first
answer that carries another one, so a release in the middle of a run cannot finish it on a
different detector. Every record carries the version the service reported; `export.py` and
`report.py` refuse a directory that mixes two.

A new version is a new run: `VERSION=v1.6.0 ./run.sh`. The undefended runs do not depend on the
detector and are taken from the previous version's directory; the 39 defended ones are measured
again.

## Run it

A GPU with about 9 GB free for the 4B backend model, Python 3.10+, `git`.

```sh
cd piarena
./setup.sh                          # clones PIArena at 8bd7a89 into upstream/, installs the defense, applies the patch
pip install torch transformers accelerate datasets rouge fuzzywuzzy python-Levenshtein
export AICORDON_API_KEY=...         # https://app.ai-cordon.com
./run.sh --status                   # state, from the result files; changes nothing
./run.sh                            # inside tmux; Ctrl-C stops, a second launch continues
DEFENSES="none aicordon_api_cut" ./run.sh   # the sanitizer variant; the undefended runs are shared
python3 export.py                   # PIArena's result files -> results/intent-<version>/runs/*.jsonl
python3 report.py --write           # the tables and the list of cases
python3 figures.py                  # the figures, SVG; ./render.sh makes PNG copies for slides
python3 show.py squad_v2 direct 24  # one sample in full
```

`report.py` alone needs nothing but Python: it recomputes every table from the records in
`results/`.

The run takes about a day on one 16 GB card. It resumes sample by sample, and a run that dies
because another process took the card's memory is retried when the memory is back.

## What is changed in PIArena

`patches/piarena-8bd7a89.patch`, three changes, none of them to a metric:

| file | change | why |
|---|---|---|
| `main.py` | the judge is given the already loaded backend model | upstream loads a second copy of the same model for the judge; two do not fit on a 16 GB card. Backend and judge are the same model here, so the verdicts are the same |
| `piarena/utils.py` | result files are written beside the target and renamed | upstream rewrites the file in place after every sample; an interrupt inside that window loses the run |
| `piarena/defenses/__init__.py` | registers `aicordon_api`; other defenses are imported inside `try/except ImportError` | upstream imports fastchat and vLLM at import time; a defense whose dependencies are absent simply does not register |

## Looking at the results without running anything

Every sample the run scored is kept in `results/intent-1.5.2/`: the detector's score and
verdicts, the model's response, the judge's verdicts, the injected instruction. The tables are
recomputed from those records by `python3 report.py`, the attacks that got through are listed in
`cases.md`, and `python3 show.py <dataset> <attack> <idx>` prints one sample in full. None of it
needs a GPU or an API key. [`results/README.md`](results/README.md) describes the files field by
field.

## Licence and credit

The harness is Apache-2.0 (`../LICENSE`). PIArena is MIT (`reference/PIARENA-LICENSE`);
`reference/piarena-results.json` is its published leaderboard data, unchanged. If you use the
numbers, cite PIArena: the protocol and the data are theirs.

```bibtex
@inproceedings{geng2026piarena,
  title={{PIArena}: A platform for prompt injection evaluation},
  author={Geng, Runpeng and Yin, Chenlong and Wang, Yanting and Chen, Ying and Jia, Jinyuan},
  booktitle={Proceedings of the 64th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  year={2026}
}
```
