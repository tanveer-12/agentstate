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

    #app {
      display: flex;
      height: 100vh;
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
  </style>
</head>
<body>
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
      </div>
      <div id="content"></div>
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

    function setNested(obj, path, value) {
      const parts = path.split(".");
      let cur = obj;
      for (let i = 0; i < parts.length - 1; i++) {
        const part = parts[i];
        if (!cur[part] || typeof cur[part] !== "object") cur[part] = {};
        cur = cur[part];
      }
      cur[parts[parts.length - 1]] = value;
    }

    function badgeLabel(event) {
      return event.agent_id || "";
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
      return "";
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

      workflowIds.forEach((workflowId) => {
        const item = document.createElement("div");
        item.className = "workflow-item" + (workflowId === currentWorkflowId ? " selected" : "");
        item.textContent = workflowId;
        item.onclick = () => selectWorkflow(workflowId);
        list.appendChild(item);
      });

      if (!currentWorkflowId || !workflowIds.includes(currentWorkflowId)) {
        selectWorkflow(workflowIds[0]);
      }
    }

    function selectWorkflow(workflowId) {
      currentWorkflowId = workflowId;
      document.querySelectorAll(".workflow-item").forEach((el) => {
        el.classList.toggle("selected", el.textContent === workflowId);
      });
      loadDetail(workflowId);
      if (currentTab === "live") startLiveView(workflowId);
    }

    async function loadDetail(workflowId) {
      const stateResp = await apiFetch(`/v1/workflows/${workflowId}`);
      const eventsResp = await apiFetch(`/v1/workflows/${workflowId}/events-list`);

      detailState = normalizeState(stateResp);
      allEvents = normalizeEvents(eventsResp);
      workflowStartTime = allEvents.length ? (allEvents[0].timestamp || null) : null;

      if (currentTab === "detail") renderDetailTab(allEvents, detailState);
      if (currentTab === "replay") renderReplayTab(allEvents);
    }

    function renderDetailEvent(event) {
      const type = eventType(event);
      const color =
        type === "patch_applied" ? "var(--green)" :
        type === "conflict_detected" ? "var(--yellow)" :
        (type === "workflow_started" || type === "workflow_completed") ? "var(--blue)" :
        type === "agent_errored" ? "var(--red)" : "var(--border)";

      let detailHtml = "";
      if (type === "patch_applied") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Target:</strong> ${event.target || ""}</div>
            <div class="detail-row"><strong>Reason:</strong> ${event.reason || ""}</div>
            <div class="detail-row"><strong>Old value:</strong><div class="json-block">${formatJson(event.old_value)}</div></div>
            <div class="detail-row"><strong>New value:</strong><div class="json-block">${formatJson(event.new_value)}</div></div>
          </div>
        `;
      } else if (type === "conflict_detected") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Path:</strong> ${event.path || ""}</div>
            <div class="detail-row">
              <span class="badge winner-badge">Winner: ${event.winner_agent_id || ""}</span>
              <span class="badge loser-badge">Loser: ${event.loser_agent_id || ""}</span>
            </div>
            <div class="detail-row"><strong>Strategy:</strong> ${event.resolution_strategy || ""}</div>
          </div>
        `;
      } else if (type === "agent_errored") {
        detailHtml = `
          <div class="detail-grid">
            <div class="detail-row"><strong>Error type:</strong> ${event.error_type || ""}</div>
            <div class="detail-row"><strong>Message:</strong> ${event.error_message || ""}</div>
            <div class="detail-row"><strong>Retries:</strong> ${event.retry_count ?? 0}</div>
          </div>
        `;
      } else {
        detailHtml = `<div class="detail-row">${formatJson(event)}</div>`;
      }

      return `
        <div class="event-row" data-type="${type}" style="border-left-color: ${color};" onclick="this.classList.toggle('open')">
          <div class="event-header">
            <div class="time">${formatTimestamp(event.timestamp || 0)}</div>
            <div><span class="badge">${badgeLabel(event)}</span></div>
            <div><span class="badge type-badge">${type}</span></div>
            <div>${eventSummary(type)}</div>
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
      html.push('<div class="panel" style="margin-top: 16px;">');
      html.push('<h3 class="section-title">Current state</h3>');
      html.push(`<pre class="state-view">${formatJson(state)}</pre>`);
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
          <div class="time">${formatTimestamp(event.timestamp || 0)}</div>
          <div><span class="badge">${badgeLabel(event)}</span></div>
          <div><span class="badge type-badge">${eventType(event)}</span></div>
          <div>${event.target || event.path || ""}</div>
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
          setNested(state, event.target, event.new_value);
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
        } catch {}
      }, 5000);
    });
  </script>
</body>
</html>
"""
