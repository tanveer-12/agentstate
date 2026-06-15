"""Self-hosted web dashboard HTML for agentstatelib."""

from __future__ import annotations

DASHBOARD_HTML: str = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>agentstatelib dashboard</title>
  <style>
    :root {
      --bg: #0f1117;
      --surface: #1a1d27;
      --surface2: #252836;
      --border: #2d3142;
      --text: #e2e8f0;
      --muted: #718096;
      --green: #48bb78;
      --yellow: #ecc94b;
      --blue: #63b3ed;
      --red: #fc8181;
      --purple: #b794f4;
      --orange: #f6ad55;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      height: 100vh;
      overflow: hidden;
    }

    .approval-banner {
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 10px 16px;
      background: rgba(236, 201, 75, 0.12);
      color: #fef3c7;
      border-bottom: 1px solid rgba(236, 201, 75, 0.35);
      font-weight: 600;
    }

    .approval-banner.visible {
      display: flex;
    }

    #app {
      display: flex;
      height: calc(100vh - 0px);
      width: 100vw;
    }

    .sidebar {
      width: 280px;
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      padding: 18px 14px;
      gap: 14px;
      min-width: 280px;
    }

    .logo {
      font-size: 1.2rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      padding: 4px 8px 10px;
    }

    #workflow-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      overflow-y: auto;
      padding-right: 2px;
    }

    .workflow-item {
      padding: 10px 12px;
      border: 1px solid transparent;
      border-radius: 10px;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
      font-size: 0.92rem;
      word-break: break-word;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    .workflow-item:hover {
      background: var(--surface2);
      color: var(--text);
    }

    .workflow-item.selected {
      background: rgba(99, 179, 237, 0.12);
      color: var(--text);
      border-color: rgba(99, 179, 237, 0.35);
    }

    .workflow-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 20px;
      height: 20px;
      padding: 0 7px;
      border-radius: 999px;
      background: rgba(236, 201, 75, 0.15);
      color: var(--yellow);
      border: 1px solid rgba(236, 201, 75, 0.35);
      font-size: 0.75rem;
      font-weight: 700;
    }

    .main {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--border);
      background: rgba(26, 29, 39, 0.6);
      padding: 14px 16px 0;
    }

    .tab {
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-bottom: none;
      border-top-left-radius: 10px;
      border-top-right-radius: 10px;
      background: var(--surface);
      color: var(--muted);
      cursor: pointer;
      font-weight: 600;
    }

    .tab.active {
      color: var(--text);
      background: var(--bg);
    }

    #content {
      flex: 1;
      min-height: 0;
      overflow: auto;
      padding: 18px;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 16px;
    }

    .section-title {
      margin: 0 0 12px;
      font-size: 1rem;
    }

    .stats {
      color: var(--muted);
      font-size: 0.92rem;
      margin-bottom: 12px;
    }

    .timeline,
    .live-table {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .event-row {
      border-left: 3px solid var(--border);
      background: var(--surface2);
      border-radius: 10px;
      padding: 12px 14px;
      cursor: pointer;
    }

    .event-row[data-type="patch_applied"] { border-left-color: var(--green); }
    .event-row[data-type="conflict_detected"] { border-left-color: var(--yellow); }
    .event-row[data-type="workflow_started"],
    .event-row[data-type="workflow_completed"] { border-left-color: var(--blue); }
    .event-row[data-type="agent_errored"] { border-left-color: var(--red); }
    .event-row[data-type="human_approval_requested"] { border-left-color: var(--yellow); }
    .event-row[data-type="human_approval_resolved"] { border-left-color: var(--purple); }

    .approval-row {
      background: rgba(236, 201, 75, 0.08);
      border: 1px solid rgba(236, 201, 75, 0.28);
    }

    .event-header {
      display: grid;
      grid-template-columns: 88px 150px 170px 1fr;
      gap: 12px;
      align-items: center;
      font-size: 0.92rem;
    }

    .time {
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 0.8rem;
      width: fit-content;
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.03);
    }

    .type-badge { color: var(--text); }
    .winner-badge { color: var(--green); border-color: rgba(72, 187, 120, 0.35); }
    .loser-badge { color: var(--red); border-color: rgba(252, 129, 129, 0.35); }

    .details {
      display: none;
      margin-top: 12px;
      color: var(--muted);
      line-height: 1.5;
    }

    .event-row.open .details {
      display: block;
    }

    .detail-grid {
      display: grid;
      gap: 8px;
    }

    .detail-row strong {
      color: var(--text);
    }

    .json-block {
      white-space: pre-wrap;
      word-break: break-word;
      background: rgba(0,0,0,0.2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      margin-top: 8px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.85rem;
      color: #cbd5e1;
    }

    .replay-controls {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .replay-topline {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    input[type="range"] {
      width: 100%;
    }

    pre.state-view {
      margin: 0;
      overflow: auto;
      max-height: calc(100vh - 230px);
      background: var(--surface2);
      color: #dbeafe;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      font-size: 0.88rem;
      line-height: 1.5;
    }

    .placeholder {
      color: var(--muted);
      padding: 20px;
      border: 1px dashed var(--border);
      border-radius: 12px;
      background: rgba(255,255,255,0.02);
    }

    .trace-layout {
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 16px;
      min-height: 0;
    }

    .turn-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow-y: auto;
      max-height: calc(100vh - 170px);
    }

    .turn-card {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface2);
      padding: 12px;
      cursor: pointer;
      transition: border-color 0.15s ease, transform 0.15s ease;
    }

    .turn-card:hover {
      border-color: rgba(99, 179, 237, 0.35);
    }

    .turn-card.selected {
      border-color: rgba(99, 179, 237, 0.75);
      box-shadow: 0 0 0 1px rgba(99, 179, 237, 0.3) inset;
    }

    .turn-card.approval-turn {
      border-color: rgba(236, 201, 75, 0.55);
      background: rgba(236, 201, 75, 0.08);
    }

    .turn-card-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 6px;
    }

    .turn-card-title {
      font-weight: 700;
    }

    .turn-card-meta {
      color: var(--muted);
      font-size: 0.9rem;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .turn-detail {
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 0;
    }

    .turn-section {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface2);
      overflow: hidden;
    }

    .turn-section summary {
      list-style: none;
      cursor: pointer;
      padding: 12px 14px;
      font-weight: 700;
    }

    .turn-section summary::-webkit-details-marker {
      display: none;
    }

    .turn-section .section-body {
      padding: 0 14px 14px;
      color: var(--text);
    }

    .mono {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .copy-btn {
      margin-left: 10px;
      padding: 4px 8px;
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text);
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.8rem;
    }

    .prompt-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }

    .prompt-tab {
      padding: 6px 10px;
      border: 1px solid var(--border);
      border-radius: 999px;
      cursor: pointer;
      color: var(--muted);
      background: transparent;
      font-size: 0.85rem;
    }

    .prompt-tab.active {
      color: var(--text);
      border-color: rgba(99, 179, 237, 0.75);
      background: rgba(99, 179, 237, 0.12);
    }

    .border-green { border-color: rgba(72, 187, 120, 0.65) !important; }
    .border-red { border-color: rgba(252, 129, 129, 0.65) !important; }
    .border-yellow { border-color: rgba(236, 201, 75, 0.65) !important; }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border-radius: 999px;
      padding: 4px 8px;
      background: rgba(255,255,255,0.04);
      border: 1px solid var(--border);
      font-size: 0.8rem;
    }

    .tool-item {
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-top: 8px;
      background: rgba(255,255,255,0.02);
      overflow: hidden;
    }

    .tool-item summary {
      padding: 10px 12px;
      cursor: pointer;
      list-style: none;
      font-weight: 600;
    }

    .tool-item summary::-webkit-details-marker {
      display: none;
    }

    .tool-item .section-body {
      padding: 0 12px 12px;
    }

    .approval-modal {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }

    .approval-modal.visible {
      display: flex;
    }

    .modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.65);
    }

    .modal-card {
      position: relative;
      z-index: 1;
      width: min(980px, 96vw);
      max-height: 90vh;
      overflow: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 24px 90px rgba(0, 0, 0, 0.5);
      padding: 18px;
    }

    .modal-header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 14px;
    }

    .modal-title {
      font-size: 1.05rem;
      font-weight: 800;
    }

    .modal-close {
      border: 1px solid var(--border);
      background: transparent;
      color: var(--text);
      border-radius: 10px;
      padding: 8px 10px;
      cursor: pointer;
    }

    .modal-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .modal-panel {
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      background: var(--surface2);
    }

    .modal-panel h4 {
      margin: 0 0 10px;
      font-size: 0.95rem;
    }

    .modal-field {
      margin-bottom: 10px;
    }

    .modal-field label {
      display: block;
      font-size: 0.85rem;
      color: var(--muted);
      margin-bottom: 6px;
    }

    .modal-field input,
    .modal-field textarea {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgba(0,0,0,0.2);
      color: var(--text);
      padding: 10px 12px;
      font: inherit;
    }

    .modal-field textarea {
      min-height: 220px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }

    .modal-actions {
      display: flex;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 14px;
      flex-wrap: wrap;
    }

    .btn {
      border: none;
      border-radius: 10px;
      padding: 10px 14px;
      cursor: pointer;
      font-weight: 700;
      color: #0f1117;
    }

    .btn-approve { background: var(--green); }
    .btn-reject { background: var(--red); }
    .btn-modify { background: var(--yellow); }
    .btn-secondary {
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
    }

    .hidden {
      display: none !important;
    }
  </style>
</head>
<body>
  <div id="approval-banner" class="approval-banner">
    <div id="approval-banner-text">Pending approvals detected.</div>
    <button class="btn btn-secondary" onclick="refreshApprovals()">Refresh approvals</button>
  </div>

  <div id="app">
    <div class="sidebar">
      <div class="logo">agentstatelib</div>
      <div id="workflow-list"></div>
    </div>
    <div class="main">
      <div class="tabs">
        <div class="tab active" data-tab="detail">Detail</div>
        <div class="tab" data-tab="live">Live</div>
        <div class="tab" data-tab="replay">Replay</div>
        <div class="tab" data-tab="trace">Trace</div>
      </div>
      <div id="content"></div>
    </div>
  </div>

  <div id="approval-modal" class="approval-modal" aria-hidden="true">
    <div class="modal-backdrop" onclick="closeApprovalModal()"></div>
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title">Pending approval</div>
        <button class="modal-close" onclick="closeApprovalModal()">Close</button>
      </div>
      <div class="modal-grid">
        <div class="modal-panel">
          <h4>Patch details</h4>
          <div class="modal-field"><label>Approval ID</label><div id="modal-approval-id" class="mono"></div></div>
          <div class="modal-field"><label>Agent</label><div id="modal-agent" class="mono"></div></div>
          <div class="modal-field"><label>Target</label><div id="modal-target" class="mono"></div></div>
          <div class="modal-field"><label>Current value</label><pre id="modal-current" class="mono json-block"></pre></div>
          <div class="modal-field"><label>Proposed new value</label><pre id="modal-proposed" class="mono json-block"></pre></div>
          <div class="modal-field"><label>Reason</label><div id="modal-reason" class="mono"></div></div>
        </div>
        <div class="modal-panel">
          <h4>Review</h4>
          <div class="modal-field">
            <label>Decision reason</label>
            <input id="modal-review-reason" type="text" placeholder="Optional review note" />
          </div>
          <div id="modify-editor-wrap" class="modal-field hidden">
            <label>Modified value (JSON)</label>
            <textarea id="modal-modified-json"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn btn-approve" onclick="submitApprovalDecision('approved')">Approve</button>
            <button class="btn btn-reject" onclick="submitApprovalDecision('rejected')">Reject</button>
            <button class="btn btn-modify" onclick="showModifyEditor()">Modify</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const API_KEY = new URLSearchParams(window.location.search).get("key") || "dev-key-123";
    const BASE_URL = window.location.origin;

    let currentWorkflowId = null;
    let eventSource = null;
    let liveEvents = [];
    let allEvents = [];
    let detailState = {};
    let workflowStartTime = null;
    let currentTab = "detail";
    let traceTurns = [];
    let selectedTurnIndex = null;
    let pendingApprovals = [];
    let approvalIndex = new Map();
    let activeApproval = null;

    function apiFetch(path, options = {}) {
      const headers = new Headers(options.headers || {});
      headers.set("x-api-key", API_KEY);

      return fetch(`${BASE_URL}${path}`, {
        ...options,
        headers
      }).then(async (response) => {
        if (!response.ok) {
          let detail = null;
          try {
            detail = await response.json();
          } catch {
            detail = { message: response.statusText };
          }
          const message = detail?.detail?.message || detail?.message || response.statusText;
          throw new Error(message);
        }
        return response.json();
      });
    }

    function normalizeWorkflowList(payload) {
      if (Array.isArray(payload.workflow_ids)) return payload.workflow_ids;
      if (Array.isArray(payload.workflows)) return payload.workflows;
      return [];
    }

    function normalizeState(payload) {
      if (!payload) return {};
      if (payload.state && typeof payload.state === "object") return payload.state;
      return payload;
    }

    function normalizeEvents(payload) {
      if (!payload) return [];
      if (Array.isArray(payload.events)) return payload.events;
      return [];
    }

    function normalizeTurns(payload) {
      if (!payload) return [];
      if (Array.isArray(payload.turns)) return payload.turns;
      return [];
    }

    function formatTimestamp(ts) {
      if (!workflowStartTime || typeof ts !== "number") return "";
      return `${(ts - workflowStartTime).toFixed(1)}s`;
    }

    function formatJson(value) {
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    }

    function eventType(event) {
      return event.type || event.event_type || "event";
    }

    function eventSummary(type) {
      if (type === "patch_applied") return "Patch updated state";
      if (type === "conflict_detected") return "Conflict resolved";
      if (type === "workflow_started") return "Workflow started";
      if (type === "workflow_completed") return "Workflow completed";
      if (type === "agent_errored") return "Agent errored";
      if (type === "checkpoint_saved") return "Checkpoint saved";
      if (type === "human_approval_requested") return "Pending approval";
      if (type === "human_approval_resolved") return "Approval resolved";
      return "";
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function approvalKey(workflowId, approvalId) {
      return `${workflowId}:${approvalId}`;
    }

    function buildApprovalIndex(approvals) {
      approvalIndex = new Map();
      pendingApprovals = approvals || [];
      for (const item of pendingApprovals) {
        approvalIndex.set(approvalKey(item.workflow_id, item.approval_id), item);
      }
    }

    async function loadApprovals(workflowId) {
      if (!workflowId) return [];
      const payload = await apiFetch(`/v1/workflows/${workflowId}/approvals`);
      const approvals = Array.isArray(payload.approvals) ? payload.approvals : [];
      buildApprovalIndex(approvals);
      updateApprovalBanner();
      return approvals;
    }

    function updateApprovalBanner() {
      const banner = document.getElementById("approval-banner");
      const text = document.getElementById("approval-banner-text");
      if (!pendingApprovals.length) {
        banner.classList.remove("visible");
        text.textContent = "Pending approvals detected.";
        return;
      }
      banner.classList.add("visible");
      text.textContent = `${pendingApprovals.length} pending approval${pendingApprovals.length === 1 ? "" : "s"} across the selected workflow.`;
    }

    async function refreshApprovals() {
      if (!currentWorkflowId) return;
      await loadApprovals(currentWorkflowId);
      if (currentTab === "detail") renderDetailTab(allEvents, detailState);
      if (currentTab === "trace") renderTraceTab();
    }

    async function loadWorkflowList() {
      const data = await apiFetch("/v1/workflows");
      const workflowIds = normalizeWorkflowList(data);
      const list = document.getElementById("workflow-list");
      list.innerHTML = "";

      if (!workflowIds.length) {
        list.innerHTML = '<div class="placeholder">No workflows yet.</div>';
        currentWorkflowId = null;
        return;
      }

      for (const workflowId of workflowIds) {
        let badgeCount = "";
        try {
          const approvals = await apiFetch(`/v1/workflows/${workflowId}/approvals`);
          const count = Array.isArray(approvals.approvals) ? approvals.approvals.length : 0;
          badgeCount = count ? `<span class="workflow-badge">${count}</span>` : "";
        } catch {
          badgeCount = "";
        }

        const item = document.createElement("div");
        item.className = "workflow-item" + (workflowId === currentWorkflowId ? " selected" : "");
        item.innerHTML = `<span>${escapeHtml(workflowId)}</span>${badgeCount}`;
        item.onclick = () => selectWorkflow(workflowId);
        list.appendChild(item);
      }

      if (!currentWorkflowId || !workflowIds.includes(currentWorkflowId)) {
        selectWorkflow(workflowIds[0]);
      }
    }

    function selectWorkflow(workflowId) {
      currentWorkflowId = workflowId;
      document.querySelectorAll(".workflow-item").forEach((el) => {
        const text = el.querySelector("span")?.textContent || el.textContent;
        el.classList.toggle("selected", text === workflowId);
      });
      loadDetail(workflowId);
      if (currentTab === "live") startLiveView(workflowId);
      if (currentTab === "trace") loadTurns(workflowId);
    }

    async function loadDetail(workflowId) {
      const stateResp = await apiFetch(`/v1/workflows/${workflowId}`);
      const eventsResp = await apiFetch(`/v1/workflows/${workflowId}/events-list`);
      detailState = normalizeState(stateResp);
      allEvents = normalizeEvents(eventsResp);
      workflowStartTime = allEvents.length ? (allEvents[0].timestamp || null) : null;
      await loadApprovals(workflowId);
      if (currentTab === "detail") renderDetailTab(allEvents, detailState);
      if (currentTab === "replay") renderReplayTab(allEvents);
      if (currentTab === "trace") renderTraceTab();
    }

    function approvalMatchesEvent(event) {
      const key = approvalKey(currentWorkflowId, event.approval_id || "");
      return approvalIndex.has(key);
    }

    function renderDetailEvent(event) {
      const type = eventType(event);
      const color =
        type === "patch_applied" ? "var(--green)" :
        type === "conflict_detected" ? "var(--yellow)" :
        (type === "workflow_started" || type === "workflow_completed") ? "var(--blue)" :
        type === "agent_errored" ? "var(--red)" :
        (type === "human_approval_requested" ? "var(--yellow)" : "var(--border)");

      const isApproval = type === "human_approval_requested" && approvalMatchesEvent(event);

      let detailHtml = "";
      if (type === "patch_applied") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Target:</strong> ${escapeHtml(event.target || "")}</div>
            <div class="detail-row"><strong>Reason:</strong> ${escapeHtml(event.reason || "")}</div>
            <div class="detail-row"><strong>Old value:</strong><div class="json-block">${escapeHtml(formatJson(event.old_value))}</div></div>
            <div class="detail-row"><strong>New value:</strong><div class="json-block">${escapeHtml(formatJson(event.new_value))}</div></div>
          </div>
        `;
      } else if (type === "conflict_detected") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Path:</strong> ${escapeHtml(event.path || "")}</div>
            <div class="detail-row">
              <span class="badge winner-badge">Winner: ${escapeHtml(event.winner_agent_id || "")}</span>
              <span class="badge loser-badge">Loser: ${escapeHtml(event.loser_agent_id || "")}</span>
            </div>
            <div class="detail-row"><strong>Strategy:</strong> ${escapeHtml(event.resolution_strategy || "")}</div>
          </div>
        `;
      } else if (type === "human_approval_requested") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Approval ID:</strong> ${escapeHtml(event.approval_id || "")}</div>
            <div class="detail-row"><strong>Description:</strong> ${escapeHtml(event.description || event.reason || "")}</div>
            <div class="detail-row"><strong>Pending patch:</strong><div class="json-block">${escapeHtml(formatJson(event.pending_patch || event.patch || {}))}</div></div>
          </div>
        `;
      } else if (type === "human_approval_resolved") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Approval ID:</strong> ${escapeHtml(event.approval_id || "")}</div>
            <div class="detail-row"><strong>Decision:</strong> ${escapeHtml(event.decision || "")}</div>
          </div>
        `;
      } else if (type === "agent_errored") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Error type:</strong> ${escapeHtml(event.error_type || "")}</div>
            <div class="detail-row"><strong>Message:</strong> ${escapeHtml(event.error_message || "")}</div>
            <div class="detail-row"><strong>Retries:</strong> ${escapeHtml(event.retry_count ?? 0)}</div>
          </div>
        `;
      } else {
        detailHtml = `<div class="detail-row"><div class="json-block">${escapeHtml(formatJson(event))}</div></div>`;
      }

      const approvalClass = isApproval ? " approval-row" : "";
      const approvalAttr = isApproval ? `data-approval-id="${escapeHtml(event.approval_id || "")}" onclick="openApprovalByEvent('${escapeHtml(event.approval_id || "")}')" ` : `onclick="this.classList.toggle('open')"`; 
      return `
        <div class="event-row${approvalClass}" data-type="${escapeHtml(type)}" style="border-left-color: ${color};" ${approvalAttr}>
          <div class="event-header">
            <div class="time">${escapeHtml(formatTimestamp(event.timestamp || 0))}</div>
            <div><span class="badge">${escapeHtml(event.agent_id || "")}</span></div>
            <div><span class="badge type-badge">${escapeHtml(type)}</span></div>
            <div>${escapeHtml(eventSummary(type))}</div>
          </div>
          <div class="details">${detailHtml}</div>
        </div>
      `;
    }

    function renderDetailTab(events, state) {
      const content = document.getElementById("content");
      const html = [];
      html.push('<div class="panel">');
      html.push('<h3 class="section-title">Event timeline</h3>');
      html.push(`<div class="stats">${events.length} events</div>`);
      html.push('<div class="timeline">');
      if (!events.length) {
        html.push('<div class="placeholder">No events for this workflow yet.</div>');
      } else {
        events.forEach((event) => html.push(renderDetailEvent(event)));
      }
      html.push("</div>");
      html.push("</div>");
      html.push('<div class="panel">');
      html.push('<h3 class="section-title">Current state</h3>');
      html.push(`<pre class="state-view">${escapeHtml(formatJson(state))}</pre>`);
      html.push("</div>");
      content.innerHTML = html.join("");
    }

    function renderLiveRow(event) {
      const content = document.getElementById("content");
      const table = content.querySelector(".live-table");
      if (!table) return;

      const row = document.createElement("div");
      row.className = "event-row";
      row.dataset.type = eventType(event);
      row.style.borderLeftColor = row.dataset.type === "patch_applied" ? "var(--green)" : "var(--border)";
      row.innerHTML = `
        <div class="event-header">
          <div class="time">${escapeHtml(formatTimestamp(event.timestamp || 0))}</div>
          <div><span class="badge">${escapeHtml(event.agent_id || "")}</span></div>
          <div><span class="badge type-badge">${escapeHtml(eventType(event))}</span></div>
          <div>${escapeHtml(event.target || event.path || "")}</div>
        </div>
      `;
      table.prepend(row);
    }

    function renderLiveView() {
      const content = document.getElementById("content");
      content.innerHTML = `
        <div class="panel">
          <h3 class="section-title">Live events</h3>
          <div class="stats" id="live-stats">${liveEvents.length} live events</div>
          <div class="live-table"></div>
        </div>
      `;
      liveEvents.slice().reverse().forEach(renderLiveRow);
    }

    function stopLiveView() {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
    }

    function startLiveView(workflowId) {
      stopLiveView();
      liveEvents = [];
      renderLiveView();

      const url = `${BASE_URL}/v1/workflows/${workflowId}/events?key=${encodeURIComponent(API_KEY)}`;
      eventSource = new EventSource(url);

      eventSource.onmessage = (msg) => {
        const event = JSON.parse(msg.data);
        liveEvents.push(event);
        const stats = document.getElementById("live-stats");
        if (stats) stats.textContent = `${liveEvents.length} live events`;
        if (currentTab === "live") renderLiveRow(event);
      };

      eventSource.onerror = () => {};
    }

    function replayToIndex(index) {
      let state = {};
      const events = allEvents.slice(0, index);
      for (const event of events) {
        if (event.type === "patch_applied") {
          const parts = event.target.split(".");
          let cur = state;
          for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (!cur[part] || typeof cur[part] !== "object") cur[part] = {};
            cur = cur[part];
          }
          cur[parts[parts.length - 1]] = event.new_value;
        }
      }
      const pre = document.getElementById("replay-state");
      const label = document.getElementById("replay-progress");
      if (pre) pre.textContent = JSON.stringify(state, null, 2);
      if (label) label.textContent = `Step ${index} of ${allEvents.length}`;
    }

    function renderReplayTab(events) {
      const content = document.getElementById("content");
      content.innerHTML = `
        <div class="panel">
          <h3 class="section-title">Replay scrubber</h3>
          <div class="replay-controls">
            <div class="replay-topline">
              <div id="replay-progress">Step 0 of ${events.length}</div>
              <div>Replay reconstructed from patch_applied events</div>
            </div>
            <input id="replay-slider" type="range" min="0" max="${events.length}" value="0" />
            <pre id="replay-state" class="state-view">{}</pre>
          </div>
        </div>
      `;
      const slider = document.getElementById("replay-slider");
      slider.addEventListener("input", () => replayToIndex(parseInt(slider.value, 10)));
      replayToIndex(0);
    }

    async function loadTurns(workflowId) {
      const payload = await apiFetch(`/v1/workflows/${workflowId}/turns`);
      traceTurns = normalizeTurns(payload);
      if (currentTab === "trace") renderTraceTab();
    }

    function selectTurn(turnIndex) {
      selectedTurnIndex = turnIndex;
      renderTraceTab();
      loadTurnDetail(currentWorkflowId, turnIndex);
    }

    function renderPromptWithAttempts(prompts) {
      if (!prompts || !prompts.length) return `<div class="placeholder">No prompt available.</div>`;
      if (prompts.length === 1) {
        return `<pre class="mono">${escapeHtml(prompts[0].prompt_text || "")}</pre>`;
      }

      const tabs = prompts.map((_, idx) =>
        `<button class="prompt-tab ${idx === 0 ? "active" : ""}" data-prompt-index="${idx}">Attempt ${idx + 1}</button>`
      ).join("");

      const body = `<div id="prompt-attempt-body"><pre class="mono">${escapeHtml(prompts[0].prompt_text || "")}</pre></div>`;
      return `<div class="prompt-tabs">${tabs}</div>${body}`;
    }

    async function loadTurnDetail(workflowId, turnIndex) {
      const eventsResp = await apiFetch(`/v1/workflows/${workflowId}/events-list`);
      const events = normalizeEvents(eventsResp);
      const turns = [];
      let current = null;
      for (const event of events) {
        if (event.type === "context_sliced") {
          if (current) turns.push(current);
          current = {
            agent_id: event.agent_id,
            events: [event],
            context_paths: event.context_paths || [],
            prompts: [],
            model_responses: [],
            validation_failures: [],
            tool_calls: [],
            patch_target: null,
            patch_reason: null,
            succeeded: false,
          };
          continue;
        }
        if (current) {
          current.events.push(event);
          if (event.type === "prompt_assembled") {
            current.prompts.push(event);
          } else if (event.type === "model_returned") {
            current.model_responses.push(event);
          } else if (event.type === "validation_failed") {
            current.validation_failures.push(event);
          } else if (event.type === "tool_called") {
            current.tool_calls.push({ called: event, returned: null });
          } else if (event.type === "tool_returned") {
            const pair = current.tool_calls.find((t) => t.called.tool_call_id === event.tool_call_id);
            if (pair) pair.returned = event;
          } else if (event.type === "patch_applied") {
            current.patch_target = event.target;
            current.patch_reason = event.reason;
            current.succeeded = true;
          }
        }
      }
      if (current) turns.push(current);

      const turn = turns[turnIndex];
      if (!turn) return;
      const content = document.getElementById("content");
      const section = (title, body, extraClass = "") => `
        <details class="turn-section ${extraClass}" open>
          <summary>${escapeHtml(title)}</summary>
          <div class="section-body">${body}</div>
        </details>
      `;

      const contextBody = turn.context_paths && turn.context_paths.length
        ? `<ul>${turn.context_paths.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>`
        : `<div class="placeholder">No context captured.</div>`;

      const promptBody = renderPromptWithAttempts(turn.prompts.length ? turn.prompts : []);

      const lastResp = turn.model_responses.length ? turn.model_responses[turn.model_responses.length - 1] : null;
      const responseBody = lastResp
        ? `<pre class="mono ${turn.succeeded ? "border-green" : "border-red"}">${escapeHtml(lastResp.raw_response || "")}</pre>`
        : `<div class="placeholder">No model response.</div>`;

      const failuresBody = turn.validation_failures.length
        ? `<div class="turn-section border-red" style="padding: 12px; border-width:1px;">
            <div class="pill">${turn.succeeded ? "Recovered via retry" : "Validation failures"}</div>
            ${turn.validation_failures.map((f) => `
              <div class="json-block" style="border-color: rgba(252,129,129,.65);">
                <div><strong>${escapeHtml(f.error_type || "")}</strong></div>
                <div>${escapeHtml(f.error_message || "")}</div>
                <div>${escapeHtml(f.raw_output || "")}</div>
              </div>
            `).join("")}
          </div>`
        : `<div class="placeholder">No validation failures.</div>`;

      const toolsBody = turn.tool_calls.length
        ? turn.tool_calls.map((pair) => `
            <details class="tool-item">
              <summary>${escapeHtml(pair.called.tool_name || "")} · ${pair.returned ? escapeHtml(String(pair.returned.latency_seconds || "")) + "s" : "pending"} · ${escapeHtml(pair.returned ? pair.returned.result_summary || "" : "")}</summary>
              <div class="section-body"></div>
            </details>
          `).join("")
        : `<div class="placeholder">No tools used.</div>`;

      const patchBody = turn.patch_target
        ? `<div class="json-block border-green">
            <div><strong>Target:</strong> ${escapeHtml(turn.patch_target)}</div>
            <div><strong>Reason:</strong> ${escapeHtml(turn.patch_reason || "")}</div>
          </div>`
        : `<div class="json-block border-red">No patch produced</div>`;

      content.querySelector(".turn-detail").innerHTML = [
        section("Context", contextBody),
        section("Prompt", promptBody),
        section("Model response", responseBody),
        section("Validation failures", failuresBody, turn.validation_failures.length ? "border-red" : ""),
        section("Tools", toolsBody),
        section("Patch produced", patchBody, turn.patch_target ? "border-green" : "border-red")
      ].join("");
    }

    function renderTraceTab() {
      const content = document.getElementById("content");
      const turnsHtml = traceTurns.map((turn, idx) => {
        const selected = idx === selectedTurnIndex ? "selected" : "";
        const status = turn.succeeded ? "✓" : "•";
        const approvalTurn = pendingApprovals.some((approval) => {
          const target = approval.target || approval.pending_patch?.target || "";
          return target && String(turn.patch_target || "").includes(String(target));
        });
        return `
          <div class="turn-card ${selected} ${approvalTurn ? "approval-turn" : ""}" onclick="selectTurn(${idx})">
            <div class="turn-card-top">
              <div class="turn-card-title">${escapeHtml(turn.agent_id || "agent")}</div>
              <div class="badge ${turn.succeeded ? "winner-badge" : "loser-badge"}">${status}</div>
            </div>
            <div class="turn-card-meta">
              <span>${escapeHtml(turn.model || "")}</span>
              <span>${escapeHtml(String(turn.total_latency_seconds ?? 0))}s</span>
              <span>${escapeHtml(String(turn.attempt_count ?? 0))} attempts</span>
            </div>
          </div>
        `;
      }).join("");

      content.innerHTML = `
        <div class="trace-layout">
          <div class="panel">
            <h3 class="section-title">Agent turns</h3>
            <div class="stats">${traceTurns.length} turns</div>
            <div class="turn-list">${turnsHtml || '<div class="placeholder">No turns yet.</div>'}</div>
          </div>
          <div class="panel turn-detail">
            <div class="placeholder">Select a turn to inspect full trace detail.</div>
          </div>
        </div>
      `;

      if (selectedTurnIndex === null && traceTurns.length) {
        selectedTurnIndex = 0;
      }
      if (selectedTurnIndex !== null && traceTurns[selectedTurnIndex]) {
        loadTurnDetail(currentWorkflowId, selectedTurnIndex);
      }
    }

    function setActiveTab(name) {
      currentTab = name;
      document.querySelectorAll(".tab").forEach((el) => {
        el.classList.toggle("active", el.dataset.tab === name);
      });

      if (name === "detail") renderDetailTab(allEvents, detailState);
      if (name === "live") {
        if (currentWorkflowId) startLiveView(currentWorkflowId);
        else renderLiveView();
      }
      if (name === "replay") renderReplayTab(allEvents);
      if (name === "trace") {
        if (currentWorkflowId) loadTurns(currentWorkflowId).then(renderTraceTab);
        else renderTraceTab();
      }
    }

    function openApprovalByEvent(approvalId) {
      const approval = approvalIndex.get(approvalKey(currentWorkflowId, approvalId));
      if (!approval) return;
      openApprovalModal(approval);
    }

    function openApprovalModal(approval) {
      activeApproval = approval;
      document.getElementById("approval-modal").classList.add("visible");
      document.getElementById("approval-modal").setAttribute("aria-hidden", "false");
      document.getElementById("modal-approval-id").textContent = approval.approval_id || "";
      document.getElementById("modal-agent").textContent = approval.agent_id || "";
      document.getElementById("modal-target").textContent = approval.target || approval.pending_patch?.target || "";
      document.getElementById("modal-current").textContent = formatJson(approval.current_value ?? approval.pending_patch?.old_value ?? null);
      document.getElementById("modal-proposed").textContent = formatJson(approval.proposed_value ?? approval.pending_patch?.value ?? approval.pending_patch?.new_value ?? null);
      document.getElementById("modal-reason").textContent = approval.reason || approval.description || "";
      document.getElementById("modal-review-reason").value = "";
      document.getElementById("modify-editor-wrap").classList.add("hidden");
      document.getElementById("modal-modified-json").value = formatJson(approval.proposed_value ?? approval.pending_patch?.value ?? approval.pending_patch?.new_value ?? null);
    }

    function closeApprovalModal() {
      activeApproval = null;
      document.getElementById("approval-modal").classList.remove("visible");
      document.getElementById("approval-modal").setAttribute("aria-hidden", "true");
    }

    function showModifyEditor() {
      document.getElementById("modify-editor-wrap").classList.remove("hidden");
    }

    async function submitApprovalDecision(decision) {
      if (!activeApproval || !currentWorkflowId) return;
      let modified_patch = null;
      if (decision === "modified") {
        try {
          modified_patch = JSON.parse(document.getElementById("modal-modified-json").value);
        } catch (err) {
          alert("Modified patch must be valid JSON.");
          return;
        }
      }

      const body = {
        decision,
        reason: document.getElementById("modal-review-reason").value || "",
        modified_patch
      };

      await apiFetch(`/v1/workflows/${currentWorkflowId}/approvals/${activeApproval.approval_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      closeApprovalModal();
      await loadDetail(currentWorkflowId);
      if (currentTab === "trace") await loadTurns(currentWorkflowId);
      await loadWorkflowList();
      if (currentTab === "detail") renderDetailTab(allEvents, detailState);
    }

    document.addEventListener("DOMContentLoaded", async () => {
      document.querySelectorAll(".tab").forEach((tab) => {
        tab.addEventListener("click", () => setActiveTab(tab.dataset.tab));
      });

      try {
        await loadWorkflowList();
      } catch (err) {
        document.getElementById("workflow-list").innerHTML =
          `<div class="placeholder">${String(err.message || err)}</div>`;
      }

      setInterval(async () => {
        try {
          await loadWorkflowList();
          if (currentWorkflowId) await loadDetail(currentWorkflowId);
          if (currentWorkflowId && currentTab === "trace") {
            await loadTurns(currentWorkflowId);
          }
        } catch {}
      }, 5000);
    });
  </script>
</body>
</html>
"""
