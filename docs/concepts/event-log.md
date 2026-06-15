# Event Log

The event log is the source of truth for a workflow. Instead of mutating shared state directly, agents append typed events that describe what changed and why. `SharedState` is derived from that history, not stored as a separate mutable blob.

## What the event log is

The event log is an append-only sequence of typed events. Every state change, conflict, checkpoint, error, model call, and human approval decision produces an event. Events are immutable once written, which makes the log safe to inspect, replay, and audit later.

In practice, that means your workflow history is a record of facts, not a pile of overwritten state. If something goes wrong, you do not lose the path that led there.

## The 16 event types

Events are organized into five families:

### Workflow lifecycle

| Event | When emitted |
|-------|-------------|
| `WorkflowStarted` | `AgentGraph.run()` begins. Carries `workflow_id`, `workflow_type`, `goal`. |
| `WorkflowCompleted` | `AgentGraph.run()` finishes. Carries `final_status`. |

### State changes

| Event | When emitted |
|-------|-------------|
| `PatchApplied` | A winning patch is applied to state. Carries `target`, `old_value`, `new_value`, `reason`. |
| `ConflictDetected` | Two patches target the same path in the same round. Carries both patches and the winner's `agent_id`. |
| `CheckpointSaved` | `save_checkpoint()` completes. Carries `checkpoint_id`, `event_count`. |

### Agent execution trace

| Event | When emitted |
|-------|-------------|
| `ContextSliced` | Agent context is prepared. Records which paths were included and `context_size_bytes`. |
| `PromptAssembled` | Full prompt text assembled before a model call. `is_correction_attempt` is true on retries. |
| `ModelCalled` | Immediately before an API call. `call_id` links to `ModelReturned`. |
| `ModelReturned` | After the API call returns. Carries raw response, `latency_seconds`, tokens, estimated cost. |
| `ValidationFailed` | Model output failed JSON or schema validation. Carries `raw_output` and `error_type`. |
| `RetryAttempted` | Correction attempt starts. Carries `previous_error` that was appended to the retry prompt. |
| `AgentErrored` | Agent raised an unhandled exception. Carries `error_type`, `error_message`, `retry_count`. |

### Tool use

| Event | When emitted |
|-------|-------------|
| `ToolCalled` | Agent invokes an external tool. Carries `tool_name`, `tool_input`, `tool_call_id`. |
| `ToolReturned` | Tool call completes. Carries `success`, `result_summary`, `latency_seconds`. |

### Human control

| Event | When emitted |
|-------|-------------|
| `HumanApprovalRequested` | Graph pauses at an approval gate. Carries `approval_id`, `description`, `pending_patch`. |
| `HumanApprovalResolved` | Human submits a decision. Carries `decision` (`approved`/`rejected`/`modified`). |

All events share the base fields: `event_id`, `workflow_id`, `agent_id`, `timestamp`, `schema_version`.

## State as a projection

`SharedState` is a projection of the event log. That means the current state can be reconstructed from events instead of being stored directly:

```python
from agentstatelib import replay

current_state = replay(all_events)
```

This is event sourcing applied to AI workflow coordination. The state you see is the result of replaying the workflow's history in order. Replay ignores all trace events and only processes `WorkflowStarted` and `PatchApplied`.

## What you get for free

You get an audit trail because every change carries agent attribution and a reason. You get replay because you can reconstruct any past state by replaying only part of the log. You get conflict history because `ConflictDetected` events preserve both competing patches.

You also get recovery because checkpoints and the event log work together. If a workflow fails halfway through, you can restore the latest checkpoint and continue from there.

## How to read the log

Load a workflow's events from the store:

```python
events = await store.get_workflow(workflow_id)
```

Filter for the event types you care about:

```python
from agentstatelib import PatchApplied, ConflictDetected, ModelReturned

patches = [e for e in events if isinstance(e, PatchApplied)]
conflicts = [e for e in events if isinstance(e, ConflictDetected)]
model_calls = [e for e in events if isinstance(e, ModelReturned)]
```

The `reason` field on `PatchApplied` events tells you what each agent thought it was doing. `ConflictDetected` events preserve both versions of the dispute. `ValidationFailed` events preserve the exact model output that failed parsing.

## Serialization

Every event serializes to and from JSON via Pydantic. The `type` field is a discriminator that lets `event_adapter` reconstruct the correct subclass:

```python
from agentstatelib import event_adapter

json_str = event.model_dump_json()
recovered = event_adapter.validate_json(json_str)
assert type(recovered) is type(event)
```

This is how SQLiteStore and PostgreSQLStore persist and restore typed events.

## Replay guarantee

State replay depends only on `WorkflowStarted` and `PatchApplied`. All other events are metadata for debugging and observability. Adding new trace event types in future versions never breaks existing replay code.

See the [Replay Debugger guide](../guides/replay-debugger.md) for step-through inspection.
