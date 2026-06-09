# Differences from OpenAI:
# - Anthropic uses the Messages API shape, not OpenAI chat completions.
# - The system prompt is passed in the top-level "system" field.
# - Anthropic has no native JSON mode. The prompt instruction in _build_prompt handles this.
# - The retry loop handles cases where the model adds explanation before the JSON.

from __future__ import annotations

import asyncio
import os
import time

import httpx
from dotenv import load_dotenv

from agentstatelib import StatePatch
from agentstatelib.contrib.base_agent import LLMAgent


class AnthropicAgent(LLMAgent):
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
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    async def _call_model(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")

        headers: dict[str, str] = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": self.model,
                    "max_tokens": 1000,
                    "system": self.system_prompt,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]


async def main():
    load_dotenv()

    agent = AnthropicAgent(
        agent_id="anthropic_demo",
        system_prompt="You are a precise assistant that returns structured state patches.",
        model=os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
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
