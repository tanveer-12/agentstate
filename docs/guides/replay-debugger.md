# Replay Debugger

The replay debugger helps you inspect a workflow after it has produced the wrong answer. Instead of guessing where things went wrong, you step through the event log and watch state evolve one event at a time.

## A debugging story

Imagine a workflow completed successfully, but the final answer is wrong. The normal state is gone by the time you notice the issue, but the event log still contains everything that happened. That is the point of the replay debugger: it lets you recover intermediate state that would otherwise be lost.

## Get the events

Start by loading the events for the workflow from the store:

```python
events = await store.get_workflow(workflow_id)
```

These events are the source of truth for the run. Once you have them, you can replay the workflow exactly as it happened.

## Step through history

Create a debugger from the event list:

```python
debugger = ReplayDebugger(events)
```

Then step through the workflow one event at a time:

```python
while True:
    try:
        event, state = debugger.step()
        print(event.type, state.facts)
    except StopIteration:
        break
```

This makes it easy to find the moment the wrong value first appeared. Once you know which event introduced the bad state, you can inspect its `reason`, `agent_id`, and target path.

## Jump to a moment

Sometimes you already know when the bug happened, such as the timestamp of a conflict or suspicious patch. In that case, use `state_at(timestamp)` to reconstruct the state at that exact moment:

```python
state = debugger.state_at(timestamp)
```

That is useful when you want to check what the workflow looked like just before or just after a conflict. It gives you a quick way to inspect a specific point in time without replaying the whole log manually.

## Why this matters

The replay debugger turns your event log into a practical debugging tool. It is not just history storage; it is a way to understand how the workflow reached a bad result. In LangGraph, once a run completes intermediate states are gone. In agentstatelib every intermediate state is recoverable.