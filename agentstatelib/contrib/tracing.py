from __future__ import annotations

import functools
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agentstatelib.core.events import ToolCalled, ToolReturned
from agentstatelib.memory.store import StateStore

T = TypeVar("T")


def trace_tool(
    store: StateStore,
    workflow_id: str,
    agent_id: str,
    tool_name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for tracing external tool calls in agent functions. Wrap any async function that makes a side-effecting external call. The workflow store and workflow_id must be available in the agent's closure."""

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            tool_call_id = str(uuid.uuid4())
            start = time.perf_counter()

            await store.append(
                ToolCalled(
                    workflow_id=workflow_id,
                    agent_id=agent_id,
                    tool_name=tool_name,
                    tool_input={"args": args, "kwargs": kwargs},
                    tool_call_id=tool_call_id,
                )
            )

            try:
                result = await fn(*args, **kwargs)
                latency = time.perf_counter() - start
                await store.append(
                    ToolReturned(
                        workflow_id=workflow_id,
                        agent_id=agent_id,
                        tool_call_id=tool_call_id,
                        success=True,
                        result_summary=str(result)[:200],
                        latency_seconds=latency,
                        error=None,
                    )
                )
                return result
            except Exception as e:
                latency = time.perf_counter() - start
                await store.append(
                    ToolReturned(
                        workflow_id=workflow_id,
                        agent_id=agent_id,
                        tool_call_id=tool_call_id,
                        success=False,
                        result_summary="error",
                        latency_seconds=latency,
                        error=str(e),
                    )
                )
                raise

        return wrapper

    return decorator
