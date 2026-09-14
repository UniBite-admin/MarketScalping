"""Local read-only web UI for the existing MarketScalping Orchestrator.

This module intentionally exposes only GET endpoints and serves a simple
browser dashboard over localhost. It is a thin presentation layer: all data is
read from the authoritative Orchestrator, never from TaskStore files or workflow
policy files directly.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.operator_console import OperatorConsole
from tools.orchestrator_core import Orchestrator


def _redact_sensitive_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(token in key_lower for token in ("secret", "token", "key", "password", "passwd", "authorization", "bearer", "credential")):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact_sensitive_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_sensitive_value(item) for item in value]
    if isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in ("sk_live_", "pk_live_", "api_key", "token", "password", "secret")):
            return "[REDACTED]"
        return value
    return value


def _sanitize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = json.loads(json.dumps(task, default=str))
    sanitized = _redact_sensitive_value(sanitized)

    artifacts = sanitized.get("artifacts") or []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            content = artifact.get("content")
            if isinstance(content, dict):
                artifact["content"] = _redact_sensitive_value(content)
    return sanitized


def _sanitize_payload(payload: Any) -> Any:
    return _redact_sensitive_value(json.loads(json.dumps(payload, default=str)))


class LocalOperatorWebServer:
    def __init__(self, orch: Optional[Orchestrator] = None, host: str = "127.0.0.1", port: int = 8765):
        self.orch = orch or Orchestrator()
        self.host = host
        self.port = int(port)
        self.httpd: Optional[ThreadingHTTPServer] = None

    def _status_snapshot(self) -> Dict[str, Any]:
        snapshot = self.orch.build_operator_snapshot()
        return _sanitize_payload(snapshot)

    def _next_action_payload(self) -> Dict[str, Any]:
        console = OperatorConsole(self.orch)
        message = console._handle_next()
        tasks = self.orch.store.list_tasks()
        selected_task = None
        for task in tasks:
            if task is None:
                continue
            if task.get("task_id") is None:
                continue
            if task.get("task_id") in message:
                selected_task = task
                break

        payload = {
            "message": message,
            "task_id": selected_task.get("task_id") if selected_task else None,
            "status": (selected_task or {}).get("status", "UNKNOWN") if selected_task else "NONE",
            "deterministic": True,
        }
        return _sanitize_payload(payload)

    def _task_payload(self, task_id: str) -> Dict[str, Any]:
        task = self.orch.store.read_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return _sanitize_task(task)

    def _task_list_payload(self) -> List[Dict[str, Any]]:
        tasks = self.orch.store.list_tasks()
        return [_sanitize_task(task) for task in tasks]

    def _dashboard_html(self) -> str:
        return """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>MarketScalping Operator</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f4f6f8;
      color: #1f2937;
    }
    .page {
      max-width: 1100px;
      margin: 24px auto;
      padding: 0 16px 40px;
    }
    header {
      border-bottom: 2px solid #d1d5db;
      padding-bottom: 10px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.04em;
    }
    .status-pill {
      background: #e0f2fe;
      border: 1px solid #7dd3fc;
      color: #075985;
      padding: 6px 10px;
      border-radius: 999px;
      font-weight: bold;
      font-size: 12px;
    }
    section {
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 18px 20px;
      margin-bottom: 18px;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 18px;
    }
    .attention-box {
      background: #fff7ed;
      border: 1px solid #fdba74;
      padding: 12px 14px;
      border-radius: 8px;
      font-weight: 600;
    }
    .meta {
      margin-top: 8px;
      color: #374151;
      line-height: 1.5;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 6px;
    }
    th, td {
      border-bottom: 1px solid #e5e7eb;
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }
    th {
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #4b5563;
    }
    a.button {
      display: inline-block;
      text-decoration: none;
      background: #111827;
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      margin-right: 8px;
      margin-top: 8px;
      font-size: 13px;
    }
    .muted {
      color: #6b7280;
    }
    .task-detail {
      display: none;
      margin-top: 12px;
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px;
    }
  </style>
</head>
<body>
  <div class=\"page\">
    <header>
      <h1>MARKETSCALPING</h1>
      <div id=\"system-status-pill\" class=\"status-pill\">SYSTEM READY</div>
    </header>

    <section>
      <h2>WHAT NEEDS MY ATTENTION?</h2>
      <div id=\"attention\" class=\"attention-box\">Loading...</div>
    </section>

    <section>
      <h2>CURRENT TASK</h2>
      <div id=\"current-task\" class=\"meta\">Loading...</div>
      <div id=\"task-detail\" class=\"task-detail\"></div>
    </section>

    <section>
      <h2>TASKS</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>STATE</th>
            <th>AGENT</th>
            <th>ACTION</th>
          </tr>
        </thead>
        <tbody id=\"task-table\"></tbody>
      </table>
    </section>

    <section>
      <h2>ROADMAP</h2>
      <div id=\"roadmap\" class=\"meta\">Loading...</div>
    </section>
  </div>

  <script>
    async function fetchJson(url) {
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || 'Request failed');
      }
      return response.json();
    }

    function renderTaskDetail(task) {
      if (!task) {
        return 'No task selected.';
      }
      const blockers = (task.policy_results || []).filter(item => item.triggered && ['BLOCK', 'REQUIRE_HUMAN_APPROVAL', 'REQUIRE_SAFETY_REVIEW'].includes((item.decision || '').toUpperCase()));
      const policySummary = blockers.length ? blockers.map(item => `${item.policy_id || 'policy'}: ${item.decision || 'UNKNOWN'}`).join(', ') : 'None';
      const historyCount = Array.isArray(task.history) ? task.history.length : 0;
      const evidenceCount = Array.isArray(task.artifacts) ? task.artifacts.length : 0;
      return `
        <strong>${escape(task.title || 'Untitled')}</strong><br />
        ID: ${escape(task.task_id || 'unknown')}<br />
        Description: ${escape(task.description || 'N/A')}<br />
        Workflow state: ${escape(task.status || 'UNKNOWN')}<br />
        Roadmap stage: ${escape(task.roadmap_stage_id || 'N/A')}<br />
        Assigned agent: ${escape(task.assigned_agent || 'UNASSIGNED')}<br />
        Policy decisions: ${escape(policySummary)}<br />
        Artifact references: ${escape(String(evidenceCount))}<br />
        History entries: ${escape(String(historyCount))}
      `;
    }

    function escape(value) {
      return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function loadDashboard() {
      try {
        const status = await fetchJson('/api/operator/status');
        const next = await fetchJson('/api/operator/next');
        const tasks = await fetchJson('/api/tasks');

        const summary = status.summary || {};
        const statusPill = document.getElementById('system-status-pill');
        statusPill.textContent = 'SYSTEM READY';

        const attention = document.getElementById('attention');
        attention.innerHTML = `<div>${escape(next.message || 'No action required.')}</div>`;

        const current = Array.isArray(tasks) && tasks.length ? tasks[tasks.length - 1] : null;
        const currentTaskNode = document.getElementById('current-task');
        if (!current) {
          currentTaskNode.textContent = 'No current task available.';
        } else {
          currentTaskNode.innerHTML = `
            <strong>${escape(current.title || 'Untitled')}</strong><br />
            State: ${escape(current.status || 'UNKNOWN')}<br />
            Agent: ${escape(current.assigned_agent || 'UNASSIGNED')}<br />
            Task ID: ${escape(current.task_id || 'unknown')}
          `;
        }

        const taskTable = document.getElementById('task-table');
        taskTable.innerHTML = '';
        if (!tasks.length) {
          taskTable.innerHTML = '<tr><td colspan="4" class="muted">No tasks found.</td></tr>';
        } else {
          for (const task of tasks.slice(-10)) {
            const row = document.createElement('tr');
            row.innerHTML = `
              <td>${escape(task.task_id || 'unknown')}</td>
              <td>${escape(task.status || 'UNKNOWN')}</td>
              <td>${escape(task.assigned_agent || 'UNASSIGNED')}</td>
              <td><a href="#" class="button" data-task-id="${escape(task.task_id || '')}">DETAIL</a></td>
            `;
            row.querySelector('a').addEventListener('click', async (event) => {
              event.preventDefault();
              const id = event.currentTarget.dataset.taskId;
              const detail = await fetchJson(`/api/tasks/${encodeURIComponent(id)}`);
              document.getElementById('task-detail').style.display = 'block';
              document.getElementById('task-detail').innerHTML = renderTaskDetail(detail);
            });
            taskTable.appendChild(row);
          }
        }

        const roadmap = document.getElementById('roadmap');
        roadmap.innerHTML = `Current: ${escape((current && current.roadmap_stage_id) || 'N/A')}<br />Next: ${escape(summary && summary.next_stage_id ? summary.next_stage_id : 'N/A')}`;
      } catch (error) {
        document.getElementById('attention').textContent = 'Unable to load operator state.';
        document.getElementById('current-task').textContent = error.message || 'Unavailable';
      }
    }

    loadDashboard();
  </script>
</body>
</html>
"""

    def _json_response(self, payload: Any, status: int = 200) -> bytes:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return b"".join([
            b"HTTP/1.1 " + str(status).encode("utf-8") + b" \r\n",
            b"Content-Type: application/json; charset=utf-8\r\n",
            b"Cache-Control: no-store\r\n",
            b"Content-Length: " + str(len(encoded)).encode("utf-8") + b"\r\n",
            b"Connection: close\r\n\r\n",
            encoded,
        ])

    def _html_response(self, html: str, status: int = 200) -> bytes:
        encoded = html.encode("utf-8")
        return b"".join([
            b"HTTP/1.1 " + str(status).encode("utf-8") + b" \r\n",
            b"Content-Type: text/html; charset=utf-8\r\n",
            b"Cache-Control: no-store\r\n",
            b"Content-Length: " + str(len(encoded)).encode("utf-8") + b"\r\n",
            b"Connection: close\r\n\r\n",
            encoded,
        ])

    def _send_error(self, status: int, message: str) -> bytes:
        return self._json_response({"error": message}, status=status)

    def _handle_get(self, path: str) -> bytes:
        if path in {"/", "/index.html"}:
            return self._html_response(self._dashboard_html())

        if path == "/api/operator/status":
            return self._json_response(self._status_snapshot())

        if path == "/api/operator/next":
            return self._json_response(self._next_action_payload())

        if path == "/api/tasks":
            return self._json_response(self._task_list_payload())

        if path.startswith("/api/tasks/"):
            task_id = path.split("/api/tasks/", 1)[1].strip("/")
            if not task_id:
                return self._send_error(404, "Task not found")
            try:
                task = self._task_payload(task_id)
            except KeyError:
                return self._send_error(404, f"Task not found: {task_id}")
            return self._json_response(task)

        return self._send_error(404, "Not found")

    def start(self) -> "LocalOperatorWebServer":
        self.httpd = ThreadingHTTPServer((self.host, self.port), self._make_handler())
        self.httpd.app = self
        self._server_thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._server_thread.start()
        return self

    def serve_forever(self) -> None:
        if self.httpd is None:
            self.start()
        if hasattr(self, "_server_thread"):
            self._server_thread.join()

    def shutdown(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    def _make_handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                try:
                    response = app._handle_get(parsed.path)
                    self.wfile.write(response)
                except Exception:
                    payload = {"error": "internal server error"}
                    out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)

            def log_message(self, format: str, *args: Any) -> None:
                return

        return Handler


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Local MarketScalping operator dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind; localhost only by default")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on")
    args = parser.parse_args()

    server = LocalOperatorWebServer(host=args.host, port=args.port)
    print(f"MarketScalping local operator UI running at http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
