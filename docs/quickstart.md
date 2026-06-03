Quickstart guide — coming with v0.1.2# Quickstart

## Install

```bash
pip install agentstate-lib
```

## Working example

```python
import asyncio
from agentstatelib import SharedState, AgentGraph, StatePatch

graph = AgentGraph()

@graph.node("planner", context=["goal"])
async def planner(ctx):
    return StatePatch(agent_id="planner", target="facts.plan", value="done", reason="planned")

@graph.node("analyst", context=["facts"])
async def analyst(ctx):
    return StatePatch(agent_id="analyst", target="facts.analysis", value="ready", reason="analyzed")

@graph.node("writer", context=["facts"])
async def writer(ctx):
    return StatePatch(
        agent_id="writer",
        target="artifacts.report",
        value={"produced_by": "writer", "artifact_type": "summary", "content": "final report"},
        reason="written",
    )

graph.edge("planner", "analyst", lambda s: s.get("facts", {}).get("plan") == "done")
graph.edge("analyst", "writer", lambda s: s.get("facts", {}).get("analysis") == "ready")

async def main():
    state = SharedState(goal="test workflow")
    final = await graph.run(state, start="planner")
    assert final.facts["plan"] == "done"
    assert final.facts["analysis"] == "ready"
    assert final.artifacts["report"].content == "final report"
    print("quickstart example passes")

asyncio.run(main())
```

## Parallel agents

```python
import asyncio
from agentstatelib import SharedState, AgentGraph, StatePatch

graph = AgentGraph()

@graph.node("analyst_a", context=["goal"])
async def analyst_a(ctx):
    return StatePatch(agent_id="analyst_a", target="facts.a", value="complete", reason="analysis a done")

@graph.node("analyst_b", context=["goal"])
async def analyst_b(ctx):
    return StatePatch(agent_id="analyst_b", target="facts.b", value="complete", reason="analysis b done")

@graph.node("writer", context=["facts"])
async def writer(ctx):
    return StatePatch(
        agent_id="writer",
        target="artifacts.summary",
        value={"produced_by": "writer", "artifact_type": "summary", "content": "merged analysis"},
        reason="merged",
    )

graph.edge("analyst_a", "writer", lambda s: s.get("facts", {}).get("a") == "complete")
graph.edge("analyst_b", "writer", lambda s: s.get("facts", {}).get("b") == "complete")

async def main():
    state = SharedState(goal="parallel test")
    final = await graph.run(state, start=["analyst_a", "analyst_b"])
    assert final.facts["a"] == "complete"
    assert final.facts["b"] == "complete"
    assert final.artifacts["summary"].content == "merged analysis"

asyncio.run(main())
```

## What's happening

- `SharedState` is the shared workflow snapshot every agent reads from.
- `@graph.node(...)` registers an async function as an agent in the graph.
- `StatePatch` is the structured change an agent proposes instead of mutating state directly.
- The edge condition decides whether the next agent should run based on the current state.
- In the parallel example, `start=["analyst_a", "analyst_b"]` tells the graph to run both agents in the first round.

## Next steps

- [SharedState](./concepts/shared-state.md)
- [Patches](./concepts/patches.md)
- [API reference: State](./api-reference/state.md)
- [API reference: Patch](./api-reference/patch.md)
- [API reference: Graph](./api-reference/graph.md)