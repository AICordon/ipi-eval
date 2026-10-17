# AI Cordon Intent 1.5.2 in PIArena

Datasets complete: 13 of 13.  
Detector: AI Cordon Intent v1.5.2, operating point 1e-04.  
Backend LLM and judge: Qwen/Qwen3-4B-Instruct-2507.

### Defense board, 13 datasets

| Defense | Clean utility | ASR direct | ASR combined | ASR mean |
|---|---:|---:|---:|---:|
| Attn.Tracker | 15.3 | 0.0 | 0.0 | 0.0 |
| **AI Cordon Intent** | 74.5 | 4.3 | 0.3 | 2.3 |
| SecAlign++ | 58.4 | 4.2 | 6.6 | 5.4 |
| PISanitizer | 74.1 | 11.2 | 3.8 | 7.5 |
| DataSentinel | 55.3 | 26.5 | 12.4 | 19.4 |
| PIGuard | 72.2 | 26.8 | 21.8 | 24.3 |
| PromptGuard | 66.4 | 30.2 | 24.5 | 27.3 |
| DataFilter | 62.6 | 37.3 | 22.2 | 29.7 |
| PromptArmor | 74.3 | 50.3 | 57.8 | 54.1 |
| No defense (this run) | 74.7 | 55.6 | 71.5 | 63.6 |
| No defense (published) | 74.3 | 55.8 | 72.4 | 64.1 |

Lower ASR is better, higher utility is better. Every row is the mean over the same 13 datasets. Published rows: PIArena `website/data/results.json`.

A blocked document is answered here by the model over an empty document; PIArena's own detection defenses answer it with a fixed warning. Counted their way, the AI Cordon Intent row reads: clean utility 74.4, ASR direct 4.2, ASR combined 0.2, mean 2.2.

### Pooled over samples

| Attack | Defense | Attacks that succeeded | ASR, % |
|---|---|---:|---:|
| direct | AI Cordon Intent | 84 / 1700 | 4.9 ± 1.0 |
| direct | No defense (this run) | 1077 / 1700 | 63.4 ± 2.3 |
| combined | AI Cordon Intent | 6 / 1700 | 0.4 ± 0.3 |
| combined | No defense (this run) | 1311 / 1700 | 77.1 ± 2.0 |

Clean documents blocked: 5 / 1700 (0.29 ± 0.28 %). Documents the API did not score (passed through as clean): 1.

### The pipeline check: no defense, this run / published

| Dataset | Utility, clean | Utility, direct | Utility, combined | ASR direct | ASR combined |
|---|---:|---:|---:|---:|---:|
| squad_v2 | 100.0 / 100.0 | 55.0 / 56.0 | 50.0 / 52.0 | 86.5 / 86.0 | 97.5 / 97.0 |
| dolly_closed_qa | 99.0 / 99.0 | 67.5 / 69.0 | 66.0 / 69.0 | 90.5 / 92.0 | 94.5 / 95.0 |
| dolly_information_extraction | 99.5 / 100.0 | 69.0 / 69.0 | 64.0 / 66.0 | 85.0 / 84.0 | 94.0 / 94.0 |
| dolly_summarization | 98.5 / 99.0 | 51.0 / 52.0 | 49.5 / 51.0 | 92.0 / 92.0 | 95.0 / 96.0 |
| nq_rag | 92.0 / 91.0 | 86.0 / 86.0 | 78.0 / 83.0 | 48.0 / 49.0 | 66.0 / 68.0 |
| msmarco_rag | 95.0 / 97.0 | 82.0 / 82.0 | 61.0 / 63.0 | 35.0 / 35.0 | 73.0 / 77.0 |
| hotpotqa_rag | 97.0 / 94.0 | 79.0 / 79.0 | 66.0 / 65.0 | 50.0 / 50.0 | 68.0 / 70.0 |
| hotpotqa_long | 55.3 / 54.0 | 47.0 / 48.0 | 31.5 / 34.0 | 14.0 / 14.0 | 33.0 / 33.0 |
| qasper_long | 29.1 / 28.0 | 27.3 / 27.0 | 23.2 / 23.0 | 12.0 / 10.0 | 27.0 / 28.0 |
| gov_report_long | 23.7 / 24.0 | 15.3 / 15.0 | 14.4 / 14.0 | 83.0 / 85.0 | 88.0 / 89.0 |
| multi_news_long | 19.4 / 19.0 | 13.7 / 14.0 | 13.1 / 13.0 | 79.0 / 80.0 | 86.0 / 86.0 |
| passage_retrieval_en_long | 100.0 / 100.0 | 93.8 / 92.0 | 71.4 / 74.0 | 17.0 / 17.0 | 61.0 / 59.0 |
| lcc_long | 62.9 / 61.0 | 52.6 / 49.0 | 45.7 / 41.0 | 31.0 / 32.0 | 47.0 / 49.0 |

### AI Cordon Intent per dataset

| Dataset | Clean utility | Blocked, clean | Blocked, direct | Blocked, combined | ASR direct | ASR combined |
|---|---:|---:|---:|---:|---:|---:|
| squad_v2 | 100.0 | 0 / 200 | 189 / 200 | 200 / 200 | 5.0 | 0.0 |
| dolly_closed_qa | 99.0 | 0 / 200 | 187 / 200 | 200 / 200 | 6.0 | 0.0 |
| dolly_information_extraction | 99.5 | 0 / 200 | 175 / 200 | 197 / 200 | 10.0 | 1.5 |
| dolly_summarization | 98.5 | 0 / 200 | 183 / 200 | 199 / 200 | 6.5 | 0.5 |
| nq_rag | 92.0 | 0 / 100 | 92 / 100 | 100 / 100 | 5.0 | 1.0 |
| msmarco_rag | 94.0 | 1 / 100 | 83 / 100 | 100 / 100 | 6.0 | 0.0 |
| hotpotqa_rag | 96.0 | 1 / 100 | 95 / 100 | 100 / 100 | 1.0 | 0.0 |
| hotpotqa_long | 55.3 | 0 / 100 | 87 / 100 | 99 / 100 | 1.0 | 0.0 |
| qasper_long | 28.5 | 2 / 100 | 75 / 100 | 100 / 100 | 0.0 | 0.0 |
| gov_report_long | 23.7 | 0 / 100 | 89 / 100 | 100 / 100 | 8.0 | 0.0 |
| multi_news_long | 19.3 | 1 / 100 | 95 / 100 | 100 / 100 | 3.0 | 0.0 |
| passage_retrieval_en_long | 100.0 | 0 / 100 | 95 / 100 | 100 / 100 | 3.0 | 1.0 |
| lcc_long | 62.9 | 0 / 100 | 80 / 100 | 99 / 100 | 2.0 | 0.0 |

