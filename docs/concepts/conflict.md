# Conflict Detection

## What a conflict is

A conflict happens when two agents in the same parallel round both target the same state path. That means they are trying to write to the same dotted location in `SharedState` at the same time.

In LangGraph, if two agents update the same key, the last writer wins silently. In agentstatelib, the conflict is detected before either patch is applied, resolved explicitly, and logged as a `ConflictDetected` event.

## The resolution pipeline

The pipeline is straightforward:

1. Agents in a round return patches.
2. The batch is submitted to `resolve_batch()`.
3. The conflict detector chooses winners for each path.
4. A `ConflictDetected` event is emitted for each collision.
5. The winning patches are applied to state.

This keeps conflicts visible instead of implicit. It also makes the final state easier to reason about because every overwritten value has a record.

## Resolution strategies

`LastWriteWins` chooses the patch with the latest timestamp. Use it when recency matters more than provenance.

`PriorityBased` chooses the patch with the highest `priority`, and falls back to last-write-wins if priorities are equal. Use it when some agents should be allowed to outrank others, such as a human-reviewed patch or a coordinator patch.

`RejectIncoming` always keeps the first patch received. Use it when you want the first claim on a path to win and treat all later writes as invalid.

You can set priority directly on a patch:

```python
patch = StatePatch(
    agent_id="reviewer",
    target="facts.status",
    value="approved",
    reason="manual review",
    priority=10,
)
```

## Writing a custom resolver

The resolver contract is a protocol. Any object with a `resolve(existing, incoming)` method can plug in.

```python
from agentstatelib.coordination.conflicts import ConflictResolver

class PreferReviewer:
    def resolve(self, existing, incoming):
        return incoming if incoming.agent_id == "reviewer" else existing
```

That is enough to satisfy the `ConflictResolver` protocol and participate in batch conflict resolution.

## Reading the conflict log

You can inspect logged conflicts by filtering the event log for `ConflictDetected` events:

```python
events = await store.get_workflow(workflow_id)
conflicts = [e for e in events if isinstance(e, ConflictDetected)]
```

This is useful for debugging, audits, and replay analysis because you can see which agent won, which agent lost, and how the resolver behaved.