# Observability Guide

agentstatelib provides three observability signals that work together: the event log (always on), OpenTelemetry traces (optional), and workflow analysis (derived from the event log).

## The event log

The event log is automatic. Every graph run writes typed events to the configured store without any setup.

```python
from agentstatelib import SQLiteStore, AgentGraph

store = SQLiteStore("workflows.db")
graph = AgentGraph(store=store)
```

Read events after a run:

```python
events = await store.get_workflow(workflow_id)
for event in events:
    print(event.type, event.timestamp)
```

Filter for specific event types:

```python
from agentstatelib import PatchApplied, ConflictDetected

patches = [e for e in events if isinstance(e, PatchApplied)]
conflicts = [e for e in events if isinstance(e, ConflictDetected)]
```

## Workflow analysis

`analyze_workflow` aggregates the full event log into a `WorkflowSummary`:

```python
from agentstatelib import analyze_workflow

store = SQLiteStore("workflows.db")
events = await store.get_workflow(workflow_id)
summary = analyze_workflow(events)

print(f"Duration: {summary.total_duration_seconds:.1f}s")
print(f"Patches: {summary.total_patches}")
print(f"Conflicts: {summary.total_conflicts} ({summary.conflict_rate:.1%})")
print(f"Model calls: {summary.total_model_calls}")
print(f"Retries: {summary.total_retries}")
print(f"Tokens: {summary.total_input_tokens + summary.total_output_tokens}")
if summary.estimated_total_cost_usd is not None:
    print(f"Cost: ${summary.estimated_total_cost_usd:.4f}")
```

### Anomaly flags

`analyze_workflow` runs six rules automatically:

| Rule | Trigger |
|------|---------|
| `high_conflict_rate` | Conflict rate > 20% |
| `long_duration` | Duration > 300 seconds |
| `dead_agent` | Agent produced zero patches |
| `high_retry_rate` | Retries > 30% of model calls |
| `high_cost` | Estimated cost > $1.00 |
| `schema_drift` | Any `schema_validation_error` in ValidationFailed events |

```python
if summary.anomaly_flags:
    for flag in summary.anomaly_flags:
        print(f"[{flag.severity.upper()}] {flag.rule_name}: {flag.description}")
```

## OpenTelemetry traces

Install the optional dependency:

```bash
pip install "agentstate-lib[otel]"
```

Configure before creating the graph:

```python
from agentstatelib import setup_tracing

setup_tracing(
    service_name="my-agent-service",
    endpoint="http://localhost:4317",  # OTLP gRPC endpoint
)
```

The graph automatically instruments:

- `workflow.run` span — full graph run, tagged with `workflow.id`, `workflow.type`, `workflow.start_agents`
- `round` span — one per execution round, tagged with `round.agent_count`, `round.agents`, `round.conflict_count`
- `agent.<id>` span — one per agent call, tagged with `agent.id`, `agent.success`, `agent.patch_count`

If OTel is not installed, all spans are handled by a zero-overhead no-op tracer. No code changes needed.

See the [OpenTelemetry guide](opentelemetry.md) for Jaeger, Grafana Tempo, and OTLP configuration.

## Terminal dashboard

Install the optional dependency:

```bash
pip install "agentstate-lib[dashboard]"
```

```python
from agentstatelib import WorkflowDashboard, InMemoryStore

store = InMemoryStore()
dashboard = WorkflowDashboard(store=store)
await dashboard.run(workflow_id)
```

The terminal dashboard shows:
- Live event stream as the workflow runs
- Per-agent patch and error counts
- Conflict log with winner/loser attribution
- Retry and validation failure counts

If `rich` is not installed, `WorkflowDashboard` is importable but non-functional.

## Web dashboard

Start the API server:

```bash
pip install "agentstate-lib[api]"
$env:AGENTSTATE_API_KEYS = "your-key"
uvicorn agentstatelib.api.app:app --port 8000
```

Open `http://localhost:8000/dashboard` in a browser.

The web dashboard provides:
- **Workflow list** — sidebar listing all workflows by ID
- **Event stream** — live SSE feed of events as they arrive
- **Trace tab** — full event timeline with turn grouping
- **Turn detail** — prompt text, model responses, validation failures, tool calls, patch outcome
- **Approval panel** — notification banner and modal for pending approval gates
- **Workflow analysis** — conflict rate, patch count, duration, anomaly flags

## AgentTurn analysis

For fine-grained per-turn inspection, use `get_agent_turns`:

```python
from agentstatelib import get_agent_turns

events = await store.get_workflow(workflow_id)
turns = get_agent_turns(events)

for turn in turns:
    print(f"{turn.agent_id}: {turn.attempt_count} attempts, "
          f"{'ok' if turn.succeeded else 'FAILED'}, "
          f"{turn.total_latency_seconds:.2f}s, "
          f"{turn.total_tokens} tokens")
```

Each `AgentTurn` groups: `ContextSliced`, `PromptAssembled` list, `(ModelCalled, ModelReturned)` pairs, `ValidationFailed` list, optional `PatchApplied`, and `ToolCalled/ToolReturned` pairs.
