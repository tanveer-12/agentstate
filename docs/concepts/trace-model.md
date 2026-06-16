# Trace model

This guide explains the move from a simple state log to a full execution trace. In v0.x, the log told you what changed; in v1.x, it tells you what the agent saw, what it tried, what failed, and how it recovered .

## From state log

The early event log focused on outcomes such as `PatchApplied`, `ConflictDetected`, and workflow lifecycle events. That is enough to replay state, but not enough to debug why a workflow made a bad decision .

The trace model adds the missing context around each turn: `ContextSliced` shows what the agent could see, `PromptAssembled` shows what it was asked, `ModelReturned` shows what the model actually produced, and `ValidationFailed` plus `RetryAttempted` show where the recovery loop kicked in. `ToolCalled` and `ToolReturned` extend that story beyond the model boundary so you can see external side effects too.

## Event families

The event log is organized into five families so each kind of behavior has a clear job.

- Workflow lifecycle: `WorkflowStarted`, `WorkflowCompleted`.
- Agent execution: `ContextSliced`, `PromptAssembled`, `ModelCalled`, `ModelReturned`, `ValidationFailed`, `RetryAttempted`.
- Tool use: `ToolCalled`, `ToolReturned`.
- State changes: `PatchApplied`, `ConflictDetected`, `CheckpointSaved`.
- Human control: `HumanApprovalRequested`, `HumanApprovalResolved` [web:101].

That separation keeps the trace readable while preserving the one thing replay needs most: a clean distinction between metadata and state mutation .

## One agent turn

A single LLM-backed turn produces a chronological chain of events that reads like a story.

1. `ContextSliced` is emitted when the agent’s view of state is prepared.
2. `PromptAssembled` records the exact prompt sent to the model.
3. `ModelCalled` marks the API call start.
4. `ModelReturned` stores the raw response from the first attempt.
5. `ValidationFailed` records why that response could not be used.
6. `RetryAttempted` marks the start of the correction attempt.
7. `PromptAssembled` appears again for the retry prompt.
8. `ModelCalled` and `ModelReturned` happen again for the second attempt.
9. `PatchApplied` records the successful state change if the retry succeeds.

That order is what lets the terminal dashboard and web UI answer “what happened?” and “why did it happen?” instead of only “what changed?”.

## Replay guarantee

State replay depends only on the state-changing events, primarily `WorkflowStarted` and `PatchApplied`. The rest of the trace events are metadata for debugging, observability, and UI detail, but they do not alter reconstructed state .

This is the core compatibility promise: you can add new trace event types later without breaking old replay code, because replay ignores events that do not contribute to state . That makes the trace log richer over time without making the system less reliable.