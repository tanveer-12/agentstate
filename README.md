# AgentStateLib

[![Version](https://img.shields.io/badge/version-v0.2.0-2563eb?style=flat-square)](https://pypi.org/project/agentstate-lib/)
[![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

AgentStateLib is a Python library for coordinating multiple AI agents through a shared, typed state model.

Instead of passing raw strings between agents, it gives each agent a structured slice of the same workflow state, so multi-agent systems are easier to validate, debug, and recover.

## What it is

AgentStateLib provides a coordination layer for multi-agent Python workflows with:

- A typed `SharedState` model for goals, tasks, facts, decisions, and artifacts.
- A `StatePatch` system for structured, auditable updates.
- An `AgentGraph` router for connecting agent functions into workflows.
- Context slicing so each agent sees only the state it needs.
- Event-backed persistence for replay and debugging.
- In-memory and SQLite storage backends.
- Conflict detection and resolution primitives.

## Current version

**v0.2.0** is the current release line. It includes the core shared-state workflow engine, structured patch application, graph routing, event logging, persistence, and early reliability features.

## Installation

```bash
pip install agentstate-lib
```

## Example

A simple multi-agent workflow usually has one agent plan, another execute, and a third summarize the result.

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
        reason=f"planned workflow for {goal!r}",
    )

@graph.node("researcher", context=["goal", "facts.planned"])
async def researcher(context: dict) -> StatePatch:
    goal = context["goal"]
    planned = context.get("facts", {}).get("planned", False)
    return StatePatch(
        agent_id="researcher",
        target="facts.research_summary",
        value=f"researched {goal!r}, planned={planned}",
        reason="store research findings",
    )

@graph.node("writer", context=["goal", "facts.research_summary"])
async def writer(context: dict) -> StatePatch:
    goal = context["goal"]
    research_summary = context.get("facts", {}).get("research_summary", "")
    return StatePatch(
        agent_id="writer",
        target="facts.final_summary",
        value=f"Final output for {goal!r}: {research_summary}",
        reason="compose final summary",
    )

graph.edge(
    "planner",
    "researcher",
    condition=lambda s: s.get("facts", {}).get("planned") is True,
)

graph.edge(
    "researcher",
    "writer",
    condition=lambda s: bool(s.get("facts", {}).get("research_summary")),
)

async def main() -> None:
    state = SharedState(goal="Write a multi-agent blog post")
    final_state = await graph.run(state, start="planner")
    print(final_state.facts)

if __name__ == "__main__":
    asyncio.run(main())
```

## How it works

Each agent is a plain async Python function that receives a small context dictionary and returns a `StatePatch`. The graph applies patches to shared state, records the update in the event log, and decides which agent runs next based on edge conditions [web:12][web:21].

This makes the workflow explicit:
- The planner marks the task as planned.
- The researcher adds working notes or findings.
- The writer turns those findings into a final result.

## Core concepts

### SharedState

`SharedState` is the validated world model shared by all agents. It is designed to hold the information agents need to coordinate without relying on unstructured chat history.

### StatePatch

Agents do not mutate state directly. Instead, they return a patch describing what should change, why it should change, and which agent proposed it.

### AgentGraph

`AgentGraph` connects agent nodes with typed edges and conditional transitions. This keeps multi-agent workflows readable and testable.

### Context slicing

Each agent can request only the paths it needs, which keeps prompts smaller and makes local-model workflows more practical.

### Event log

Every patch application is captured as an event so you can replay, inspect, and debug workflow execution later.

## Working around current limitations

AgentStateLib is still early-stage, so some parts are intentionally minimal. Until the library grows more features, the best way to work around those limits is to keep workflows narrow, deterministic, and explicit.

- Use small state paths like `facts.*` and `tasks.*` instead of large nested objects.
- Keep each agent responsible for one job.
- Prefer structured outputs over free-form text where possible.
- Add your own validation around patches if you need stricter guarantees.
- Use SQLite for local persistence while experimenting.
- Replay workflows from the event log when debugging failures.
- Split complex workflows into multiple graph steps instead of trying to do everything in one agent call.

## Project status

AgentStateLib is actively developed and currently focused on the shared-state coordination layer for multi-agent systems.

Current capabilities include:
- `SharedState`
- `StatePatch`
- `AgentGraph`
- Event recording
- In-memory storage
- SQLite storage
- Context slicing
- Early conflict handling

## Contributing

Contributions are welcome, especially in these areas:
- Graph execution improvements.
- State validation and patch handling.
- Conflict detection and resolution.
- Persistence backends.
- Examples and documentation.
- Tests for multi-agent workflows.

## License

Licensed under the MIT License.
