# SharedState

## What SharedState is

SharedState is the shared world model used by every workflow in agentstatelib.

A useful way to think about it is as a shared blackboard. Every agent in a workflow can read from the same blackboard and propose updates to it. Agents never write directly to the blackboard. Instead, they submit structured update proposals that go through validation, conflict resolution, and event logging before becoming part of the shared state.

Because all agents read from the same state snapshot during a parallel execution round, every agent sees a consistent view of the workflow. This eliminates intra-round race conditions and makes workflow execution deterministic and debuggable.

## Why it is never mutated directly

SharedState is immutable by design.

Instead of modifying state in place, every change is represented as a `StatePatch`. The patch is applied through `apply_patch()`, which returns a new `SharedState` object while leaving the original unchanged.

This design enables several important capabilities:

- **Auditability** — every change is attributed to an agent and recorded.
- **Replayability** — any historical state can be reconstructed from the event log.
- **Consistent parallel execution** — all agents in a round read the same snapshot.
- **Conflict detection** — multiple agents attempting to modify the same path can be detected before state changes occur.

Without immutability, it would be much harder to understand how a workflow reached a particular result or identify which agent introduced an incorrect change.

## The fields

### goals

Goals represent high-level objectives.

For example, in a research workflow you might create goals such as:

- Research competing products
- Analyze market trends
- Produce final recommendation

Goals help organize related tasks and provide progress tracking across the workflow.

### tasks

Tasks represent concrete units of work.

Examples:

- Summarize article A
- Extract pricing information
- Verify competitor claims
- Draft executive summary

Tasks are typically assigned to individual agents and move through statuses such as `pending`, `running`, and `done`.

### artifacts

Artifacts are outputs produced by agents.

Examples:

- A draft report
- A summarized article
- A generated code snippet
- A final recommendation document

Artifacts allow agents to share intermediate and final outputs through shared state.

### facts

Facts store structured information that should be accessible throughout the workflow.

Examples:

```python
{
    "company": "ExampleCorp",
    "deadline": "2026-01-15",
    "preferred_model": "llama3"
}
```

Facts are useful for configuration, extracted knowledge, and workflow-wide context.

### decisions

Decisions record important workflow choices along with the reasoning behind them.

Examples:

- Use SQLite instead of PostgreSQL for v0.1
- Reject conflicting patch from agent B
- Prioritize source A because it is more recent

Decisions provide an audit trail that helps explain why the workflow evolved in a particular direction.

## Code example

```python
from agentstatelib.core.patch import StatePatch, apply_patch
from agentstatelib.core.state import SharedState

state = SharedState(goal="Build agentstatelib")

patch = StatePatch(
    agent_id="planner",
    target="facts.owner",
    value="tanveer",
    reason="record workflow owner",
)

new_state = apply_patch(state, patch)

assert state is not new_state
assert "owner" not in state.facts
assert new_state.facts["owner"] == "tanveer"
```

The original state remains unchanged while the new state contains the applied update.

## Next steps

Now that you understand SharedState, continue to the [Patches](./patches.md) concept page to learn how agents propose changes through `StatePatch` and how those changes become part of workflow state.