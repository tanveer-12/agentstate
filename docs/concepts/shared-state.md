# SharedState

## What SharedState is

SharedState is the shared world model all agents in a workflow read from. It is the "blackboard that all agents can read and propose updates to."

## Why you never mutate it directly

You never change SharedState in place. Every update goes through `StatePatch` → `apply_patch` → a new `SharedState` object, and the original snapshot stays immutable. That gives you an audit trail, replayability, and conflict detection because every mutation is explicit and recorded.

## The fields

- `goals`: Use this when you want to track multiple high-level objectives, such as "research competitors" and "draft proposal."
- `tasks`: Use this for concrete units of work, such as "summarize source A" or "verify citation links."
- `artifacts`: Use this for outputs created by agents, such as a draft paragraph, a code snippet, or a summary document.
- `facts`: Use this for durable structured knowledge, such as "preferred model is Claude" or "deadline is Friday."
- `decisions`: Use this for records of choices, such as "we will use SQLite for v0.1" or "reject patch B."

## Code example

```python
from agentstatelib.core.state import SharedState

state = SharedState(goal="Build agentstate")
# patch = StatePatch(target="facts.owner", value="agentstate")
# new_state = apply_patch(state, patch)

assert state.goal == "Build agentstate"
# assert new_state is not state
```

## What's next

See the [Patches](./patches.md) concept page.