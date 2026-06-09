from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from agentstatelib.contrib.base_agent import MaxRetriesExceeded
from agentstatelib.core.patch import StatePatch
from examples.models.ollama_agent import OllamaAgent, check_connection


@dataclass
class BenchmarkResult:
    model: str
    use_grammar: bool
    attempt: int
    success: bool
    retries_used: int
    latency_seconds: float
    error: str | None


BENCHMARK_CONTEXT = {
    "goal": "Analyze architectural differences between monolithic and microservices systems",
    "tasks": {
        "task_1": {
            "description": "identify three core differences",
            "status": "pending",
        }
    },
    "facts": {"domain": "software architecture", "depth": "technical"},
}


async def run_single_attempt(
    model: str,
    base_url: str,
    context: dict,
    use_grammar: bool,
    max_retries: int = 3,
) -> BenchmarkResult:
    start = time.perf_counter()
    agent = OllamaAgent(
        agent_id="benchmark",
        system_prompt="Return a single JSON state patch.",
        model=model,
        base_url=base_url,
        use_grammar=use_grammar,
        max_retries=max_retries,
    )

    success = False
    error: str | None = None
    retries_used = 0

    try:
        _ = await agent(context)
        success = True
    except MaxRetriesExceeded as e:
        error = str(e)
        retries_used = e.attempts
    except Exception as e:
        error = str(e)

    latency = time.perf_counter() - start
    return BenchmarkResult(
        model=model,
        use_grammar=use_grammar,
        attempt=1,
        success=success,
        retries_used=retries_used,
        latency_seconds=latency,
        error=error,
    )


async def benchmark_model(model: str, base_url: str, n_runs: int = 20) -> dict:
    grammar_results = [
        await run_single_attempt(model, base_url, BENCHMARK_CONTEXT, True)
        for _ in range(n_runs)
    ]
    plain_results = [
        await run_single_attempt(model, base_url, BENCHMARK_CONTEXT, False)
        for _ in range(n_runs)
    ]

    def summarize(results: list[BenchmarkResult]) -> dict:
        successes = [r for r in results if r.success]
        return {
            "success_rate": len(successes) / len(results) if results else 0.0,
            "avg_retries": sum(r.retries_used for r in results) / len(results)
            if results
            else 0.0,
            "avg_latency_seconds": sum(r.latency_seconds for r in results)
            / len(results)
            if results
            else 0.0,
        }

    return {
        "model": model,
        "n_runs": n_runs,
        "with_grammar": summarize(grammar_results),
        "without_grammar": summarize(plain_results),
        "results": [asdict(r) for r in grammar_results + plain_results],
    }


async def main():
    load_dotenv(override=True)
    base_url = os.environ["OLLAMA_BASE_URL"]
    if not base_url:
        raise RuntimeError("OLLAMA_BASE_URL is missing from .env")
    model_env = os.environ.get("OLLAMA_MODELS", "llama3:8b,mistral:7b")
    models = [m.strip() for m in model_env.split(",") if m.strip()]

    if not check_connection(base_url):
        print(
            "Ollama connection failed.\n"
            "Check:\n"
            "- Ollama is running\n"
            "- base_url is correct\n"
            "- ngrok tunnel is active\n"
            "- models are pulled"
        )
        return

    all_results = []
    for model in models:
        result = await benchmark_model(model, base_url, n_runs=20)
        all_results.append(result)

    print(
        f"{'Model':<18} {'Grammar':<10} {'Success':<10} {'Avg Retries':<12} {'Avg Latency (s)':<16}"
    )
    print("-" * 70)
    for item in all_results:
        for label, key in [("yes", "with_grammar"), ("no", "without_grammar")]:
            stats = item[key]
            print(
                f"{item['model']:<18} {label:<10} {stats['success_rate']:<10.2f} "
                f"{stats['avg_retries']:<12.2f} {stats['avg_latency_seconds']:<16.2f}"
            )

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    payload = {"benchmarks": all_results}
    (out_dir / "benchmark_results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
