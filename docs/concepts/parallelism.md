# Parallel Execution

## The round model

Every call to `graph.run()` executes as a sequence of **rounds**.

A round represents a set of agents that are eligible to run at the same time based on the current state and graph topology.

The execution cycle for each round is:

1. Determine which agents should run.
2. Execute all of them concurrently against the same state snapshot.
3. Collect all returned patches.
4. Resolve any path conflicts.
5. Apply the winning patches.
6. Run invariant checks.
7. Compute the next round.
8. Repeat until no agents remain runnable.

Conceptually:

```text
Round N
│
├─ Agent A
├─ Agent B
└─ Agent C
       │
       ▼
 Resolve conflicts
       │
       ▼
 Apply winners
       │
       ▼
 Check invariants
       │
       ▼
 Compute Round N+1
```

A critical property of the model is that all agents in a round receive the **same state snapshot**.

For example:

```python
state.facts["counter"] = 42
```

If two agents run in the same round:

```text
Round 1
├─ agent_a
└─ agent_b
```

both agents see:

```python
ctx["facts"]["counter"] == 42
```

Neither agent can observe modifications produced by the other.

Those updates are not visible until the round finishes and the winning patches have been applied.

In other words:

> No agent in a round sees another agent's updates until the next round.

This makes round execution deterministic and easy to reason about.

---

## Why this matters

The round model eliminates a large class of race conditions that commonly appear in concurrent systems.

Imagine two agents both reading:

```python
facts.counter
```

and making decisions based on its value.

Without snapshot isolation:

```text
agent_a reads counter
agent_b updates counter
agent_a continues
```

the behavior depends on timing.

With agentstatelib's round model:

```text
agent_a reads counter=42
agent_b reads counter=42
```

Both agents receive identical inputs regardless of scheduling order.

Benefits include:

* No read-write races within a round
* Deterministic agent inputs
* Easier debugging
* Reproducible execution
* Explicit conflict handling

When multiple agents attempt to update the same state path, the collision is detected and recorded rather than silently overwritten.

The result is a workflow model that behaves more like a transactional system than a collection of independently mutating coroutines.

---

## Fan-out topology

A fan-out occurs when one agent triggers multiple downstream agents.

Example:

```text
coordinator
     │
 ┌───┴───┐
 ▼       ▼
analyst_a analyst_b
```

The coordinator runs first.

When it completes, both analysts become eligible for the next round.

This topology is created with two edges:

```python
graph.edge("coordinator", "analyst_a")
graph.edge("coordinator", "analyst_b")
```

Execution timeline:

```text
Round 1
└─ coordinator

Round 2
├─ analyst_a
└─ analyst_b
```

Suppose the coordinator produces:

```python
StatePatch(
    target="facts.started",
    value=True,
)
```

That patch is applied at the end of Round 1.

When Round 2 begins, both analysts receive a state snapshot that already contains:

```python
facts.started == True
```

The coordinator's update is visible to every agent in the next round.

---

## Fan-in

A fan-in occurs when multiple upstream agents converge into a single downstream agent.

Example:

```text
analyst_a ──┐
            │
            ▼
       aggregator
            ▲
            │
analyst_b ──┘
```

Edges:

```python
graph.edge("analyst_a", "aggregator")
graph.edge("analyst_b", "aggregator")
```

Execution timeline:

```text
Round 1
└─ coordinator

Round 2
├─ analyst_a
└─ analyst_b

Round 3
└─ aggregator
```

Notice that the aggregator only runs once.

Even though two edges point to it, the graph computes the next round by collecting all reachable agents and removing duplicates.

Internally, `_next_round()` deduplicates reachable nodes before execution begins.

Conceptually:

```text
analyst_a → aggregator
analyst_b → aggregator

Next round candidates:
[aggregator, aggregator]

After deduplication:
[aggregator]
```

This guarantees that a downstream aggregation step executes exactly once per round.

---

## Parallel start

Execution does not have to begin with a single agent.

You can launch multiple agents in Round 1 by passing a list:

```python
await graph.run(
    state,
    start=["agent_a", "agent_b"],
)
```

Execution:

```text
Round 1
├─ agent_a
└─ agent_b
```

Both agents run concurrently against the same initial state snapshot.

This is useful when:

* Multiple independent workflows should begin immediately
* Several analysis agents can start from the same input
* A coordinator step is unnecessary

If the agents update different state paths, both patches are applied normally.

If they update the same path, the conflict resolution system handles the collision.

---

## The semaphore

Agent execution is controlled by an `asyncio.Semaphore`.

The semaphore is configured through the `max_concurrent` parameter on `AgentGraph`.

```python
graph = AgentGraph(
    max_concurrent=10,
)
```

The default value is:

```python
max_concurrent = 10
```

This limits the total number of agent coroutines that may execute simultaneously.

For example:

```text
Round contains 50 agents
max_concurrent = 10
```

Only ten agents run at a time.

As agents finish, additional agents acquire semaphore slots and begin execution.

This mechanism protects external systems from excessive concurrency.

A lower value is often useful when agents make:

* LLM API calls
* Database requests
* Web requests
* External service calls

Example:

```python
graph = AgentGraph(
    max_concurrent=3,
)
```

This can help stay within provider rate limits while preserving the round-based execution model.

The semaphore affects **how many agents run concurrently**, but it does **not** change round semantics.

All agents in a round still observe the same state snapshot, conflicts are still resolved at the round boundary, and invariants are still checked after the winning patches are applied.
