# Observability

Most multi-agent frameworks are black boxes. You know what went in and what came out. agentstatelib is the opposite — every agent call, state change, conflict, and routing decision is recorded.

## Three signals

agentstatelib observability has three layers.

The event log is always on and records what happened: workflow start, patch application, conflicts, checkpoints, and errors.

OTel traces are optional and show how long each part took, which is what you use when you want a Jaeger waterfall for a specific run.

`WorkflowSummary` is computed from the event log and gives aggregate statistics like duration, patch volume, conflicts, and anomaly flags.

## The trace model

Datadog traces HTTP requests across microservices to help you find which service is slow or failing.

agentstatelib uses the same mental model for AI workflows: it traces agent calls across rounds to help you find which agent is slow, which agent is producing conflicts, and which agent is failing.

That matters because the coordination layer is where multi-agent systems actually coordinate work, and that is what your library owns.

The result is a glass-box workflow view instead of a chat-history blob.

## Why this is different

LangSmith is tied to the LangChain ecosystem, so its strongest tracing story is inside LangChain-style apps.

CrewAI and AutoGen do have observability features, but they are centered on their own frameworks and runtime concepts rather than a framework-agnostic coordination substrate.

agentstatelib is different because it instruments the coordination layer, not the model calls.

That makes the observability story portable across OpenAI, Anthropic, Ollama, llama.cpp, or any other callable agent backend.

## What to inspect

When a workflow looks wrong, start with the event log to see what actually happened.

Then open the trace to see which round or agent was slow or failed.

Finally, read `WorkflowSummary` to quickly spot high conflict rate, long runtimes, or dead agents.

This gives you one coherent observability stack for debugging, performance analysis, and recovery.