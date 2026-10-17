**AI Cordon Intent 2.1.1**: over-defense accuracy **82.3%**, the mean over the three splits (PIGuard's figure); higher is better.

| trigger words | prompts | quiet, the service's verdict | not judged |
|---|---:|---:|---:|
| one | 113 | 86.7% ± 6.3 | 0 |
| two | 113 | 94.7% ± 4.3 | 0 |
| three | 113 | 65.5% ± 8.6 | 0 |
| **all** | **339** | **82.3% ± 4.1** | 0 |

The same prompts at each operating point the service publishes (the false-alarm rate it was set for on clean text):

| operating point | one | two | three | mean |
|---|---:|---:|---:|---:|
| fpr_1e-03 | 28.3% | 60.2% | 17.7% | 35.4% |
| fpr_1e-04 | 86.7% | 94.7% | 65.5% | 82.3% |

By category of the prompt:

| category | prompts | quiet |
|---|---:|---:|
| Common Queries | 126 | 89.7% ± 5.4 |
| Multilingual | 84 | 85.7% ± 7.5 |
| Technique Queries | 87 | 66.7% ± 9.7 |
| Virtual Creation | 42 | 85.7% ± 10.6 |

- Detector version: v2.1.1.
- Not judged (too short for the detector), counted as quiet: 0 of 339.
- ± is the half-width of the 95% Wilson interval. Protocol and data: PIGuard (Li et al., ACL 2025), `leolee99/PIGuard` @ `1b5751e8`.
