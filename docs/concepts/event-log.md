# Event Log

The event log is the source of truth for a workflow. Instead of mutating shared state directly, agents append typed events that describe what changed and why. `SharedState` is derived from that history, not stored as a separate mutable blob .

## What the event log is

The event log is an append-only sequence of typed events. Every state change, conflict, checkpoint, and error produces an event. Events are immutable once written, which makes the log safe to inspect, replay, and audit later.

In practice, that means your workflow history is a record of facts, not a pile of overwritten state. If something goes wrong, you do not lose the path that led there.

## State as a projection

`SharedState` is a projection of the event log . That means the current state can be reconstructed from events instead of being stored directly. In code, the idea is:

```python
current_state = replay(all_events)
```

This is event sourcing from distributed systems applied to AI workflow coordination. The state you see is just the result of replaying the workflow’s history in order.

That design is what gives you replay and recovery without needing a separate manual state sync system. It also makes the workflow easier to debug because the state transitions are explicit.

## What you get for free

You get an audit trail because every change carries agent attribution and a reason. You get replay because you can reconstruct any past state by replaying only part of the log. You get conflict history because `ConflictDetected` events preserve both competing patches.

You also get recovery because checkpoints and the event log work together for fault tolerance. If a workflow fails halfway through, you can restore the latest checkpoint and continue from there.

## How to read the log

You can load a workflow’s events from the store and inspect them directly:

```python
events = await store.get_workflow(workflow_id)
```

Then filter for the event types you care about:

```python
patches = [e for e in events if isinstance(e, PatchApplied)]
```

A useful thing to inspect is the `reason` field on `PatchApplied` events, because it tells you what each agent thought it was doing at the time. That often makes the difference between “something changed” and “now I know why it changed”.

You can also look at `ConflictDetected` events to see both versions of a disputed update. That gives you a complete story of the disagreement instead of only the final winner.