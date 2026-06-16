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

Agentstatelib does not issue API keys or run a hosted service. You configure
valid keys yourself — this works much like a database password.

### Option A — generate via the API

The server exposes an unauthenticated endpoint so a fresh deployment can
bootstrap itself:

```bash
curl -X POST http://localhost:8000/v1/keys/generate
```

Response:

```json
{
  "key": "abc123...",
  "note": "Add this key to AGENTSTATE_API_KEYS on your server. Example: AGENTSTATE_API_KEYS=key1,key2"
}
```

Add the returned key to the server's environment and restart:

```bash
export AGENTSTATE_API_KEYS=abc123...
```

### Option B — generate locally

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Activating a key

Set the `AGENTSTATE_API_KEYS` environment variable to a comma-separated list
of valid keys before starting the server:

```bash
AGENTSTATE_API_KEYS=key1,key2,key3
```

Multiple keys support key rotation — add a new key while old clients continue
using the previous one, then remove the old key when all clients have updated.

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
  "version": "0.5.0"
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

### Export workflow (download JSON)

Downloads the complete event log plus final reconstructed state as a JSON
file. Useful for archiving, debugging, or sharing a run.

```bash
curl \
  -H "x-api-key: your-key-here" \
  -o "workflow_WF_ID.json" \
  http://localhost:8000/v1/workflows/WF_ID/export
```

The response sets `Content-Disposition: attachment` so browsers prompt to
save the file. The dashboard's **Download JSON** button uses this endpoint.

Export schema:

```json
{
  "workflow_id": "wf_3a9c2f1b4e8d",
  "exported_at": 1718500000.0,
  "event_count": 42,
  "final_state": { ... },
  "events": [ ... ]
}
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

Register an approval gate on a graph edge. When the gate fires, the graph pauses and emits `HumanApprovalRequested`. The pending patch sits in `graph.pending_approvals` until resolved via the API.

```python
graph.edge(
    "planner",
    "executor",
    condition=lambda s: s.get("status") == "ready",
    approval_required=lambda state, patch: patch.target.startswith("financial."),
)
```

The approval flow:

```text
AgentGraph.run()
     │
     ▼ (approval_required fires)
HumanApprovalRequested emitted
     │
     ▼
GET /v1/workflows/{id}/approvals   ← reviewer lists pending approvals
     │
     ▼
POST /v1/workflows/{id}/approvals/{approval_id}   ← reviewer decides
     │
     ▼
HumanApprovalResolved + PatchApplied emitted
```

### List pending approvals

```bash
curl -H "x-api-key: $KEY" \
  http://localhost:8000/v1/workflows/$WF_ID/approvals
```

### Approve

```bash
curl -X POST -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved"}' \
  http://localhost:8000/v1/workflows/$WF_ID/approvals/$APPROVAL_ID
```

### Reject

```bash
curl -X POST -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"decision": "rejected", "reason": "amount exceeds policy"}' \
  http://localhost:8000/v1/workflows/$WF_ID/approvals/$APPROVAL_ID
```

### Modify and approve

```bash
curl -X POST -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "modified",
    "modified_patch": {
      "agent_id": "human",
      "target": "financial.balance",
      "value": -100,
      "reason": "capped at policy limit"
    }
  }' \
  http://localhost:8000/v1/workflows/$WF_ID/approvals/$APPROVAL_ID
```

See the [Human in the Loop guide](human-in-the-loop.md) for programmatic resolution, event trail details, and patterns like timeout auto-rejection.
