# Patches

## What a patch is

A patch is a proposal, not a write. An agent does not change `SharedState` directly; it returns a `StatePatch` that describes the change it wants to make.

That separation matters because it keeps every mutation explicit and reviewable. Instead of silently changing state, the workflow can inspect, validate, and log every proposed update before it becomes part of the shared world.

## Why agents propose instead of write

Agents propose patches so the system can preserve an audit trail, detect conflicts, and support replay. If state changes were applied directly by agents, you would lose the ability to reconstruct why a value changed or which agent caused it.

Proposal-based writes also make parallel execution safe. Multiple agents can work against the same snapshot, and the library can decide which patch wins instead of letting later writes overwrite earlier ones invisibly.

## The patch pipeline

The patch flow is simple:

1. An agent returns a patch.
2. The conflict detector checks whether any patch targets the same path as another patch in the same round.
3. `apply_patch()` applies the winning patch to the current state.
4. Invariants run against the updated state.
5. The result becomes the next shared state snapshot.

This pipeline keeps mutation controlled and observable. It also means a failed invariant or a conflict can be handled explicitly instead of causing hidden corruption.

## Dotted target paths

`target` uses dotted paths to point into nested dictionaries. Each segment walks one level deeper into the state.

Examples:

- `facts.plan`
- `goals.primary.status`
- `tasks.task_1.description`
- `artifacts.summary.content`

In practice, this lets agents update precise parts of the shared world. You can patch a single fact, a task status, or an artifact field without replacing the whole object.

## Priority in conflicts

When two patches collide, `priority` helps the resolver choose between them. Higher priority patches can be favored over lower priority patches, depending on the configured conflict resolution strategy.

That gives you a way to encode policy into the workflow. For example, a coordinator agent might have higher priority than a worker agent, or a human-approved patch might outrank an automatically generated one.

Without agentstatelib, agent B silently overwrites agent A's work. With agentstatelib, the conflict is detected, resolved by your configured strategy, and logged.