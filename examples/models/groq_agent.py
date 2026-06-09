# Groq runs open models (Llama3, Mistral) with very low latency. Free tier. OpenAI-compatible API.

from __future__ import annotations

import asyncio
import os
import time

import httpx
from dotenv import load_dotenv

from agentstatelib import StatePatch
from agentstatelib.contrib.base_agent import LLMAgent


class GroqAgent(LLMAgent):
    def __init__(
        self,
        agent_id,
        system_prompt,
        model,
        api_key: str | None = None,
        max_retries: int = 3,
    ):
        super().__init__(
            agent_id=agent_id,
            system_prompt=system_prompt,
            model=model,
            max_retries=max_retries,
        )
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"

    async def _call_model(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


async def main():
    load_dotenv()

    agent = GroqAgent(
        agent_id="groq_demo",
        system_prompt="You are a precise assistant that returns structured state patches.",
        model=os.environ.get("GROQ_MODEL", "llama3-8b-8192"),
    )

    context = {
        "goal": "Update the task status",
        "task": {"id": "task_1", "status": "in_progress"},
    }

    start = time.perf_counter()
    patch = await agent(context)
    elapsed = time.perf_counter() - start

    print(patch)
    print(f"Elapsed: {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
