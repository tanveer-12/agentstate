# Reference implementation for Ollama.
# Works with any Ollama instance — local, Docker, remote server.
# Set base_url to point at your Ollama server.
# The library does not know or care where your Ollama runs.

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

from agentstatelib import StatePatch
from agentstatelib.contrib.base_agent import LLMAgent


class PatchDraft(BaseModel):
    target: str
    value: Any
    reason: str


class OllamaAgent(LLMAgent):
    def __init__(
        self,
        agent_id,
        system_prompt,
        model,
        base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        use_grammar: bool = True,
        max_retries: int = 3,
    ):
        super().__init__(
            agent_id=agent_id,
            system_prompt=system_prompt,
            model=model,
            max_retries=max_retries,
        )
        self.base_url = base_url
        self.use_grammar = use_grammar

    async def _call_model(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            if self.use_grammar:
                body["format"] = PatchDraft.model_json_schema()
            response = await client.post(f"{self.base_url}/api/generate", json=body)
            response.raise_for_status()
            return response.json()["response"]


def check_connection(base_url: str) -> bool:
    try:
        requests.get(f"{base_url}/api/tags", timeout=5)
        return True
    except Exception:
        return False


async def main():
    load_dotenv()

    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    if not check_connection(base_url):
        print(
            "Ollama connection failed.\n"
            "Common causes:\n"
            "- Ollama is not running\n"
            "- OLLAMA_BASE_URL is wrong\n"
            "- ngrok tunnel expired\n"
            "- The model has not been pulled yet"
        )
        return

    agent = OllamaAgent(
        agent_id="ollama_demo",
        system_prompt="You are a precise assistant that returns structured state patches.",
        model=os.environ.get("OLLAMA_MODEL", "llama3:8b"),
        base_url=base_url,
        use_grammar=True,
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
