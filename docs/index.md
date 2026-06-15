agentstate gives multiple AI agents a shared, typed world to operate in, with structured state updates, conflict resolution, and an event-sourced audit log. It is framework-agnostic, works with local or hosted models, and is designed to make parallel agent workflows reliable, debuggable, and recoverable.

| Feature                    | agentstate | LangGraph | CrewAI | AutoGen |
|----------------------------|-----------|-----------|--------|----------|
| Typed shared state         | ✅        | ⚠️ dict   | ❌     | ❌     |
| Append-only event log      | ✅        | ❌        | ❌     | ❌     |
| Conflict detection         | ✅        | ❌        | ❌     | ❌     |
| Parallel round execution   | ✅        | ⚠️ limited| ❌     | ❌     |
| Replay debugger            | ✅        | ❌        | ❌     | ❌     |
| Framework agnostic         | ✅        | ❌        | ⚠️     | ⚠️     |
| Local model support        | ✅        | ⚠️        | ⚠️     | ⚠️     |
| Built-in observability     | ✅        | ❌        | ❌     | ❌     |
| Human-in-the-loop gates    | ✅        | ⚠️        | ❌     | ❌     |
| OpenTelemetry tracing      | ✅        | ❌        | ❌     | ❌     |

## Install

```bash
pip install agentstate-lib
```

Optional extras:

```bash
pip install "agentstate-lib[api]"        # FastAPI HTTP server + web dashboard
pip install "agentstate-lib[otel]"       # OpenTelemetry export
pip install "agentstate-lib[dashboard]"  # Rich terminal dashboard
pip install "agentstate-lib[contrib]"    # LLMAgent base class
```

## Import

```python
from agentstatelib import SharedState, AgentGraph, StatePatch
```

## Positioning

agentstate is the coordination layer that sits underneath multi-agent frameworks instead of replacing them. It focuses on shared typed state, auditable mutations, and recovery tooling so teams can build workflows that are easier to inspect, test, and trust.

## Current version

`v0.5.0` — Phase 2E complete. All features through human-in-the-loop approval gates are implemented and tested.

See [Quickstart](quickstart.md) to run your first workflow in under five minutes.
