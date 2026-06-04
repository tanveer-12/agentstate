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

## Next Steps

Learn the core concepts:

- [SharedState](./concepts/shared-state.md)
- [Patches](./concepts/patches.md)

Explore the API:

- [State Models](./api-reference/state.md)
- [Patch API](./api-reference/patch.md)
- [Graph API](./api-reference/graph.md)