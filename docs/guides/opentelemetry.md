# OpenTelemetry guide

## Step 1: Install and start Jaeger

Run Jaeger locally with the all-in-one container:

```bash
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest
```

Open `http://localhost:16686` to verify the Jaeger UI is running.

## Step 2: Install the OTel extra

Install the tracing dependencies:

```bash
pip install agentstate-lib[otel]
```

## Step 3: Configure tracing

Call `setup_tracing(service_name="my-app")` once before any `graph.run()` call.

```python
from agentstatelib.observability.tracing import setup_tracing

setup_tracing(service_name="my-app")
```

No other code changes are needed. Once tracing is configured, the graph instrumentation emits spans automatically.

## Step 4: Run a workflow

Run your workflow normally.

As the graph executes, it emits spans for the workflow, each round, and each agent call.

## Step 5: Read the trace

Open Jaeger in your browser.

Select your service from the service dropdown, find a trace, and open the waterfall view.

The span hierarchy should read like this:

- Parent span: the workflow.
- Child spans: the rounds.
- Grandchild spans: the individual agent calls.

## Step 6: What to look for

In the trace waterfall, check:

- Which agent span has the longest duration. That is usually the slowest model call.
- Which rounds have `conflict_count > 0`.
- Which agent spans have `success=False`.

These are the most useful signals when debugging slow or failing workflows.

## Production backends

You can point the same tracing setup at production backends.

For Datadog, change the exporter endpoint to:

```text
https://trace.agent.datadoghq.com
```

and add the API key header required by your Datadog setup.

For Honeycomb, use:

```text
https://api.honeycomb.io:443/
```

with the Honeycomb API key header.

## WorkflowSummary

You can also analyze the event log after a run:

```python
from agentstatelib.observability.analysis import analyze_workflow

summary = analyze_workflow(events)
```

`summary.workflow_id` identifies the run.

`summary.total_duration_seconds` is the total runtime.

`summary.total_patches` is the total number of patch applications.

`summary.total_conflicts` is the number of conflicts detected.

`summary.conflict_rate` is `total_conflicts / max(total_patches, 1)`.

`summary.agent_stats` contains per-agent patch and error counts.

`summary.is_anomalous` tells you whether the summary contains any error-severity anomaly flags.

`summary.anomaly_flags` contains the specific warnings or errors raised by the analyzer.

A typical check looks like this:

```python
if summary.is_anomalous:
    for flag in summary.anomaly_flags:
        print(flag.rule_name, flag.description, flag.severity)
```

That gives you a fast, post-run view of workflow health without opening the trace UI.