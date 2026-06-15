# Quickstart

Get your first workflow running in under five minutes.

## Install

```bash
pip install agentstate-lib
```

## Working Example

```python
import asyncio

from agentstatelib import AgentGraph, SharedState, StatePatch

graph = AgentGraph()


@graph.node("planner", context=["goal"])
async def planner(ctx):
    return StatePatch(
        agent_id="planner",
        target="facts.plan",
        value="research topic",
        reason="Created initial plan",
    )


@graph.node("researcher", context=["facts.plan"])
async def researcher(ctx):
    return StatePatch(
        agent_id="researcher",
        target="facts.research",
        value="Found three useful sources",
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


graph.edge(
    "planner",
    "researcher",
    lambda s: s.get("facts", {}).get("plan") == "research topic",
)

graph.edge(
    "researcher",
    "writer",
    lambda s: s.get("facts", {}).get("research")
    == "Found three useful sources",
)


async def main():
    state = SharedState(
        goal="Write a market research report"
    )

    final = await graph.run(
        state,
        start="planner",
    )

    print(final.facts)


asyncio.run(main())
```

Output:

```python
{
    "plan": "research topic",
    "research": "Found three useful sources",
    "report": "Final report drafted",
}
```

## Parallel Agents

Multiple agents can run in the same round.

Pass a list to `start=`:

```python
final = await graph.run(
    state,
    start=["analyst_a", "analyst_b"],
)
```

Example:

```python
import asyncio

from agentstatelib import AgentGraph, SharedState, StatePatch

graph = AgentGraph()


@graph.node("analyst_a")
async def analyst_a(ctx):
    return StatePatch(
        agent_id="analyst_a",
        target="facts.a",
        value="complete",
        reason="Analysis A finished",
    )


@graph.node("analyst_b")
async def analyst_b(ctx):
    return StatePatch(
        agent_id="analyst_b",
        target="facts.b",
        value="complete",
        reason="Analysis B finished",
    )


async def main():
    state = SharedState(goal="Run analysis")

    final = await graph.run(
        state,
        start=["analyst_a", "analyst_b"],
    )

    print(final.facts)


asyncio.run(main())
```

Both agents execute concurrently in round 1 and their patches are batch-resolved before being applied.

## What's Happening?

- `SharedState` is the shared world model that all agents read from.
- `@graph.node(...)` registers an async function as an agent in the graph.
- Agents never mutate state directly. They return a `StatePatch`.
- A `StatePatch` is a proposal describing a state change.
- Edge conditions decide whether downstream agents should run.
- All agents in a round see the same state snapshot.
- `start=["analyst_a", "analyst_b"]` runs both agents in parallel during the first round.
- Conflicting patches are resolved before any state updates occur.

## Event log

Every graph run writes an append-only event log automatically. Use an `InMemoryStore` (tests) or `SQLiteStore` (persistent):

```python
from agentstatelib import SQLiteStore, AgentGraph

store = SQLiteStore("workflows.db")
graph = AgentGraph(store=store)

final = await graph.run(state, start="planner")

events = await store.get_workflow(state.workflow_id)
print(f"Recorded {len(events)} events")
```

## Human approval gates

Register an approval gate on any edge. The graph pauses, stores the pending patch in `graph.pending_approvals`, and waits:

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

See the [Human in the Loop guide](./guides/human-in-the-loop.md) for REST API resolution and patterns.

## Next Steps

Core concepts:

- [SharedState](./concepts/shared-state.md)
- [Patches](./concepts/patches.md)
- [Event Log](./concepts/event-log.md)
- [Trace Model](./concepts/trace-model.md)

API reference:

- [State Models](./api-reference/state.md)
- [Patch API](./api-reference/patch.md)
- [Graph API](./api-reference/graph.md)

Guides:

- [HTTP API](./guides/http-api.md)
- [Human in the Loop](./guides/human-in-the-loop.md)
- [Checkpoint & Recovery](./guides/checkpoint-recovery.md)
- [Observability](./guides/observability.md)