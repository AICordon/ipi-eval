# AI Cordon Intent — benchmarks

How [AI Cordon Intent](https://app.ai-cordon.com), our prompt-injection detector, does on public
benchmarks. All results are kept here with every answer, so anyone can check them.

| benchmark | what it checks | Intent 2.1 |
|---|---|---|
| [LLMail-Inject](llmail/) by Microsoft | catches real attack emails without raising alarms on normal mail | [99.4% of attacks caught](llmail/results/intent-2.1.1/) |
| [Quadrat-IPI](quadrat-full/) | finds injections hidden in emails, documents and web pages | [96.4% found, with 1 false alarm in 1,000 clean documents](quadrat-full/results/intent-2.1.1/) |
| [Quadrat-IPI spans](quadrat-spans/) | shows which part of the document is the injection | [94.3% pointed at; on flagged documents the mark overlaps the injection by 0.81](quadrat-spans/results/intent-2.1.1/) |
| [NotInject](notinject/) | stays quiet on harmless text that sounds suspicious | [82.3% pass](notinject/results/intent-2.1.1/) |
| [PIArena](piarena/) | protects an AI assistant from attacks while it keeps doing its job | measured for the [previous version](piarena/results/intent-1.5.2/) |
| [Latency](latency/) | how fast it checks a document | [about a quarter of a second](latency/results/intent-2.1.1/) |

Each benchmark's page has the details and the earlier version of the detector for comparison.

## Licence

Apache-2.0. Benchmark data belongs to its authors and is not stored here.
