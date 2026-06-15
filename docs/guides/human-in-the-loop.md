# Human in the Loop

Approval gates let a workflow pause at a risky edge and wait for human review before applying a patch. They are a good fit for workflows that touch financial data, send external communications, make irreversible changes, or operate in regulated domains.

## Section 1 — When to use approval gates

Use approval gates when a patch is costly, irreversible, or hard to undo. Common examples include transferring money, sending customer-facing email, deleting data, changing production infrastructure, or taking an action that needs auditability and review.

Approval gates are not for routine state updates. If a patch is low risk and easily reversible, let the graph apply it automatically so the workflow stays fast and simple.

A good rule of thumb is this: if a human would reasonably ask "should this really happen?" before the system applies the change, it should probably be gated.

## Section 2 — Registering a gate

Register a gate on an edge by passing `approval_required` to `graph.edge()`. The predicate receives the current `SharedState` and the proposed `StatePatch`, and returns `True` when the patch should pause for human review.

```python
from agentstatelib import AgentGraph, SharedState, StatePatch

graph = AgentGraph()

graph.edge(
    "planner",
    "executor",
    condition=lambda state: state["status"] == "ready",
    approval_required=lambda state, patch: (
        patch.target.startswith("financial.")
        or patch.target in {"email.subject", "email.body"}
        or patch.target.startswith("production.")
    ),
)
```

You can make the predicate as specific as you need. For example, gate only when the target is a sensitive path and the proposed value crosses a threshold, or when the patch would modify a field in a regulated object.

## Section 3 — The approval flow

When the graph reaches a gated edge, the graph does **not** stop entirely. It:

1. Emits `HumanApprovalRequested` to the event store with the proposed patch embedded.
2. Stores the pending approval in `graph.pending_approvals` (keyed by `approval_id`).
3. Skips applying that patch and continues processing any other non-gated patches in the same round.

The pending patch sits in `graph.pending_approvals` until `resume_from_approval` is called — either by a human via the web dashboard/API, or programmatically by another agent or policy service.

```python
# Pause — graph run finishes without applying the gated patch
final_state = await graph.run(state, start="planner")

# The gated patch is waiting:
print(graph.pending_approvals)
# {'appr_abc123': PendingApproval(workflow_id=..., patch=StatePatch(...), ...)}
```

## Section 4 — Resolving approvals

### Via the REST API

The web server exposes three approval endpoints (all require `x-api-key` authentication):

```
GET  /v1/workflows/{workflow_id}/approvals
POST /v1/workflows/{workflow_id}/approvals/{approval_id}
```

**List pending approvals:**

```bash
curl -H "x-api-key: $KEY" \
  http://localhost:8000/v1/workflows/$WF_ID/approvals
```

```json
{
  "approvals": [
    {
      "approval_id": "appr_abc123",
      "workflow_id": "...",
      "agent_id": "planner",
      "description": "Transfer $500 to account 99",
      "patch": {"target": "financial.balance", "value": -500, ...}
    }
  ],
  "count": 1
}
```

**Approve:**

```bash
curl -X POST -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved"}' \
  http://localhost:8000/v1/workflows/$WF_ID/approvals/appr_abc123
```

**Reject:**

```bash
curl -X POST -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"decision": "rejected", "reason": "amount exceeds policy limit"}' \
  http://localhost:8000/v1/workflows/$WF_ID/approvals/appr_abc123
```

**Modify and approve:**

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
  http://localhost:8000/v1/workflows/$WF_ID/approvals/appr_abc123
```

### Via `resume_from_approval` (programmatic)

```python
# Approve — returns the updated SharedState
new_state = await graph.resume_from_approval(
    approval_id="appr_abc123",
    decision="approved",
    modified_patch=None,
)

# Reject — returns None
result = await graph.resume_from_approval(
    approval_id="appr_abc123",
    decision="rejected",
    modified_patch=None,
)

# Modify
from agentstatelib import StatePatch

new_state = await graph.resume_from_approval(
    approval_id="appr_abc123",
    decision="modified",
    modified_patch=StatePatch(
        agent_id="policy_service",
        target="financial.balance",
        value=-100,
        reason="capped at policy limit",
    ),
)
```

`resume_from_approval` always:
- Pops the approval from `graph.pending_approvals`.
- Emits `HumanApprovalResolved` to the event store.
- If approved or modified: applies the patch, emits `PatchApplied`, and returns the new `SharedState`.
- If rejected: discards the patch and returns `None`.
- Raises `KeyError` if the `approval_id` is not found.

## Section 5 — Web dashboard integration

The web dashboard (served at `/dashboard`) shows:

- **Notification banner** — appears at the top when there are pending approvals for the selected workflow.
- **Badge** — a yellow `●` marker on workflow items in the sidebar that have pending approvals.
- **Highlighted rows** — approval-related turns in the Trace tab are highlighted in amber.
- **Approval modal** — click Review in the banner to open the modal, which shows:
  - `approval_id` and producing `agent_id`
  - patch target, current value (before), proposed value (after)
  - Approve / Reject / Modify + Approve actions

The dashboard polls `GET /v1/workflows/{id}/approvals` on every workflow selection and on a 5-second interval when a workflow is selected.

## Section 6 — Event trail

Every approval leaves a complete, ordered trace in the event log:

| Event | When emitted |
|-------|-------------|
| `HumanApprovalRequested` | When the graph skips a gated patch and waits |
| `HumanApprovalResolved` | When `resume_from_approval` is called |
| `PatchApplied` | If the decision was `approved` or `modified` |

These events are queryable via `GET /v1/workflows/{id}/events-list` and visible in the Trace and Detail tabs of the web dashboard.

## Section 7 — Patterns

### Timeout auto-rejection

```python
import asyncio
from agentstatelib import AgentGraph

async def auto_reject_stale(graph: AgentGraph, timeout_seconds: float = 3600.0) -> None:
    """Reject any approval that has been pending longer than timeout_seconds."""
    await asyncio.sleep(timeout_seconds)
    for approval_id in list(graph.pending_approvals):
        await graph.resume_from_approval(
            approval_id=approval_id,
            decision="rejected",
            modified_patch=None,
        )
```

### Policy service auto-approval

```python
async def policy_check(graph: AgentGraph) -> None:
    for approval_id, pending in list(graph.pending_approvals.items()):
        patch = pending.patch
        if patch.target.startswith("financial.") and abs(patch.value) < 50:
            # Low-risk: auto-approve small transactions
            await graph.resume_from_approval(
                approval_id=approval_id,
                decision="approved",
                modified_patch=None,
            )
```

### Second-agent approval

You can run a second "reviewer" agent that reads the pending approval from the event log, decides, and calls `resume_from_approval`. This gives you a fully automated multi-stage approval pipeline while keeping the same approval primitive.
