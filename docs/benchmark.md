# Benchmark

## Methodology

This benchmark measures how often an Ollama-backed agent returns a valid `StatePatch` under two conditions: with grammar-constrained output and without it. Each run uses the same benchmark context, the same model, and the same retry limit, so the only variable is whether Ollama receives a schema through the `format` parameter.

For each model, the benchmark runs `n_runs` attempts with grammar enabled and `n_runs` attempts with grammar disabled. For each attempt, it records whether the call succeeded, how many retries were used, the total latency, and any error raised by the retry loop. The benchmark is intended to measure structured-output reliability, not raw token throughput.

## Results

| Model | Grammar | Success rate | Avg retries | Avg latency (s) |
|---|---:|---:|---:|---:|
| `llama3:8b` | yes | 1.00 | 0.00 | 1.86 |
| `llama3:8b` | no | 1.00 | 0.00 | 2.01 |
| `mistral:7b` | yes | 1.00 | 0.00 | 1.44 |
| `mistral:7b` | no | 1.00 | 0.00 | 1.86 |

The grammar condition uses Ollama structured outputs, which constrain generation to a JSON schema passed via `format`. In this run, the simplified schema was reliable and slightly faster than prompt-only output for both local models.

## Interpretation

The important result is not just that grammar works, but that it works without reducing success rate. In your earlier run, the grammar schema was too strict and failed consistently; after simplifying the schema, both models reached 100% success with zero retries. That tells you the coordination model was fine all along — the output contract was the part that needed simplification.

The practical takeaway is that structured output is now viable for local-model agents in this project. Use the grammar path when you want a stricter contract, and keep the retry loop anyway as a safety net for future model or schema changes.