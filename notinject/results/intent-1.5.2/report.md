**AI Cordon Intent 1.5.2**: over-defense accuracy **88.2%**, the mean over the three splits (PIGuard's figure); higher is better.

| trigger words | prompts | quiet, the service's verdict | not judged |
|---|---:|---:|---:|
| one | 113 | 92.9% ± 4.9 | 16 |
| two | 113 | 95.6% ± 4.0 | 8 |
| three | 113 | 76.1% ± 7.8 | 4 |
| **all** | **339** | **88.2% ± 3.4** | 28 |

The same prompts at each operating point the service publishes (the false-alarm rate it was set for on clean text):

| operating point | one | two | three | mean |
|---|---:|---:|---:|---:|
| 1e-03 | 85.0% | 91.2% | 72.6% | 82.9% |
| 1e-04 | 92.9% | 95.6% | 76.1% | 88.2% |
| 1e-05 | 95.6% | 97.3% | 84.1% | 92.3% |

By category of the prompt:

| category | prompts | quiet |
|---|---:|---:|
| Common Queries | 126 | 92.9% ± 4.6 |
| Multilingual | 84 | 95.2% ± 4.9 |
| Technique Queries | 87 | 82.8% ± 7.9 |
| Virtual Creation | 42 | 71.4% ± 13.2 |

- Detector version: v1.5.2.
- Not judged (too short for the detector), counted as quiet: 28 of 339.
- ± is the half-width of the 95% Wilson interval. Protocol and data: PIGuard (Li et al., ACL 2025), `leolee99/PIGuard` @ `1b5751e8`.
