# Patches

## What a patch is

A `StatePatch` is a **proposal**, not a write.

Agents never modify `SharedState` directly. Instead, they return a `StatePatch` describing the change they want to make. The library then decides whether that change should actually be applied.

```python
from agentstatelib import StatePatch

patch = StatePatch(
    agent_id="research_agent",
    target="facts.domain",
    value="machine learning",
    reason="Detected primary topic from source documents",
)
```

This extra layer exists for several important reasons.

### Conflict detection

If two agents attempt to modify the same piece of state during the same parallel round, the library can detect the collision before anything is written.

Without patches:

```text
Agent A writes facts.domain = "biology"
Agent B writes facts.domain = "physics"
```

The last write silently wins.

With patches:

```text
Agent A proposes facts.domain = "biology"
Agent B proposes facts.domain = "physics"
```

The conflict is detected and resolved explicitly.

### Attribution

Every patch contains the `agent_id` of the agent that produced it.

This means the event log can answer questions such as:

- Which agent made this change?
- When was it made?
- What value was replaced?
- Why was it changed?

### Auditability

Every patch requires a reason.

This creates a human-readable history of workflow decisions and state transitions.

Without patches, state changes happen silently.

With patches, every change becomes an explicit event.

---

## The patch pipeline

A patch travels through several stages before it becomes part of the workflow state.

```text
Agent
  │
  ▼
StatePatch
  │
  ▼
ConflictDetector.resolve_batch()
  │
  ▼
apply_patch()
  │
  ▼
InvariantChecker.check()
  │
  ▼
New SharedState
  │
  ▼
PatchApplied event logged
```

Each stage has a single responsibility.

### Agent

Produces a `StatePatch`.

The agent does not modify state itself.

### ConflictDetector.resolve_batch()

Receives all patches produced during the current parallel round.

If multiple patches target the same path, the configured conflict resolution strategy chooses a winner.

### apply_patch()

Applies the winning patch to a copy of the current state.

The original state object remains unchanged.

### InvariantChecker.check()

Validates that the updated state still satisfies workflow invariants.

Examples:

- Tasks must reference valid goals.
- Completed goals cannot have unfinished tasks.

If an error-level invariant fails, workflow execution stops.

### New SharedState

A new immutable snapshot is created.

All agents in the next round will read this updated snapshot.

### PatchApplied event

A `PatchApplied` event is written to the event store.

The event contains:

- patch ID
- target path
- old value
- new value
- reason
- workflow ID
- agent ID

This event becomes part of the permanent audit trail.

---

## The target field

The `target` field specifies **where** the update should be applied.

Targets use dotted-path notation.

```python
StatePatch(
    agent_id="agent",
    target="facts.domain",
    value="robotics",
    reason="Detected topic",
)
```

This updates:

```python
state.facts["domain"]
```

### Examples

Fact update:

```python
target="facts.domain"
```

Task update:

```python
target="tasks.research.status"
```

Artifact update:

```python
target="artifacts.draft.content"
```

Decision metadata:

```python
target="facts.selected_model"
```

### Automatic path creation

Intermediate dictionaries are created automatically.

```python
set_nested({}, "tasks.t1.status", "done")
```

Produces:

```python
{
    "tasks": {
        "t1": {
            "status": "done"
        }
    }
}
```

You do not need to manually create every level beforehand.

This allows agents to propose updates using simple dotted paths regardless of how deeply nested the target location is.

---

## The reason field

The `reason` field is technically required and should be treated as required in spirit as well.

A good reason explains **why** the change is being made.

Poor example:

```python
reason="done"
```

This tells future readers almost nothing.

Better example:

```python
reason="Completed literature review and identified 12 relevant papers"
```

Now the event log immediately communicates:

- what happened
- why it happened
- what work was completed

When debugging workflows weeks later, the reason field often becomes the most valuable piece of information in the entire event log.

Compare:

```text
facts.paper_count = 12
reason = "done"
```

versus

```text
facts.paper_count = 12
reason = "Completed literature review and identified 12 relevant papers"
```

The second entry explains the workflow state without requiring any additional investigation.

As a rule, write reasons for humans, not machines.

---

## Priority

`StatePatch` includes an optional `priority` field.

```python
patch = StatePatch(
    agent_id="planner",
    target="facts.strategy",
    value="approach_a",
    reason="Planner selected strategy",
    priority=10,
)
```

Default value:

```python
priority = 0
```

Priority becomes important when using the `PriorityBased` conflict resolver.

```text
Patch A priority = 5
Patch B priority = 10
```

Patch B wins.

If priorities are equal:

```text
Patch A priority = 10
Patch B priority = 10
```

The resolver falls back to timestamp ordering (last-write-wins behavior).

### When to use priority

Use higher priorities for agents whose decisions should dominate others.

Examples:

- Planner agent over worker agents
- Human approval agent over autonomous agents
- Validation agent over extraction agents

Example:

```python
StatePatch(
    agent_id="human_review",
    target="facts.approved",
    value=True,
    reason="Human reviewer approved output",
    priority=100,
)
```

This ensures the human review decision wins conflicts against lower-priority automated agents.

If you do not need hierarchical authority between agents, leave the priority field at its default value of `0`.