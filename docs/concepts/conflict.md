# Conflict Detection and Resolution

## What is a conflict?

A conflict occurs when two or more agents running in the **same parallel execution round** return patches that target the **same dotted state path**.

For example:

```python
StatePatch(
    agent_id="agent_a",
    target="facts.status",
    value="done",
    reason="completed",
)

StatePatch(
    agent_id="agent_b",
    target="facts.status",
    value="failed",
    reason="validation failed",
)
```

Both agents are attempting to modify `facts.status` during the same round. Only one value can ultimately be applied to the state, so the system must decide which patch wins.

This differs from LangGraph's default behavior.

When multiple LangGraph nodes update the same key in parallel, the framework typically merges updates using behavior equivalent to `dict.update()`. If two nodes write the same key, one update silently overwrites the other. The collision is not explicitly recorded.

In agentstatelib, the same situation produces a `ConflictDetected` event. The configured conflict resolver determines the winning patch, and both competing patches remain available in the event history for auditing and debugging.

This means conflicts are:

* Explicitly detected
* Explicitly resolved
* Permanently recorded

rather than silently overwritten.

---

## When conflicts happen

Conflicts are only detected **within a single execution round**.

Consider the following workflow:

### Round 1

```text
agent_a
    └── facts.status = "running"
```

### Round 2

```text
agent_b
    └── facts.status = "complete"
```

This is **not** a conflict.

By the time Round 2 begins, the patch from Round 1 has already been applied to the shared state. Agent B is intentionally updating existing state rather than competing with Agent A.

Conflict detection only examines the patches produced by agents running concurrently in the same round.

Internally, all patches generated during a round are collected and passed together to:

```python
ConflictDetector.resolve_batch(...)
```

Only collisions discovered inside that batch are treated as conflicts.

---

## The resolution pipeline

The conflict resolution process follows a fixed sequence.

### 1. Agents finish execution

All agents in the current round execute against the same state snapshot and return patches.

```text
agent_a → facts.status
agent_b → facts.status
```

### 2. Patches enter `resolve_batch()`

The graph collects every patch produced during the round.

```python
result = conflict_detector.resolve_batch(patches)
```

### 3. Path collision detected

The detector groups patches by target path.

```text
facts.status
├── patch_a
└── patch_b
```

Since more than one patch targets the same path, a conflict exists.

### 4. Resolver chooses a winner

The configured resolver is called:

```python
winner = resolver.resolve(existing, incoming)
```

The resolver returns the patch that should be applied.

### 5. Conflict event emitted

A `ConflictDetected` event is created containing:

* path
* winner agent
* loser agent
* resolution strategy
* both original patches

### 6. Winning patch applied

The winning patch is sent to `apply_patch()`.

```python
state = apply_patch(state, winner)
```

### 7. Patch event emitted

A `PatchApplied` event records the state change.

The workflow then continues normally.

---

## Resolution strategies

agentstatelib ships with three built-in conflict resolution strategies.

### LastWriteWins (default)

```python
from agentstatelib import LastWriteWins
```

The patch with the newest timestamp wins.

```python
patch_a.timestamp = 1000
patch_b.timestamp = 2000
```

Result:

```text
patch_b wins
```

If timestamps are equal, the incoming patch wins.

Use this strategy when:

* Newer information should replace older information
* Agent ordering does not matter
* You want simple, predictable behavior

This is the default resolver used by `AgentGraph`.

---

### PriorityBased

```python
from agentstatelib import PriorityBased
```

The patch with the higher priority wins.

```python
StatePatch(priority=1)
StatePatch(priority=10)
```

Result:

```text
priority=10 wins
```

If priorities are equal, the resolver falls back to Last Write Wins.

Use this strategy when:

* Certain agents are more authoritative
* Supervisor agents should override worker agents
* Different classes of agents have different trust levels

Example:

```python
StatePatch(
    priority=100,
    ...
)
```

---

### RejectIncoming

```python
from agentstatelib import RejectIncoming
```

The first patch that claims a path wins.

Every later patch targeting the same path during that round is rejected.

The rejected patch is still recorded in the conflict log.

Use this strategy when:

* The first agent should effectively lock a path
* Deterministic first-writer behavior is desired
* You want to prevent later agents from overriding an earlier decision

Result:

```text
first patch wins
incoming patch loses
```

---

## Custom resolver

Custom conflict resolution strategies are implemented through the `ConflictResolver` protocol.

The protocol requires only one method:

```python
resolve(existing, incoming) -> StatePatch
```

Minimal example:

```python
class MyResolver:
    def resolve(self, existing, incoming):
        if incoming.agent_id == "supervisor":
            return incoming
        return existing
```

Any class providing this method satisfies the protocol.

No inheritance is required.

No base class is required.

No registration step is required.

You can pass the resolver directly into `AgentGraph`:

```python
graph = AgentGraph(
    conflict_resolver=MyResolver()
)
```

This allows domain-specific conflict policies while keeping the conflict detection system unchanged.

---

## Reading the conflict log

All conflict events are persisted through the configured state store.

You can retrieve them after workflow execution and inspect exactly what happened.

```python
events = await store.get_workflow(state.workflow_id)

conflicts = [
    event
    for event in events
    if isinstance(event, ConflictDetected)
]
```

Each conflict event exposes:

```python
event.path
event.winner_agent_id
event.loser_agent_id
event.resolution_strategy
```

Example:

```python
for event in conflicts:
    print(
        event.path,
        event.winner_agent_id,
        event.loser_agent_id,
        event.resolution_strategy,
    )
```

Possible output:

```text
facts.status agent_b agent_a LastWriteWins
```

Because the event also stores both competing patches, conflict history remains fully auditable even after the workflow completes.

This makes it possible to answer questions such as:

* Which agents disagreed?
* Which state path was contested?
* Why did a particular value win?
* How often are conflicts occurring?
* Which resolver strategy was active?

without inspecting workflow execution logs or reproducing the run.
