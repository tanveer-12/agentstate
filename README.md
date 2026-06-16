# AgentStateLib

AgentStateLib is a Python library for building reliable multi-agent workflows. It gives multiple agents a shared, typed state and a simple graph router, so you can coordinate them without passing raw strings around.

## Installation

```bash
pip install agentstate-lib
```

## Quick start

```python
import asyncio
from agentstatelib import SharedState, AgentGraph, StatePatch

graph = AgentGraph()

@graph.node("planner", context=["goal"])
async def planner(context: dict) -> StatePatch:
    goal = context["goal"]
    return StatePatch(
        agent_id="planner",
        target="facts.planned",
        value=True,
        reason=f"planned goal: {goal!r}",
    )

@graph.node("summarizer", context=["facts.planned", "goal"])
async def summarizer(context: dict) -> StatePatch:
    planned = context.get("facts", {}).get("planned")
    goal = context.get("goal")
    summary = f"Workflow for goal {goal!r} planned={planned}"
    return StatePatch(
        agent_id="summarizer",
        target="facts.summary",
        value=summary,
        reason="add summary",
    )

graph.edge(
    "planner",
    "summarizer",
    condition=lambda s: s.get("facts", {}).get("planned") is True,
)

async def main() -> None:
    state = SharedState(goal="Write a multi-agent blog post")
    final_state = await graph.run(state, start="planner")
    print(final_state.facts)

if __name__ == "__main__":
    asyncio.run(main())
```

## Core ideas

- **SharedState**: a Pydantic model that holds the workflow’s goal, tasks, artifacts, decisions, and facts.
- **StatePatch**: what agents return. A structured change like “set `facts.planned = True`”.
- **AgentGraph**: runs agents as a directed graph. Each agent is just an async function that receives a small context dict and returns a `StatePatch`.
- **Context slicing**: each agent declares which paths it needs (e.g. `["goal", "facts.planned"]`), and only sees that subset of the state.
- **Event store**: every applied patch is recorded as an event in a pluggable store (in-memory or SQLite), so you can replay or debug workflows. [file:1]

## Status

Version `0.5.1` — all Phase 2E features are implemented and tested (93 tests pass, mypy strict: 0 errors).

**Phase 1–2E implemented:**
- SharedState, StatePatch, AgentGraph, round-based parallel execution
- Conflict detection with LastWriteWins, PriorityBased, RejectIncoming strategies
- InvariantChecker framework with two built-in checkers
- Append-only event log (16 typed events) — InMemoryStore, SQLiteStore, PostgreSQLStore
- Checkpointing to disk with save/load/recovery
- ReplayDebugger for step-through inspection of any past state
- Full trace model: ContextSliced, PromptAssembled, ModelCalled, ModelReturned, ValidationFailed, RetryAttempted, ToolCalled, ToolReturned
- LLMAgent base class with retry-with-correction loop
- OpenTelemetry tracing (optional, graceful no-op fallback)
- Rich terminal dashboard (optional)
- FastAPI HTTP server with SSE streaming and web dashboard
- Human-in-the-loop approval gates with REST API and programmatic resolution
- WorkflowSummary analysis with anomaly detection