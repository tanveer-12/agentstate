"""Optional base class for LLM-backed agent functions. Provides the retry-with-correction loop common across all providers. Not required — any async callable accepting a dict and returning a StatePatch is a valid AgentFn."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from pydantic import ValidationError

from agentstatelib.core.events import (
    ModelCalled,
    ModelReturned,
    PromptAssembled,
    RetryAttempted,
    StateEvent,
    ValidationFailed,
)
from agentstatelib.core.patch import StatePatch
from agentstatelib.memory.store import StateStore


class MaxRetriesExceeded(Exception):
    def __init__(
        self,
        agent_id: str,
        attempts: int,
        last_error: str,
        last_output: str,
    ) -> None:
        self.agent_id = agent_id
        self.attempts = attempts
        self.last_error = last_error
        self.last_output = last_output
        super().__init__(str(self))

    def __str__(self) -> str:
        return (
            f"MaxRetriesExceeded:\n"
            f"  agent_id: {self.agent_id}\n"
            f"  attempts: {self.attempts}\n"
            f"  last_error: {self.last_error}\n"
            f"  last_output: {self.last_output}"
        )


class LLMAgent:
    """Optional base class for LLM-backed agent functions.

    Example:
        from agentstate.router.graph import AgentGraph
        from agentstate.contrib.base_agent import LLMAgent
        from agentstate.core.patch import StatePatch

        class MyOllamaAgent(LLMAgent):
            async def _call_model(self, prompt: str) -> str:
                response = await self.client.generate(prompt)
                return response.text

        agent = MyOllamaAgent(
            agent_id="researcher",
            system_prompt="You update task status.",
            model="llama3:8b",
        )

        graph = AgentGraph()
        graph.node("researcher", agent)
        graph.edge("start", "researcher")
    """

    def __init__(
        self,
        agent_id: str,
        system_prompt: str,
        model: str,
        max_retries: int = 3,
        store: StateStore | None = None,
        workflow_id: str | None = None,
        provider: str = "unknown",
    ) -> None:
        self.agent_id = agent_id
        self.system_prompt = system_prompt
        self.model = model
        self.max_retries = max_retries
        self._store = store
        self._workflow_id = workflow_id
        self.provider = provider

    async def _emit(self, event: StateEvent) -> None:
        if self._store is not None:
            await self._store.append(event)

    async def __call__(self, context: dict[str, Any]) -> StatePatch:
        last_error: str | None = None
        last_output: str | None = None

        for attempt in range(self.max_retries):
            prompt = self._build_prompt(context, error=last_error)
            await self._emit(
                PromptAssembled(
                    workflow_id=self._workflow_id or "",
                    agent_id=self.agent_id,
                    prompt_text=prompt,
                    system_prompt_length=len(self.system_prompt),
                    context_length=len(json.dumps(context, indent=2, default=str)),
                    is_correction_attempt=last_error is not None,
                    attempt_number=attempt,
                )
            )

            call_id = str(uuid.uuid4())
            started = time.perf_counter()

            await self._emit(
                ModelCalled(
                    workflow_id=self._workflow_id or "",
                    agent_id=self.agent_id,
                    model=self.model,
                    provider=self.provider,
                    attempt_number=attempt,
                    call_id=call_id,
                )
            )

            raw = await self._call_model(prompt)
            latency = time.perf_counter() - started

            await self._emit(
                ModelReturned(
                    workflow_id=self._workflow_id or "",
                    agent_id=self.agent_id,
                    call_id=call_id,
                    raw_response=raw,
                    latency_seconds=latency,
                    input_tokens=None,
                    output_tokens=None,
                    estimated_cost_usd=None,
                )
            )

            cleaned = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )

            try:
                parsed: dict[str, Any] = json.loads(cleaned)
            except json.JSONDecodeError as e:
                last_error = str(e)
                last_output = raw
                will_retry = attempt < self.max_retries - 1
                await self._emit(
                    ValidationFailed(
                        workflow_id=self._workflow_id or "",
                        agent_id=self.agent_id,
                        attempt_number=attempt,
                        error_type="json_decode_error",
                        error_message=str(e),
                        raw_output=raw,
                        will_retry=will_retry,
                    )
                )
                if will_retry:
                    await self._emit(
                        RetryAttempted(
                            workflow_id=self._workflow_id or "",
                            agent_id=self.agent_id,
                            attempt_number=attempt + 1,
                            previous_error=str(e),
                        )
                    )
                continue

            try:
                return StatePatch(agent_id=self.agent_id, **parsed)
            except ValidationError as e:
                last_error = str(e)
                last_output = raw
                will_retry = attempt < self.max_retries - 1
                await self._emit(
                    ValidationFailed(
                        workflow_id=self._workflow_id or "",
                        agent_id=self.agent_id,
                        attempt_number=attempt,
                        error_type="schema_validation_error",
                        error_message=str(e),
                        raw_output=raw,
                        will_retry=will_retry,
                    )
                )
                if will_retry:
                    await self._emit(
                        RetryAttempted(
                            workflow_id=self._workflow_id or "",
                            agent_id=self.agent_id,
                            attempt_number=attempt + 1,
                            previous_error=str(e),
                        )
                    )
                continue

        raise MaxRetriesExceeded(
            agent_id=self.agent_id,
            attempts=self.max_retries,
            last_error=last_error or "unknown",
            last_output=last_output or "",
        )

    def _build_prompt(self, context: dict[str, Any], error: str | None = None) -> str:
        parts = [
            self.system_prompt,
            "Current state context:\n" + json.dumps(context, indent=2, default=str),
            "Return a JSON object with exactly these three fields:\n- target: string "
            "(the dotted state path to update)\n- value: any valid JSON "
            "(the new value)\n- reason: string (one sentence explaining this update)"
            "\n\nReturn only the JSON object. No markdown. No explanation."
            " No code fences.",
        ]
        if error is not None:
            parts.append(
                f"Your previous response failed with this error:\n{error}\n "
                f" Return corrected JSON only."
            )
        return "\n\n".join(parts)

    async def _call_model(self, prompt: str) -> str:
        """
        Make one call to your model with the given prompt.
        Return the raw string response.
        The base class handles JSON parsing, StatePatch validation,
        and the retry loop.
        """
        raise NotImplementedError("Subclass must implement _call_model")
