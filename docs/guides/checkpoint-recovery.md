# Checkpoint and Recovery

Checkpoints give you a way to save the current `SharedState` to disk so a long workflow can resume after failure without starting over from scratch. They are most useful when the workflow is expensive, long-running, or running in an environment where interruptions are likely.

## When to use checkpoints

Use checkpoints for long workflows where failure near the end would be expensive to recover from. They are also a good fit for workflows that call paid APIs, because you do not want to repeat work you already paid for. If you are running on unreliable hardware or a flaky environment, checkpoints give you a recovery point instead of a full restart.

A checkpoint is especially valuable when the workflow has already built up a lot of state, artifacts, or decisions. In that case, losing progress means more than just rerunning a few cheap steps.

## Saving a checkpoint

```python
cp = await save_checkpoint(final_state, store)
```

Saving a checkpoint writes the full `SharedState` to disk as JSON. The checkpoint also stores `event_count`, which marks how far the workflow had progressed in the event store at the moment the snapshot was taken. That makes the checkpoint a snapshot of state plus a pointer to the event log position it came from.

You can treat the checkpoint as a recovery bookmark: the state lives in the checkpoint file, and the event log tells you how much history had already happened.

## Recovering a workflow

```python
loaded = load_latest_checkpoint(workflow_id)
```

When you need to recover, load the latest checkpoint for that workflow and resume from there. The `event_count` field tells you where the workflow had reached, so you can restart from that point instead of replaying the entire event history. That keeps recovery fast and avoids unnecessary reprocessing.

In practice, this means you can restore the last known good state, inspect it, and continue execution with the remaining agents. That is the same pattern you want for fault-tolerant multi-agent workflows: store the full snapshot, keep the event history, and resume from the latest safe point.