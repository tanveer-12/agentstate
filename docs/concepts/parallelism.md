# Parallel Execution

## The round model

agentstatelib runs in rounds. In every round, all runnable agents execute concurrently against the same state snapshot. No agent in a round sees another agent's updates until the next round begins.

That snapshot behavior is what makes round-based execution deterministic and auditable. Every patch in a round is based on the same input state.

## Why this matters

This model removes read-write races within a round. If two agents are both reasoning over the same state, they do not accidentally observe each other’s in-progress changes.

In sequential execution, agent B always sees agent A’s changes if B runs later. In agentstatelib, parallel agents do not get that hidden advantage inside the same round.

## Fan-out topology

A fan-out like `coordinator -> [analyst_a, analyst_b]` means the coordinator runs first, then both analysts become runnable in the next round.

Both analysts run in round 2 simultaneously. That is how you model independent subtasks that can be done in parallel.

## Fan-in

A fan-in like `[analyst_a, analyst_b] -> aggregator` means the aggregator runs only after both analysts have completed.

That places the aggregator in round 3 in the usual case: coordinator in round 1, analysts in round 2, aggregator in round 3. The aggregator sees the merged state after both analysts have contributed.

## Parallel start

You can start multiple agents at once with:

```python
await graph.run(state, start=["a", "b"])
```

This is useful when there is no single coordinator and you want several agents to begin from the same initial snapshot.

## The semaphore

`AgentGraph.__init__` accepts `max_concurrent`, which controls total concurrency across the graph. The default is `10`.

This does not change the round model. It only limits how many agent coroutines may execute at the same time, which is important for large graphs or resource-heavy agent functions.