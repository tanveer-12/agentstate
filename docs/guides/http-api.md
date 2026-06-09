# HTTP API

## When to use the HTTP API

The HTTP API is a transport layer around the same event-sourced runtime used by the Python library. It allows external processes, services, and user interfaces to interact with workflow state over HTTP.

Use the HTTP API when:

* Agents run in separate processes or machines.
* External systems need to query workflow state.
* External systems need to update workflow state.
* Streaming live workflow events to a browser-based dashboard.
* Building human-in-the-loop workflows where a person reviews and approves state changes.

Use the Python library directly when everything runs inside a single process. Direct library integration avoids network overhead and provides the simplest developer experience.

---

## API key model

The `x-api-key` header authenticates callers to **your own server**.

Agentstatelib does not issue API keys.

There is:

* No sign-up process.
* No hosted account.
* No central registry.
* No key management service.

You configure valid API keys yourself before starting the server.

This works much like a database password: whoever runs the server chooses the valid credentials.

Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Configure one or more valid keys:

```bash
AGENTSTATE_API_KEYS=key1,key2,key3
```

Multiple keys are useful for key rotation. A new key can be added while old clients continue using the previous key, allowing credentials to be rotated without downtime.

All protected endpoints require:

```http
x-api-key: your-key-here
```

---

## Running the server

Set one or more API keys:

### PowerShell

```powershell
$env:AGENTSTATE_API_KEYS = "your-key-here"
```

Start the server:

```bash
uvicorn agentstatelib.api.app:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/v1/health
```

Example response:

```json
{
  "status": "ok",
  "version": "0.2.0"
}
```

FastAPI automatically generates OpenAPI documentation:

```text
http://localhost:8000/docs
```

---

## Endpoint reference

### Health check

```bash
curl http://localhost:8000/v1/health
```

---

### List workflows

```bash
curl \
  -H "x-api-key: your-key-here" \
  http://localhost:8000/v1/workflows
```

Response:

```json
{
  "workflow_ids": [
    "wf-1",
    "wf-2"
  ],
  "count": 2
}
```

---

### Create workflow

```bash
curl \
  -X POST \
  -H "x-api-key: your-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Research event sourcing",
    "workflow_type": "research"
  }' \
  http://localhost:8000/v1/workflows
```

---

### Get workflow state

```bash
curl \
  -H "x-api-key: your-key-here" \
  http://localhost:8000/v1/workflows/WORKFLOW_ID
```

---

### Submit patch

```bash
curl \
  -X POST \
  -H "x-api-key: your-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "reviewer",
    "target": "facts.approved",
    "value": true,
    "reason": "Human review complete"
  }' \
  http://localhost:8000/v1/workflows/WORKFLOW_ID/patches
```

---

### Stream workflow events (header authentication)

Useful for curl, httpx, and backend services.

```bash
curl \
  -N \
  -H "x-api-key: your-key-here" \
  http://localhost:8000/v1/workflows/WORKFLOW_ID/events
```

---

### Stream workflow events (query parameter authentication)

Required for browser EventSource connections.

```text
http://localhost:8000/v1/workflows/WORKFLOW_ID/events?key=your-key-here
```

---

### Get workflow event history

```bash
curl \
  -H "x-api-key: your-key-here" \
  http://localhost:8000/v1/workflows/WORKFLOW_ID/events-list
```

Response:

```json
{
  "events": [...],
  "count": 42
}
```

---

### Python httpx SSE example

```python
import httpx
import asyncio


async def main():
    async with httpx.AsyncClient(
        headers={
            "x-api-key": "your-key-here"
        }
    ) as client:

        async with client.stream(
            "GET",
            "http://localhost:8000/v1/workflows/WORKFLOW_ID/events",
        ) as response:

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    print(line)


asyncio.run(main())
```

---

## SSE streaming

Server-Sent Events (SSE) provide a lightweight way to stream workflow events from the server to a client over a single long-lived HTTP connection.

When new events are appended to a workflow, connected clients receive them immediately without repeatedly polling the server.

Browser example:

```javascript
const events = new EventSource(
  "/v1/workflows/WORKFLOW_ID/events?key=your-key-here"
);

events.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

The event endpoint returns:

```http
Cache-Control: no-cache
```

This prevents intermediaries and browsers from caching streaming responses.

It also returns:

```http
X-Accel-Buffering: no
```

This disables buffering in Nginx and compatible reverse proxies. Without this header, events may be accumulated and delivered in large batches instead of appearing immediately.

These headers are important when deploying behind:

* Nginx
* Cloud load balancers
* Reverse proxies
* API gateways

---

## Human-in-the-loop workflows

A common workflow pattern is:

1. Run an agent graph until a checkpoint is reached.
2. Expose the current workflow state to a human reviewer.
3. Let the reviewer inspect the workflow.
4. Allow the reviewer to submit an approved state change.
5. Resume execution using the updated workflow state.

Example flow:

```text
Agent Graph
     │
     ▼
Checkpoint
     │
     ▼
GET /v1/workflows/{id}
     │
     ▼
Human Review
     │
     ▼
POST /v1/workflows/{id}/patches
     │
     ▼
PatchApplied Event
     │
     ▼
Resume Graph Execution
```

This pattern enables:

* Human approval workflows.
* Compliance review steps.
* Escalation handling.
* Manual corrections.
* Expert-in-the-loop systems.

The ability to safely inject reviewed changes into an event-sourced workflow is one of the primary reasons to expose workflow state through the HTTP API.
