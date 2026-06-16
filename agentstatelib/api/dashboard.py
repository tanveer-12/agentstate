"""Self-hosted web dashboard HTML for agentstatelib."""

from __future__ import annotations

DASHBOARD_HTML: str = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>agentstatelib</title>
  <style>
    :root {
      --bg:             #f8fafc;
      --surface:        #ffffff;
      --surface2:       #f1f5f9;
      --border:         #e2e8f0;
      --border2:        #cbd5e1;
      --text:           #0f172a;
      --muted:          #64748b;
      --accent:         #2563eb;

      --green:          #16a34a;
      --green-bg:       #f0fdf4;
      --green-border:   #bbf7d0;

      --yellow:         #b45309;
      --yellow-bg:      #fffbeb;
      --yellow-border:  #fde68a;

      --blue:           #2563eb;
      --blue-bg:        #eff6ff;
      --blue-border:    #bfdbfe;

      --red:            #dc2626;
      --red-bg:         #fef2f2;
      --red-border:     #fecaca;

      --purple:         #7c3aed;
      --purple-bg:      #faf5ff;
      --purple-border:  #ddd6fe;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, system-ui, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      background: var(--bg);
      color: var(--text);
      height: 100vh;
      overflow: hidden;
    }

    /* ─── Key modal ─────────────────────────────────────────────────── */
    .overlay {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 300;
      background: rgba(15, 23, 42, 0.45);
      align-items: center;
      justify-content: center;
    }
    .overlay.visible { display: flex; }

    .key-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 32px;
      width: min(440px, 94vw);
      box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    .key-card h2 { font-size: 1.15rem; font-weight: 700; margin-bottom: 6px; }
    .key-card .key-desc {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 18px;
      line-height: 1.6;
    }
    .key-card input[type="password"] {
      width: 100%;
      border: 1px solid var(--border2);
      border-radius: 8px;
      padding: 10px 12px;
      font-family: ui-monospace, monospace;
      font-size: 13px;
      background: var(--surface2);
      color: var(--text);
      outline: none;
      margin-bottom: 10px;
    }
    .key-card input[type="password"]:focus { border-color: var(--accent); }
    .key-hint {
      font-size: 12px;
      color: var(--muted);
      margin-top: 14px;
      padding: 10px 12px;
      background: var(--surface2);
      border-radius: 8px;
      line-height: 1.7;
    }
    .key-hint code {
      font-family: ui-monospace, monospace;
      background: var(--border);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 11px;
    }

    /* ─── App shell ─────────────────────────────────────────────────── */
    #app { display: flex; height: 100vh; width: 100vw; }
    #app.hidden { display: none; }

    /* ─── Sidebar ───────────────────────────────────────────────────── */
    .sidebar {
      width: 260px;
      min-width: 260px;
      background: var(--surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .sidebar-hd {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 12px 12px;
      border-bottom: 1px solid var(--border);
    }
    .logo { font-size: 14px; font-weight: 800; color: var(--text); letter-spacing: -0.01em; }
    .logo span { color: var(--accent); }
    .icon-btn {
      border: none;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      padding: 5px 7px;
      border-radius: 6px;
      font-size: 14px;
      line-height: 1;
    }
    .icon-btn:hover { background: var(--surface2); color: var(--text); }

    #workflow-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .wf-item {
      padding: 8px 10px;
      border-radius: 7px;
      cursor: pointer;
      font-size: 11px;
      font-family: ui-monospace, monospace;
      color: var(--muted);
      border: 1px solid transparent;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      transition: background 0.1s, color 0.1s;
    }
    .wf-item:hover { background: var(--surface2); color: var(--text); }
    .wf-item.selected { background: var(--blue-bg); color: var(--blue); border-color: var(--blue-border); }
    .wf-id-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .approval-badge {
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 999px;
      background: var(--yellow-bg);
      color: var(--yellow);
      border: 1px solid var(--yellow-border);
      font-size: 10px;
      font-weight: 700;
    }

    /* ─── Main area ─────────────────────────────────────────────────── */
    .main { flex: 1; min-width: 0; display: flex; flex-direction: column; }

    /* ─── Approval banner ───────────────────────────────────────────── */
    .approval-banner {
      display: none;
      padding: 9px 14px;
      background: var(--yellow-bg);
      border-bottom: 1px solid var(--yellow-border);
      color: var(--yellow);
      font-size: 13px;
      font-weight: 600;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    .approval-banner.visible { display: flex; }

    /* ─── Tab bar ───────────────────────────────────────────────────── */
    .tab-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
      min-height: 46px;
      gap: 10px;
    }
    .tabs { display: flex; gap: 2px; }
    .tab {
      padding: 7px 13px;
      border: none;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      border-radius: 6px;
      border-bottom: 2px solid transparent;
      transition: color 0.1s, background 0.1s;
    }
    .tab:hover { color: var(--text); background: var(--surface2); }
    .tab.active { color: var(--accent); border-bottom-color: var(--accent); background: var(--blue-bg); }
    .tab-actions { display: flex; gap: 8px; align-items: center; }
    .dl-btn {
      padding: 6px 11px;
      border: 1px solid var(--border2);
      border-radius: 6px;
      background: var(--surface);
      color: var(--text);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .dl-btn:hover { background: var(--surface2); }

    /* ─── Content ───────────────────────────────────────────────────── */
    #content { flex: 1; overflow-y: auto; padding: 14px; background: var(--bg); }

    /* ─── Panels ────────────────────────────────────────────────────── */
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 12px;
    }
    .panel-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text);
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .count-pill {
      font-size: 11px;
      font-weight: 600;
      color: var(--muted);
      background: var(--surface2);
      padding: 1px 8px;
      border-radius: 999px;
      text-transform: none;
      letter-spacing: 0;
    }
    .placeholder {
      color: var(--muted);
      font-size: 13px;
      padding: 18px;
      text-align: center;
      border: 1px dashed var(--border);
      border-radius: 8px;
    }
    .hidden { display: none !important; }

    /* ─── Event timeline ────────────────────────────────────────────── */
    .timeline { display: flex; flex-direction: column; gap: 5px; }

    .evt {
      display: flex;
      align-items: stretch;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
      background: var(--surface);
      transition: border-color 0.1s;
    }
    .evt:hover { border-color: var(--border2); }

    .evt-stripe { width: 4px; flex-shrink: 0; background: var(--border2); }

    /* stripe colors by event type */
    .evt[data-t="patch_applied"]            .evt-stripe { background: var(--green); }
    .evt[data-t="model_returned"]           .evt-stripe { background: var(--green); }
    .evt[data-t="workflow_completed"]       .evt-stripe { background: var(--blue); }
    .evt[data-t="workflow_started"]         .evt-stripe { background: var(--blue); }
    .evt[data-t="human_approval_resolved"]  .evt-stripe { background: var(--purple); }
    .evt[data-t="model_called"]             .evt-stripe { background: var(--yellow); }
    .evt[data-t="conflict_detected"]        .evt-stripe { background: var(--yellow); }
    .evt[data-t="human_approval_requested"] .evt-stripe { background: var(--yellow); }
    .evt[data-t="validation_failed"]        .evt-stripe { background: var(--red); }
    .evt[data-t="agent_errored"]            .evt-stripe { background: var(--red); }

    .evt-body { flex: 1; padding: 8px 12px; min-width: 0; }
    .evt-row {
      display: grid;
      grid-template-columns: 140px 110px 170px 1fr;
      gap: 10px;
      align-items: center;
      font-size: 12px;
    }
    .evt-time {
      color: var(--muted);
      font-family: ui-monospace, monospace;
      font-size: 11px;
      white-space: nowrap;
    }
    .evt-agent {
      font-family: ui-monospace, monospace;
      font-size: 11px;
      font-weight: 600;
      color: var(--text);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .evt-type-badge {
      display: inline-flex;
      align-items: center;
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 10px;
      font-weight: 700;
      font-family: ui-monospace, monospace;
      border: 1px solid var(--border);
      background: var(--surface2);
      color: var(--muted);
      white-space: nowrap;
    }
    /* badge colors */
    .evt[data-t="patch_applied"]            .evt-type-badge { color: var(--green);  background: var(--green-bg);  border-color: var(--green-border); }
    .evt[data-t="model_returned"]           .evt-type-badge { color: var(--green);  background: var(--green-bg);  border-color: var(--green-border); }
    .evt[data-t="workflow_started"]         .evt-type-badge,
    .evt[data-t="workflow_completed"]       .evt-type-badge { color: var(--blue);   background: var(--blue-bg);   border-color: var(--blue-border); }
    .evt[data-t="model_called"]             .evt-type-badge,
    .evt[data-t="conflict_detected"]        .evt-type-badge,
    .evt[data-t="human_approval_requested"] .evt-type-badge { color: var(--yellow); background: var(--yellow-bg); border-color: var(--yellow-border); }
    .evt[data-t="validation_failed"]        .evt-type-badge,
    .evt[data-t="agent_errored"]            .evt-type-badge { color: var(--red);    background: var(--red-bg);    border-color: var(--red-border); }
    .evt[data-t="human_approval_resolved"]  .evt-type-badge { color: var(--purple); background: var(--purple-bg); border-color: var(--purple-border); }

    .evt-summary { font-size: 12px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .evt-summary code {
      background: var(--surface2);
      border: 1px solid var(--border);
      padding: 0 4px;
      border-radius: 3px;
      font-family: ui-monospace, monospace;
      font-size: 10px;
    }
    .evt-detail {
      display: none;
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid var(--border);
      font-size: 12px;
      color: var(--muted);
      line-height: 1.6;
    }
    .evt.open .evt-detail { display: block; }
    .evt-detail > div { margin-bottom: 6px; }
    .evt-detail strong { color: var(--text); }

    /* ─── Code blocks ───────────────────────────────────────────────── */
    .code-block {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 7px;
      padding: 9px 11px;
      white-space: pre-wrap;
      word-break: break-all;
      color: var(--text);
      line-height: 1.5;
      margin-top: 5px;
    }
    .code-block.scrollable { max-height: 260px; overflow-y: auto; }

    /* ─── State display ─────────────────────────────────────────────── */
    .state-meta {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }
    .meta-card {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px 12px;
    }
    .meta-label { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
    .meta-value { font-size: 13px; color: var(--text); }
    .meta-value.mono { font-family: ui-monospace, monospace; font-size: 11px; }

    .status-pill {
      display: inline-flex;
      align-items: center;
      padding: 2px 9px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
    }
    .status-complete  { background: var(--green-bg);  color: var(--green);  border: 1px solid var(--green-border); }
    .status-running   { background: var(--yellow-bg); color: var(--yellow); border: 1px solid var(--yellow-border); }
    .status-failed    { background: var(--red-bg);    color: var(--red);    border: 1px solid var(--red-border); }
    .status-paused    { background: var(--purple-bg); color: var(--purple); border: 1px solid var(--purple-border); }

    .facts-table { width: 100%; border-collapse: collapse; font-size: 13px; }
    .facts-table tr { border-bottom: 1px solid var(--border); }
    .facts-table tr:last-child { border-bottom: none; }
    .facts-table td { padding: 7px 10px; vertical-align: top; }
    .facts-table .fk { font-family: ui-monospace, monospace; font-size: 11px; color: var(--muted); width: 180px; white-space: nowrap; }
    .facts-table .fv { color: var(--text); }
    .fv-null  { color: var(--muted); font-style: italic; }
    .fv-true  { color: var(--green); font-weight: 700; }
    .fv-false { color: var(--red);   font-weight: 700; }
    .fv-num   { color: var(--accent); font-family: ui-monospace, monospace; }

    /* ─── Live tab ──────────────────────────────────────────────────── */
    .live-stream { display: flex; flex-direction: column; gap: 3px; }
    .live-row {
      display: grid;
      grid-template-columns: 8px 100px 110px 150px 1fr;
      gap: 10px;
      align-items: center;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 12px;
      background: var(--surface);
      border: 1px solid var(--border);
    }
    .dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;
      background: var(--border2);
    }
    .dot.green  { background: var(--green); }
    .dot.yellow { background: var(--yellow); }
    .dot.blue   { background: var(--blue); }
    .dot.red    { background: var(--red); }
    .dot.purple { background: var(--purple); }
    .live-time { color: var(--muted); font-family: ui-monospace, monospace; font-size: 11px; }
    .live-agent { font-family: ui-monospace, monospace; font-size: 11px; font-weight: 600; }

    /* ─── Trace tab ─────────────────────────────────────────────────── */
    .trace-grid {
      display: grid;
      grid-template-columns: 270px 1fr;
      gap: 12px;
      align-items: start;
    }
    .agent-list { display: flex; flex-direction: column; gap: 5px; }
    .agent-card {
      padding: 11px 12px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      cursor: pointer;
      transition: border-color 0.1s, background 0.1s;
    }
    .agent-card:hover { border-color: var(--border2); background: var(--surface2); }
    .agent-card.selected { border-color: var(--accent); background: var(--blue-bg); }
    .agent-card-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 5px;
    }
    .agent-name { font-weight: 700; font-size: 13px; }
    .agent-ok   { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 999px; font-size: 11px; font-weight: 700; background: var(--green-bg);  color: var(--green);  border: 1px solid var(--green-border); }
    .agent-fail { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 999px; font-size: 11px; font-weight: 700; background: var(--red-bg);    color: var(--red);    border: 1px solid var(--red-border); }
    .agent-meta { font-size: 11px; color: var(--muted); display: flex; gap: 10px; flex-wrap: wrap; }

    .agent-detail { display: flex; flex-direction: column; gap: 8px; }

    .section {
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      background: var(--surface);
    }
    .section summary {
      display: flex;
      align-items: center;
      gap: 7px;
      padding: 10px 13px;
      cursor: pointer;
      list-style: none;
      font-weight: 700;
      font-size: 13px;
      user-select: none;
    }
    .section summary::-webkit-details-marker { display: none; }
    .section[open] summary { border-bottom: 1px solid var(--border); }
    .section-arr { color: var(--muted); font-size: 10px; transition: transform 0.15s; }
    .section[open] .section-arr { transform: rotate(90deg); }
    .section-tag {
      margin-left: auto;
      font-size: 11px;
      font-weight: 600;
      color: var(--muted);
      background: var(--surface2);
      padding: 1px 7px;
      border-radius: 999px;
    }
    .section-body { padding: 11px 13px; font-size: 13px; }

    .ctx-table { width: 100%; border-collapse: collapse; font-size: 12px; }
    .ctx-table tr { border-bottom: 1px solid var(--border); }
    .ctx-table tr:last-child { border-bottom: none; }
    .ctx-table td { padding: 6px 8px; vertical-align: top; }
    .ctx-table .cp { font-family: ui-monospace, monospace; color: var(--muted); width: 155px; white-space: nowrap; }
    .ctx-table .cv { font-family: ui-monospace, monospace; font-size: 11px; color: var(--text); word-break: break-all; }

    .model-stats {
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      margin-bottom: 10px;
      font-size: 12px;
    }
    .model-stat-key { color: var(--muted); }
    .model-stat-val { font-weight: 700; }

    .patch-box {
      background: var(--green-bg);
      border: 1px solid var(--green-border);
      border-radius: 8px;
      padding: 11px 13px;
    }
    .patch-target {
      font-family: ui-monospace, monospace;
      font-size: 13px;
      font-weight: 700;
      color: var(--green);
      margin-bottom: 5px;
    }
    .patch-reason { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
    .no-patch-box {
      background: var(--red-bg);
      border: 1px solid var(--red-border);
      border-radius: 8px;
      padding: 11px 13px;
      color: var(--red);
      font-size: 13px;
    }
    .vf-box {
      background: var(--red-bg);
      border: 1px solid var(--red-border);
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 8px;
      font-size: 12px;
    }
    .vf-box:last-child { margin-bottom: 0; }
    .vf-type { font-weight: 700; color: var(--red); margin-bottom: 3px; }
    .vf-msg  { color: var(--muted); }

    /* ─── Approval modal ────────────────────────────────────────────── */
    .approval-modal {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 200;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .approval-modal.visible { display: flex; }
    .modal-bg {
      position: absolute;
      inset: 0;
      background: rgba(15,23,42,0.4);
    }
    .modal-card {
      position: relative;
      z-index: 1;
      width: min(1000px, 96vw);
      max-height: 90vh;
      overflow-y: auto;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      box-shadow: 0 20px 70px rgba(0,0,0,0.12);
      padding: 20px;
    }
    .modal-hd {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    .modal-hd h3 { font-size: 15px; font-weight: 800; }
    .modal-close {
      border: 1px solid var(--border);
      background: var(--surface2);
      color: var(--text);
      border-radius: 7px;
      padding: 6px 11px;
      cursor: pointer;
      font-size: 13px;
    }
    .modal-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .modal-panel { border: 1px solid var(--border); border-radius: 10px; padding: 14px; background: var(--surface2); }
    .modal-panel h4 { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin-bottom: 12px; }
    .modal-field { margin-bottom: 10px; }
    .modal-field label { display: block; font-size: 11px; font-weight: 600; color: var(--muted); margin-bottom: 5px; }
    .modal-field input,
    .modal-field textarea {
      width: 100%;
      border: 1px solid var(--border2);
      border-radius: 7px;
      background: var(--surface);
      color: var(--text);
      padding: 8px 10px;
      font: inherit;
      font-size: 13px;
    }
    .modal-field textarea {
      min-height: 200px;
      resize: vertical;
      font-family: ui-monospace, monospace;
      font-size: 12px;
    }
    .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; }

    .btn {
      border: none;
      border-radius: 8px;
      padding: 9px 15px;
      cursor: pointer;
      font-weight: 700;
      font-size: 13px;
    }
    .btn-approve  { background: var(--green);  color: #fff; }
    .btn-reject   { background: var(--red);    color: #fff; }
    .btn-modify   { background: var(--yellow); color: #fff; }
    .btn-ghost    { background: var(--surface2); color: var(--text); border: 1px solid var(--border2); }
  </style>
</head>
<body>

  <!-- ── Key setup modal ─────────────────────────────────────────── -->
  <div id="key-modal" class="overlay">
    <div class="key-card">
      <h2>Enter your API key</h2>
      <p class="key-desc">
        The key is stored only in this browser (localStorage) and sent only
        to your own server — never anywhere else.
      </p>
      <input id="key-input" type="password" placeholder="your-api-key-here" autocomplete="off" />
      <button class="btn btn-approve" style="width:100%;" onclick="saveKey()">Save &amp; Continue →</button>
      <div class="key-hint">
        Generate a key: <code>POST /v1/keys/generate</code><br/>
        Activate it: <code>AGENTSTATE_API_KEYS=your-key</code> in your server env.
      </div>
    </div>
  </div>

  <!-- ── Approval banner ─────────────────────────────────────────── -->
  <div id="approval-banner" class="approval-banner">
    <span id="approval-banner-text">Pending approvals.</span>
    <button class="btn btn-ghost" style="font-size:12px;padding:5px 10px;" onclick="refreshApprovals()">Refresh</button>
  </div>

  <!-- ── Main app ─────────────────────────────────────────────────── -->
  <div id="app" class="hidden">
    <aside class="sidebar">
      <div class="sidebar-hd">
        <div class="logo">agent<span>state</span>lib</div>
        <button class="icon-btn" onclick="openKeyModal()" title="Change API key">⚙</button>
      </div>
      <div id="workflow-list"></div>
    </aside>

    <div class="main">
      <div class="tab-bar">
        <div class="tabs">
          <button class="tab active" data-tab="detail">Detail</button>
          <button class="tab" data-tab="live">Live</button>
          <button class="tab" data-tab="replay">Replay</button>
          <button class="tab" data-tab="trace">Trace</button>
        </div>
        <div class="tab-actions">
          <button id="dl-btn" class="dl-btn hidden" onclick="downloadWorkflow()">↓ Download JSON</button>
        </div>
      </div>
      <div id="content"></div>
    </div>
  </div>

  <!-- ── Approval modal ──────────────────────────────────────────── -->
  <div id="approval-modal" class="approval-modal" aria-hidden="true">
    <div class="modal-bg" onclick="closeApprovalModal()"></div>
    <div class="modal-card">
      <div class="modal-hd">
        <h3>Pending approval</h3>
        <button class="modal-close" onclick="closeApprovalModal()">✕ Close</button>
      </div>
      <div class="modal-cols">
        <div class="modal-panel">
          <h4>Patch details</h4>
          <div class="modal-field"><label>Approval ID</label><div id="m-approval-id" style="font-family:monospace;font-size:12px;"></div></div>
          <div class="modal-field"><label>Agent</label><div id="m-agent" style="font-family:monospace;font-size:12px;"></div></div>
          <div class="modal-field"><label>Target</label><div id="m-target" style="font-family:monospace;font-size:12px;"></div></div>
          <div class="modal-field"><label>Current value</label><pre id="m-current" class="code-block scrollable"></pre></div>
          <div class="modal-field"><label>Proposed value</label><pre id="m-proposed" class="code-block scrollable"></pre></div>
          <div class="modal-field"><label>Reason</label><div id="m-reason" style="font-size:13px;"></div></div>
        </div>
        <div class="modal-panel">
          <h4>Review decision</h4>
          <div class="modal-field">
            <label>Decision note (optional)</label>
            <input id="m-review-reason" type="text" placeholder="Optional note…" />
          </div>
          <div id="m-modify-wrap" class="modal-field hidden">
            <label>Modified value (JSON)</label>
            <textarea id="m-modified-json"></textarea>
          </div>
          <div class="modal-actions">
            <button class="btn btn-approve" onclick="submitApproval('approved')">✓ Approve</button>
            <button class="btn btn-reject"  onclick="submitApproval('rejected')">✕ Reject</button>
            <button class="btn btn-modify"  onclick="showModifyEditor()">✎ Modify</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    // ── Key management ──────────────────────────────────────────────
    let API_KEY = localStorage.getItem("agentstate_key") || "";

    // Accept key from URL for backward compat, then immediately strip it
    const _urlKey = new URLSearchParams(window.location.search).get("key");
    if (_urlKey) {
      API_KEY = _urlKey;
      localStorage.setItem("agentstate_key", _urlKey);
      const _u = new URL(window.location.href);
      _u.searchParams.delete("key");
      history.replaceState({}, "", _u.toString());
    }

    function openKeyModal() {
      document.getElementById("key-input").value = API_KEY;
      document.getElementById("key-modal").classList.add("visible");
    }

    function saveKey() {
      const k = document.getElementById("key-input").value.trim();
      if (!k) return;
      API_KEY = k;
      localStorage.setItem("agentstate_key", k);
      document.getElementById("key-modal").classList.remove("visible");
      document.getElementById("app").classList.remove("hidden");
      loadWorkflowList().catch(showListError);
    }

    // ── Global state ────────────────────────────────────────────────
    const BASE = window.location.origin;
    let currentWfId     = null;
    let eventSource     = null;
    let liveEvents      = [];
    let allEvents       = [];
    let detailState     = {};
    let wfStartTime     = null;
    let currentTab      = "detail";
    let selectedAgent   = null;
    let pendingApprovals = [];
    let approvalMap     = new Map();
    let activeApproval  = null;

    // ── API ─────────────────────────────────────────────────────────
    async function apiFetch(path, opts = {}) {
      const h = new Headers(opts.headers || {});
      h.set("x-api-key", API_KEY);
      const resp = await fetch(`${BASE}${path}`, { ...opts, headers: h });
      if (!resp.ok) {
        let d;
        try { d = await resp.json(); } catch { d = { message: resp.statusText }; }
        throw new Error(d?.detail?.message || d?.message || resp.statusText);
      }
      return resp.json();
    }

    async function apiFetchRaw(path) {
      const resp = await fetch(`${BASE}${path}`, { headers: { "x-api-key": API_KEY } });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp;
    }

    // ── Helpers ─────────────────────────────────────────────────────
    function esc(v) {
      return String(v ?? "")
        .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
    }
    function fmt(v) { try { return JSON.stringify(v, null, 2); } catch { return String(v); } }

    function fmtTime(ts) {
      if (typeof ts !== "number") return "";
      const d = new Date(ts * 1000);
      const hms = d.toLocaleTimeString([], { hour12: false });
      if (!wfStartTime) return hms;
      return `${hms}  +${(ts - wfStartTime).toFixed(1)}s`;
    }

    function evType(ev) { return ev.type || ev.event_type || "event"; }

    function dotColor(t) {
      if (["patch_applied","model_returned","workflow_completed"].includes(t)) return "green";
      if (["model_called","conflict_detected","human_approval_requested","retry_attempted"].includes(t)) return "yellow";
      if (["workflow_started"].includes(t)) return "blue";
      if (["human_approval_resolved"].includes(t)) return "purple";
      if (["agent_errored","validation_failed"].includes(t)) return "red";
      return "";
    }

    function evSummary(t, ev) {
      switch (t) {
        case "patch_applied": {
          const v = fmt(ev.new_value);
          return `set <code>${esc(ev.target||"")}</code> → ${esc(v.length>80 ? v.slice(0,80)+"…" : v)}`;
        }
        case "model_returned": {
          const ms  = ev.latency_seconds ? (ev.latency_seconds*1000).toFixed(0) : "?";
          const tok = (ev.input_tokens||0)+(ev.output_tokens||0);
          const cost= ev.estimated_cost_usd ? ` · $${ev.estimated_cost_usd.toFixed(4)}` : "";
          return `responded in ${ms}ms · ${tok} tokens${cost}`;
        }
        case "model_called":
          return `calling <code>${esc(ev.model||"model")}</code>…`;
        case "prompt_assembled": {
          const len = ev.context_length || (ev.prompt_text||"").length;
          const att = ev.attempt_number ? ` · attempt ${ev.attempt_number+1}` : "";
          return `built prompt · ${len} chars${att}`;
        }
        case "context_sliced": {
          const p = (ev.context_paths||[]).slice(0,4).join(", ");
          const extra = (ev.context_paths||[]).length > 4 ? ` +${(ev.context_paths||[]).length-4}` : "";
          return `reading <code>${esc(p)}${extra}</code>`;
        }
        case "workflow_started":   return `started · <code>${esc(ev.workflow_type||"")}</code>`;
        case "workflow_completed": return `done · status <code>${esc(ev.final_status||"complete")}</code>`;
        case "validation_failed":  return `parse failed · attempt ${(ev.attempt_number||0)+1}`;
        case "retry_attempted":    return `retrying · attempt ${ev.attempt_number||"?"}`;
        case "conflict_detected":  return `conflict on <code>${esc(ev.path||"")}</code> · ${esc(ev.winner_agent_id||"")} wins`;
        case "human_approval_requested": return "awaiting human approval";
        case "human_approval_resolved":  return `decision: <code>${esc(ev.decision||"")}</code>`;
        case "agent_errored":      return esc(ev.error_type||"error");
        case "checkpoint_saved":   return `checkpoint · ${ev.event_count} events`;
        default: return "";
      }
    }

    function evDetail(t, ev) {
      if (t === "patch_applied") return `
        <div><strong>Target:</strong> <code>${esc(ev.target||"")}</code></div>
        <div><strong>Reason:</strong> ${esc(ev.reason||"")}</div>
        <div><strong>Old value:</strong><div class="code-block scrollable">${esc(fmt(ev.old_value))}</div></div>
        <div><strong>New value:</strong><div class="code-block scrollable">${esc(fmt(ev.new_value))}</div></div>`;
      if (t === "model_returned") return `
        <div><strong>Latency:</strong> ${(ev.latency_seconds||0).toFixed(3)}s &nbsp;
             <strong>Input tokens:</strong> ${ev.input_tokens||0} &nbsp;
             <strong>Output tokens:</strong> ${ev.output_tokens||0} &nbsp;
             <strong>Cost:</strong> $${(ev.estimated_cost_usd||0).toFixed(4)}</div>
        <div><strong>Response:</strong><div class="code-block scrollable">${esc(ev.raw_response||"")}</div></div>`;
      if (t === "prompt_assembled") return `
        <div><strong>Attempt:</strong> ${ev.attempt_number||0} &nbsp; <strong>Context length:</strong> ${ev.context_length||0} chars</div>
        <div><strong>Prompt:</strong><div class="code-block scrollable">${esc(ev.prompt_text||"")}</div></div>`;
      if (t === "context_sliced") return `
        <div><strong>Paths:</strong> ${esc((ev.context_paths||[]).join(", "))}</div>
        <div><strong>Size:</strong> ${ev.context_size_bytes||0} bytes</div>`;
      if (t === "conflict_detected") return `
        <div><strong>Path:</strong> <code>${esc(ev.path||"")}</code></div>
        <div><strong>Winner:</strong> <span style="color:var(--green);font-weight:700;">${esc(ev.winner_agent_id||"")}</span> &nbsp;
             <strong>Loser:</strong> <span style="color:var(--red);font-weight:700;">${esc(ev.loser_agent_id||"")}</span></div>
        <div><strong>Strategy:</strong> ${esc(ev.resolution_strategy||"")}</div>`;
      if (t === "validation_failed") return `
        <div><strong>Error type:</strong> <code>${esc(ev.error_type||"")}</code></div>
        <div><strong>Message:</strong> ${esc(ev.error_message||"")}</div>
        <div><strong>Will retry:</strong> ${ev.will_retry ? "yes" : "no"}</div>
        <div><strong>Raw output:</strong><div class="code-block scrollable">${esc(ev.raw_output||"")}</div></div>`;
      if (t === "human_approval_requested") return `
        <div><strong>Approval ID:</strong> <code>${esc(ev.approval_id||"")}</code></div>
        <div><strong>Description:</strong> ${esc(ev.description||"")}</div>
        <div><strong>Pending patch:</strong><div class="code-block scrollable">${esc(fmt(ev.pending_patch||ev.patch||{}))}</div></div>`;
      if (t === "human_approval_resolved") return `
        <div><strong>Approval ID:</strong> <code>${esc(ev.approval_id||"")}</code></div>
        <div><strong>Decision:</strong> <code>${esc(ev.decision||"")}</code></div>`;
      if (t === "agent_errored") return `
        <div><strong>Error type:</strong> ${esc(ev.error_type||"")}</div>
        <div><strong>Message:</strong> ${esc(ev.error_message||"")}</div>
        <div><strong>Retry count:</strong> ${ev.retry_count||0}</div>`;
      if (t === "workflow_started") return `
        <div><strong>Goal:</strong> ${esc(ev.goal||"")}</div>
        <div><strong>Type:</strong> ${esc(ev.workflow_type||"")}</div>`;
      if (t === "workflow_completed") return `
        <div><strong>Final status:</strong> ${esc(ev.final_status||"")}</div>`;
      return `<div class="code-block scrollable">${esc(fmt(ev))}</div>`;
    }

    function renderEvent(ev) {
      const t  = evType(ev);
      const isApproval = t === "human_approval_requested" &&
                         approvalMap.has(`${currentWfId}:${ev.approval_id}`);
      const onclick = isApproval
        ? `openApprovalByEvent('${esc(ev.approval_id||"")}')`
        : `this.classList.toggle('open')`;
      return `
        <div class="evt" data-t="${esc(t)}" onclick="${onclick}">
          <div class="evt-stripe"></div>
          <div class="evt-body">
            <div class="evt-row">
              <div class="evt-time">${esc(fmtTime(ev.timestamp||0))}</div>
              <div class="evt-agent">${esc(ev.agent_id||"system")}</div>
              <div><span class="evt-type-badge">${esc(t)}</span></div>
              <div class="evt-summary">${evSummary(t,ev)}</div>
            </div>
            <div class="evt-detail">${evDetail(t,ev)}</div>
          </div>
        </div>`;
    }

    // ── State rendering ─────────────────────────────────────────────
    function statusPillClass(s) {
      if (s==="complete") return "status-complete";
      if (s==="running")  return "status-running";
      if (s==="failed")   return "status-failed";
      return "status-paused";
    }

    function renderFactVal(v) {
      if (v===null||v===undefined) return `<span class="fv-null">—</span>`;
      if (v===true)  return `<span class="fv-true">true</span>`;
      if (v===false) return `<span class="fv-false">false</span>`;
      if (typeof v==="number") return `<span class="fv-num">${v}</span>`;
      if (typeof v==="string") {
        if (v.length > 240) return `<div class="code-block scrollable">${esc(v)}</div>`;
        return esc(v);
      }
      return `<div class="code-block scrollable">${esc(fmt(v))}</div>`;
    }

    function renderState(state) {
      if (!state||!Object.keys(state).length)
        return `<div class="placeholder">No state available.</div>`;

      const meta = `
        <div class="state-meta">
          <div class="meta-card">
            <div class="meta-label">Workflow ID</div>
            <div class="meta-value mono">${esc(state.workflow_id||"")}</div>
          </div>
          <div class="meta-card">
            <div class="meta-label">Status</div>
            <div class="meta-value"><span class="status-pill ${statusPillClass(state.status||"")}">${esc(state.status||"")}</span></div>
          </div>
          <div class="meta-card">
            <div class="meta-label">Type</div>
            <div class="meta-value">${esc(state.workflow_type||"")}</div>
          </div>
          <div class="meta-card" style="grid-column:1/-1;">
            <div class="meta-label">Goal</div>
            <div class="meta-value">${esc(state.goal||"")}</div>
          </div>
        </div>`;

      const facts = state.facts||{};
      const factsHtml = Object.keys(facts).length
        ? `<div class="panel-title" style="margin-bottom:10px;">Facts</div>
           <table class="facts-table">
             ${Object.entries(facts).map(([k,v]) =>
               `<tr><td class="fk">${esc(k)}</td><td class="fv">${renderFactVal(v)}</td></tr>`
             ).join("")}
           </table>`
        : `<div class="placeholder" style="margin-top:12px;">No facts yet.</div>`;

      const tasks = Object.values(state.tasks||{});
      const tasksHtml = tasks.length
        ? `<div class="panel-title" style="margin-top:14px;margin-bottom:10px;">Tasks</div>
           <table class="facts-table">
             ${tasks.map(t => `<tr>
               <td class="fk">${esc((t.id||"").slice(0,8))}…</td>
               <td class="fv"><span class="status-pill ${statusPillClass(t.status||"")}">${esc(t.status||"")}</span> ${esc(t.description||"")}</td>
             </tr>`).join("")}
           </table>` : "";

      return meta + factsHtml + tasksHtml;
    }

    // ── Detail tab ──────────────────────────────────────────────────
    function renderDetail(events, state) {
      const el = document.getElementById("content");
      el.innerHTML = `
        <div class="panel">
          <div class="panel-title">Event Timeline <span class="count-pill">${events.length} events</span></div>
          <div class="timeline">
            ${events.length ? events.map(renderEvent).join("") : `<div class="placeholder">No events yet.</div>`}
          </div>
        </div>
        <div class="panel">
          <div class="panel-title">Current State</div>
          ${renderState(state)}
        </div>`;
    }

    // ── Live tab ────────────────────────────────────────────────────
    function renderLiveTab() {
      document.getElementById("content").innerHTML = `
        <div class="panel">
          <div class="panel-title">Live Events <span id="live-cnt" class="count-pill">${liveEvents.length}</span></div>
          <div id="live-stream" class="live-stream"></div>
        </div>`;
      liveEvents.slice().reverse().forEach(appendLiveRow);
    }

    function appendLiveRow(ev) {
      const stream = document.getElementById("live-stream");
      if (!stream) return;
      const t = evType(ev);
      const dc = dotColor(t);
      const row = document.createElement("div");
      row.className = "live-row";
      row.innerHTML = `
        <span class="dot ${dc}"></span>
        <span class="live-time">${esc(fmtTime(ev.timestamp||0))}</span>
        <span class="live-agent">${esc(ev.agent_id||"system")}</span>
        <span style="color:var(--muted);font-size:11px;">${esc(t)}</span>
        <span style="font-size:12px;">${evSummary(t,ev)}</span>`;
      stream.prepend(row);
      const cnt = document.getElementById("live-cnt");
      if (cnt) cnt.textContent = liveEvents.length;
    }

    function stopLive() { if (eventSource) { eventSource.close(); eventSource = null; } }

    function startLive(wfId) {
      stopLive();
      liveEvents = [];
      renderLiveTab();
      const url = `${BASE}/v1/workflows/${wfId}/events?key=${encodeURIComponent(API_KEY)}`;
      eventSource = new EventSource(url);
      eventSource.onmessage = (msg) => {
        const ev = JSON.parse(msg.data);
        liveEvents.push(ev);
        if (currentTab === "live") appendLiveRow(ev);
      };
      eventSource.onerror = () => {};
    }

    // ── Replay tab ──────────────────────────────────────────────────
    function replayAt(idx) {
      const s = {};
      for (let i = 0; i < idx; i++) {
        const ev = allEvents[i];
        if (ev.type === "patch_applied") {
          const parts = ev.target.split(".");
          let cur = s;
          for (let j = 0; j < parts.length-1; j++) {
            if (!cur[parts[j]] || typeof cur[parts[j]] !== "object") cur[parts[j]] = {};
            cur = cur[parts[j]];
          }
          cur[parts[parts.length-1]] = ev.new_value;
        }
      }
      return s;
    }

    function renderReplay(events) {
      document.getElementById("content").innerHTML = `
        <div class="panel">
          <div class="panel-title">State Scrubber</div>
          <div style="display:flex;flex-direction:column;gap:12px;">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);">
              <span id="replay-lbl">Step 0 of ${events.length}</span>
              <span>Built from patch_applied events</span>
            </div>
            <input id="replay-slider" type="range" min="0" max="${events.length}" value="0" />
            <div class="code-block" id="replay-state" style="max-height:calc(100vh - 270px);overflow:auto;">{}</div>
          </div>
        </div>`;
      const sl = document.getElementById("replay-slider");
      sl.addEventListener("input", () => {
        const idx = parseInt(sl.value, 10);
        document.getElementById("replay-lbl").textContent = `Step ${idx} of ${events.length}`;
        document.getElementById("replay-state").textContent = JSON.stringify(replayAt(idx), null, 2);
      });
    }

    // ── Trace tab ───────────────────────────────────────────────────
    function buildTurns(events) {
      const turns = [];
      let cur = null;
      events.forEach((ev, idx) => {
        if (ev.type === "context_sliced") {
          if (cur) turns.push(cur);
          cur = {
            agent_id: ev.agent_id,
            ctx_idx: idx,
            context_paths: ev.context_paths || [],
            prompts: [],
            model_calls: [],
            model_responses: [],
            validation_failures: [],
            tool_calls: [],
            patch: null,
            succeeded: false,
            total_latency: 0,
            total_tokens: 0,
          };
          return;
        }
        if (!cur) return;
        if (ev.type === "prompt_assembled")  cur.prompts.push(ev);
        if (ev.type === "model_called")      cur.model_calls.push(ev);
        if (ev.type === "model_returned") {
          cur.model_responses.push(ev);
          cur.total_latency += ev.latency_seconds||0;
          cur.total_tokens  += (ev.input_tokens||0)+(ev.output_tokens||0);
        }
        if (ev.type === "validation_failed") cur.validation_failures.push(ev);
        if (ev.type === "tool_called")       cur.tool_calls.push({called:ev,returned:null});
        if (ev.type === "tool_returned") {
          const p = cur.tool_calls.find(t => t.called.tool_call_id === ev.tool_call_id);
          if (p) p.returned = ev;
        }
        if (ev.type === "patch_applied") { cur.patch = ev; cur.succeeded = true; }
        if (ev.type === "agent_errored") { cur.succeeded = false; }
      });
      if (cur) turns.push(cur);
      return turns;
    }

    function getCtxValues(turn) {
      const s = replayAt(turn.ctx_idx);
      const vals = {};
      for (const path of turn.context_paths) {
        const parts = path.split(".");
        let v = s;
        for (const p of parts) v = v?.[p];
        vals[path] = v;
      }
      return vals;
    }

    function renderAgentDetail(turn) {
      const ctxVals = getCtxValues(turn);

      const ctxHtml = turn.context_paths.length
        ? `<table class="ctx-table">
            ${turn.context_paths.map(p => {
              const v = ctxVals[p];
              const disp = v === undefined ? '<span style="color:var(--muted)">—</span>'
                         : typeof v === "object" ? esc(fmt(v)).slice(0,400)
                         : esc(String(v)).slice(0,400);
              return `<tr><td class="cp">${esc(p)}</td><td class="cv">${disp}</td></tr>`;
            }).join("")}
           </table>`
        : `<div class="placeholder">No context declared.</div>`;

      const lastPrompt = turn.prompts.length ? turn.prompts[turn.prompts.length-1] : null;
      const promptHtml = lastPrompt
        ? `<div class="code-block scrollable">${esc(lastPrompt.prompt_text||"")}</div>`
        : `<div class="placeholder">No prompt assembled.</div>`;

      const lastResp = turn.model_responses.length ? turn.model_responses[turn.model_responses.length-1] : null;
      const respHtml = lastResp ? `
        <div class="model-stats">
          <div><span class="model-stat-key">Model:</span> <span class="model-stat-val">${esc(turn.model_calls[0]?.model||"")}</span></div>
          <div><span class="model-stat-key">Latency:</span> <span class="model-stat-val">${(lastResp.latency_seconds||0).toFixed(3)}s</span></div>
          <div><span class="model-stat-key">Input tokens:</span> <span class="model-stat-val">${lastResp.input_tokens||0}</span></div>
          <div><span class="model-stat-key">Output tokens:</span> <span class="model-stat-val">${lastResp.output_tokens||0}</span></div>
          ${lastResp.estimated_cost_usd ? `<div><span class="model-stat-key">Cost:</span> <span class="model-stat-val">$${lastResp.estimated_cost_usd.toFixed(4)}</span></div>` : ""}
        </div>
        <div class="code-block scrollable">${esc(lastResp.raw_response||"")}</div>`
        : `<div class="placeholder">No model response.</div>`;

      const patchHtml = turn.patch
        ? `<div class="patch-box">
             <div class="patch-target">→ ${esc(turn.patch.target||"")}</div>
             <div class="patch-reason">${esc(turn.patch.reason||"")}</div>
             <div class="code-block scrollable">${esc(fmt(turn.patch.new_value))}</div>
           </div>`
        : `<div class="no-patch-box">No patch produced — agent did not write to state.</div>`;

      const vfHtml = turn.validation_failures.length
        ? turn.validation_failures.map(f => `
            <div class="vf-box">
              <div class="vf-type">${esc(f.error_type||"error")}</div>
              <div class="vf-msg">${esc(f.error_message||"")}</div>
            </div>`).join("")
        : `<div class="placeholder">No validation failures.</div>`;

      const att = turn.prompts.length;
      const modelName = turn.model_calls[0]?.model || "";

      return `
        <details class="section" open>
          <summary><span class="section-arr">▶</span> Context received
            <span class="section-tag">${turn.context_paths.length} paths</span></summary>
          <div class="section-body">${ctxHtml}</div>
        </details>
        <details class="section">
          <summary><span class="section-arr">▶</span> Prompt assembled
            <span class="section-tag">${att} attempt${att!==1?"s":""}</span></summary>
          <div class="section-body">${promptHtml}</div>
        </details>
        <details class="section">
          <summary><span class="section-arr">▶</span> Model response
            <span class="section-tag">${esc(modelName)}</span></summary>
          <div class="section-body">${respHtml}</div>
        </details>
        <details class="section" open>
          <summary><span class="section-arr">▶</span> State written</summary>
          <div class="section-body">${patchHtml}</div>
        </details>
        ${turn.validation_failures.length ? `
        <details class="section">
          <summary><span class="section-arr">▶</span> Validation failures
            <span class="section-tag" style="color:var(--red);">${turn.validation_failures.length}</span></summary>
          <div class="section-body">${vfHtml}</div>
        </details>` : ""}`;
    }

    function renderTrace() {
      const turns = buildTurns(allEvents);
      const cards = turns.map((turn, idx) => {
        const sel = idx === selectedAgent ? " selected" : "";
        return `
          <div class="agent-card${sel}" onclick="selectAgent(${idx})">
            <div class="agent-card-top">
              <span class="agent-name">${esc(turn.agent_id||"agent")}</span>
              <span class="${turn.succeeded ? "agent-ok" : "agent-fail"}">${turn.succeeded ? "✓" : "✗"}</span>
            </div>
            <div class="agent-meta">
              <span>${turn.total_latency.toFixed(2)}s</span>
              <span>${turn.total_tokens} tok</span>
              <span>${turn.prompts.length} attempt${turn.prompts.length!==1?"s":""}</span>
              ${turn.validation_failures.length ? `<span style="color:var(--red);">${turn.validation_failures.length} retries</span>` : ""}
            </div>
          </div>`;
      }).join("");

      const detail = (selectedAgent !== null && turns[selectedAgent])
        ? renderAgentDetail(turns[selectedAgent])
        : `<div class="placeholder">Select an agent to see its full input and output.</div>`;

      document.getElementById("content").innerHTML = `
        <div class="trace-grid">
          <div>
            <div class="panel">
              <div class="panel-title">Agents <span class="count-pill">${turns.length}</span></div>
              <div class="agent-list">
                ${cards || `<div class="placeholder">No agent turns yet.</div>`}
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-title">Agent Detail</div>
            <div class="agent-detail">${detail}</div>
          </div>
        </div>`;

      if (selectedAgent === null && turns.length) selectAgent(0);
    }

    function selectAgent(idx) {
      selectedAgent = idx;
      renderTrace();
    }

    // ── Approvals ───────────────────────────────────────────────────
    async function loadApprovals(wfId) {
      if (!wfId) return;
      const data = await apiFetch(`/v1/workflows/${wfId}/approvals`);
      pendingApprovals = Array.isArray(data.approvals) ? data.approvals : [];
      approvalMap = new Map();
      for (const a of pendingApprovals) approvalMap.set(`${a.workflow_id}:${a.approval_id}`, a);
      updateApprovalBanner();
    }

    function updateApprovalBanner() {
      const banner = document.getElementById("approval-banner");
      const text   = document.getElementById("approval-banner-text");
      if (!pendingApprovals.length) { banner.classList.remove("visible"); return; }
      banner.classList.add("visible");
      text.textContent = `${pendingApprovals.length} pending approval${pendingApprovals.length!==1?"s":""} for this workflow.`;
    }

    async function refreshApprovals() {
      if (!currentWfId) return;
      await loadApprovals(currentWfId);
      renderCurrentTab();
    }

    // ── Workflow list ───────────────────────────────────────────────
    async function loadWorkflowList() {
      const data = await apiFetch("/v1/workflows");
      const ids  = Array.isArray(data.workflow_ids) ? data.workflow_ids : [];
      const list = document.getElementById("workflow-list");
      list.innerHTML = "";

      if (!ids.length) {
        list.innerHTML = `<div class="placeholder">No workflows yet.</div>`;
        return;
      }

      for (const id of ids) {
        let badge = "";
        try {
          const ap = await apiFetch(`/v1/workflows/${id}/approvals`);
          const cnt = Array.isArray(ap.approvals) ? ap.approvals.length : 0;
          badge = cnt ? `<span class="approval-badge">${cnt}</span>` : "";
        } catch {}

        const item = document.createElement("div");
        item.className = "wf-item" + (id === currentWfId ? " selected" : "");
        item.innerHTML = `<span class="wf-id-text">${esc(id)}</span>${badge}`;
        item.onclick = () => selectWorkflow(id);
        list.appendChild(item);
      }

      if (!currentWfId || !ids.includes(currentWfId)) selectWorkflow(ids[0]);
    }

    function selectWorkflow(id) {
      currentWfId   = id;
      selectedAgent = null;
      document.querySelectorAll(".wf-item").forEach(el =>
        el.classList.toggle("selected", el.querySelector(".wf-id-text")?.textContent === id)
      );
      document.getElementById("dl-btn").classList.remove("hidden");
      loadDetail(id);
      if (currentTab === "live") startLive(id);
    }

    async function loadDetail(id) {
      const [stateR, eventsR] = await Promise.all([
        apiFetch(`/v1/workflows/${id}`),
        apiFetch(`/v1/workflows/${id}/events-list`),
      ]);
      detailState = stateR.state || stateR;
      allEvents   = Array.isArray(eventsR.events) ? eventsR.events : [];
      wfStartTime = allEvents.length ? (allEvents[0].timestamp || null) : null;
      await loadApprovals(id);
      renderCurrentTab();
    }

    function renderCurrentTab() {
      if (currentTab === "detail") renderDetail(allEvents, detailState);
      if (currentTab === "replay") renderReplay(allEvents);
      if (currentTab === "trace")  renderTrace();
    }

    function setTab(name) {
      currentTab = name;
      document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
      if (name === "live") { currentWfId ? startLive(currentWfId) : renderLiveTab(); return; }
      renderCurrentTab();
    }

    // ── Download ────────────────────────────────────────────────────
    async function downloadWorkflow() {
      if (!currentWfId) return;
      try {
        const resp = await apiFetchRaw(`/v1/workflows/${currentWfId}/export`);
        const blob = await resp.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement("a");
        a.href     = url;
        a.download = `workflow_${currentWfId}.json`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (err) { alert("Export failed: " + err.message); }
    }

    // ── Approval modal ──────────────────────────────────────────────
    function openApprovalByEvent(approvalId) {
      const a = approvalMap.get(`${currentWfId}:${approvalId}`);
      if (a) openApprovalModal(a);
    }

    function openApprovalModal(approval) {
      activeApproval = approval;
      document.getElementById("approval-modal").classList.add("visible");
      document.getElementById("approval-modal").setAttribute("aria-hidden","false");
      document.getElementById("m-approval-id").textContent = approval.approval_id||"";
      document.getElementById("m-agent").textContent       = approval.agent_id||"";
      document.getElementById("m-target").textContent      = approval.target||approval.pending_patch?.target||"";
      document.getElementById("m-current").textContent     = fmt(approval.current_value??approval.pending_patch?.old_value??null);
      document.getElementById("m-proposed").textContent    = fmt(approval.proposed_value??approval.pending_patch?.value??approval.pending_patch?.new_value??null);
      document.getElementById("m-reason").textContent      = approval.reason||approval.description||"";
      document.getElementById("m-review-reason").value     = "";
      document.getElementById("m-modify-wrap").classList.add("hidden");
      document.getElementById("m-modified-json").value     = fmt(approval.proposed_value??approval.pending_patch?.value??null);
    }

    function closeApprovalModal() {
      activeApproval = null;
      document.getElementById("approval-modal").classList.remove("visible");
      document.getElementById("approval-modal").setAttribute("aria-hidden","true");
    }

    function showModifyEditor() {
      document.getElementById("m-modify-wrap").classList.remove("hidden");
    }

    async function submitApproval(decision) {
      if (!activeApproval||!currentWfId) return;
      let modified_patch = null;
      if (decision === "modified") {
        try { modified_patch = JSON.parse(document.getElementById("m-modified-json").value); }
        catch { alert("Modified patch must be valid JSON."); return; }
      }
      await apiFetch(`/v1/workflows/${currentWfId}/approvals/${activeApproval.approval_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, reason: document.getElementById("m-review-reason").value||"", modified_patch }),
      });
      closeApprovalModal();
      await loadDetail(currentWfId);
      await loadWorkflowList();
    }

    // ── Init ────────────────────────────────────────────────────────
    function showListError(err) {
      document.getElementById("workflow-list").innerHTML =
        `<div class="placeholder">${esc(String(err?.message||err))}</div>`;
    }

    document.addEventListener("DOMContentLoaded", () => {
      document.querySelectorAll(".tab").forEach(t =>
        t.addEventListener("click", () => setTab(t.dataset.tab))
      );
      document.getElementById("key-input").addEventListener("keydown", e => {
        if (e.key === "Enter") saveKey();
      });

      if (!API_KEY) {
        openKeyModal();
      } else {
        document.getElementById("app").classList.remove("hidden");
        loadWorkflowList().catch(showListError);
      }

      setInterval(async () => {
        try {
          await loadWorkflowList();
          if (currentWfId && currentTab !== "live") await loadDetail(currentWfId);
        } catch {}
      }, 5000);
    });
  </script>
</body>
</html>
"""
