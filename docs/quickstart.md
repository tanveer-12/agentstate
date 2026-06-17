# Quickstart

Get your first multi-agent workflow running in under five minutes.

---

## Prerequisites

- **Python 3.12 or later** — check with `python --version`
- **pip** — bundled with Python 3.12+
- A terminal (PowerShell, bash, or zsh all work)

---

## Install

```bash
pip install agentstate-lib
```

Optional extras — install only what you need:

```bash
pip install "agentstate-lib[contrib]"    # LLMAgent base class (subclass to plug in any model)
pip install "agentstate-lib[api]"        # FastAPI HTTP server + SSE streaming + web dashboard
pip install "agentstate-lib[otel]"       # OpenTelemetry export
pip install "agentstate-lib[dashboard]"  # Rich terminal dashboard
```

Verify the install:

```bash
python -c "import agentstatelib; print(agentstatelib.__version__)"
```

---

## Your first workflow

Create a file called `my_workflow.py`:

```python
import asyncio
from agentstatelib import AgentGraph, SharedState, StatePatch

graph = AgentGraph()

@graph.node("planner", context=["goal"])
async def planner(ctx):
    return StatePatch(
        agent_id="planner",
        target="facts.plan",
        value="research the topic",
        reason="Created initial plan",
    )

@graph.node("researcher", context=["facts.plan"])
async def researcher(ctx):
    return StatePatch(
        agent_id="researcher",
        target="facts.research",
        value="Found three relevant sources",
        reason="Completed research step",
    )

@graph.node("writer", context=["facts.research"])
async def writer(ctx):
    return StatePatch(
        agent_id="writer",
        target="facts.report",
        value="Final report drafted",
        reason="Converted research into report",
    )

graph.edge("planner", "researcher", lambda s: s.get("facts", {}).get("plan") == "research the topic")
graph.edge("researcher", "writer", lambda s: s.get("facts", {}).get("research") == "Found three relevant sources")

async def main():
    state = SharedState(goal="Write a market research report")
    final = await graph.run(state, start="planner")
    print(final.facts)

asyncio.run(main())
```

Run it:

```bash
python my_workflow.py
```

Expected output:

```python
{
    "plan": "research the topic",
    "research": "Found three relevant sources",
    "report": "Final report drafted",
}
```

---

## How it works

| Concept | What it does |
|---|---|
| `SharedState` | The shared world model. All agents read from the same snapshot each round. |
| `StatePatch` | What an agent returns. A structured proposal: *"set `facts.report` to this value"*. |
| `AgentGraph` | Routes agents as a directed graph. Resolves conflicts before applying patches. |
| `@graph.node` | Registers an async function as a named agent. The `context=` list declares which state paths it needs to read. |
| `graph.edge` | Adds a directed edge. The `condition` lambda receives the current state dict and returns `True` to activate the next agent. |

Agents never mutate state directly — they return proposals. The graph applies them atomically after resolving any conflicts.

---

## Parallel agents

Pass a list to `start=` to run multiple agents concurrently in the first round:

```python
final = await graph.run(state, start=["analyst_a", "analyst_b"])
```

All agents in the same round see the same state snapshot. Their patches are batch-resolved (conflict detection runs) before any state update occurs.

---

## Persistent event log

Every run is automatically recorded. Swap the default in-memory store for SQLite to keep the log across restarts:

```python
from agentstatelib import SQLiteStore, AgentGraph

store = SQLiteStore("workflows.db")
graph = AgentGraph(store=store)

final = await graph.run(state, start="planner")

events = await store.get_workflow(state.workflow_id)
print(f"Recorded {len(events)} events")
```

---

## Connect a real AI model

Install the contrib extra and subclass `LLMAgent`. You only need to implement `_call_model` — everything else (JSON parsing, schema validation, retry-with-correction) is inherited:

```bash
pip install "agentstate-lib[contrib]"
```

```python
import httpx
from agentstatelib.contrib.base_agent import LLMAgent

class MyOllamaAgent(LLMAgent):
    async def _call_model(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3:8b", "prompt": prompt, "stream": False},
            )
            return r.json()["response"]
```

Ready-to-run example files for every provider are in the `examples/models/` directory.

---

## Human approval gates

Pause the workflow and wait for a human decision before a sensitive step:

```python
graph.edge(
    "planner",
    "executor",
    condition=lambda s: s.get("status") == "ready",
    approval_required=lambda state, patch: patch.target.startswith("financial."),
)

final = await graph.run(state, start="planner")

# Resolve programmatically
approval_id = next(iter(graph.pending_approvals))
new_state = await graph.resume_from_approval(
    approval_id=approval_id,
    decision="approved",
    modified_patch=None,
)
```

---

## Environment variables

These are only needed when using the optional extras:

| Variable | Used by | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI example agent | API key |
| `OPENAI_MODEL` | OpenAI example agent | Model name (default: `gpt-4o-mini`) |
| `ANTHROPIC_API_KEY` | Anthropic example agent | API key |
| `ANTHROPIC_MODEL` | Anthropic example agent | Model name (default: `claude-haiku-4-5-20251001`) |
| `GROQ_API_KEY` | Groq example agent | API key |
| `GROQ_MODEL` | Groq example agent | Model name (default: `llama3-8b-8192`) |
| `OLLAMA_BASE_URL` | Ollama example agent | Server URL (default: `http://localhost:11434`) |
| `OLLAMA_MODEL` | Ollama example agent | Model name (default: `llama3:8b`) |

Put them in a `.env` file — the example agents load it automatically via `python-dotenv`.

---

## Full documentation

### Concepts

- [Shared State](./concepts/shared-state.md) — the `SharedState` model and field structure
- [Patches](./concepts/patches.md) — `StatePatch` anatomy and how mutations work
- [Conflict Detection](./concepts/conflict.md) — LastWriteWins, PriorityBased, RejectIncoming strategies
- [Parallel Execution](./concepts/parallelism.md) — round-based scheduling and batch resolution
- [Event Log](./concepts/event-log.md) — append-only store, InMemoryStore, SQLiteStore, PostgreSQLStore
- [Trace Model](./concepts/trace-model.md) — 16 typed trace events for LLM agents
- [Observability](./concepts/observability.md) — Rich dashboard and metrics overview
- [Local Models](./concepts/local-models.md) — model-agnostic design and the `LLMAgent` contract

### API Reference

- [State](./api-reference/state.md) — `SharedState`, field types, Pydantic schema
- [Patch](./api-reference/patch.md) — `StatePatch` fields and validation rules
- [Graph](./api-reference/graph.md) — `AgentGraph`, `node`, `edge`, `run`, approval API
- [Conflicts](./api-reference/conflicts.md) — conflict resolver classes and custom resolvers
- [Store](./api-reference/store.md) — `InMemoryStore`, `SQLiteStore`, `PostgreSQLStore` API

### Guides

- [HTTP API](./guides/http-api.md) — FastAPI server, SSE streaming, REST endpoints
- [Human in the Loop](./guides/human-in-the-loop.md) — approval gates, REST resolution, programmatic resolution
- [Checkpoint & Recovery](./guides/checkpoint-recovery.md) — save/load state, automatic recovery on restart
- [Replay Debugger](./guides/replay-debugger.md) — step-through inspection of any past workflow
- [LLM Integration](./guides/llm-integration.md) — `LLMAgent` base class, retry loop, structured output
- [Local Models](./guides/local-models.md) — Ollama, LM Studio, vLLM, Groq, Anthropic, rule-based agents
- [OpenTelemetry](./guides/opentelemetry.md) — exporting traces to Jaeger, Grafana, and other collectors
- [Observability](./guides/observability.md) — Rich terminal dashboard setup
