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
from datetime import datetime
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

    def _approval_payload(self, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("request JSON must be an object")

        decision = payload.get("decision")
        if not isinstance(decision, str) or decision.upper() not in {"APPROVE", "REJECT"}:
            raise ValueError("decision must be APPROVE or REJECT")

        actor = payload.get("actor")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor is required")

        reason = payload.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason is required")

        confirm = payload.get("confirm")
        if confirm is not True:
            raise ValueError("confirm must be explicitly true")

        evidence_refs_raw = payload.get("evidence_refs", [])
        if evidence_refs_raw is None:
            evidence_refs_raw = []
        if not isinstance(evidence_refs_raw, list):
            raise ValueError("evidence_refs must be a list")

        evidence_refs: List[Dict[str, str]] = []
        for ref in evidence_refs_raw:
            if not isinstance(ref, dict):
                raise ValueError("each evidence_ref must be an object")
            artifact_id = ref.get("artifact_id")
            artifact_type = ref.get("artifact_type")
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                raise ValueError("each evidence_ref requires artifact_id")
            if not isinstance(artifact_type, str) or not artifact_type.strip():
                raise ValueError("each evidence_ref requires artifact_type")
            evidence_refs.append({"artifact_id": artifact_id, "artifact_type": artifact_type})

        task = self.orch.store.read_task(task_id)
        if task is None:
            raise KeyError(task_id)

        policy_context = {}
        for item in task.get("policy_results") or []:
            if isinstance(item, dict) and item.get("triggered") is True and str(item.get("decision") or "").upper() == "REQUIRE_HUMAN_APPROVAL":
                policy_context = item
                break

        return self.orch.record_human_approval(
            task_id=task_id,
            decision=str(decision).upper(),
            actor=str(actor).strip(),
            reason=str(reason).strip(),
            evidence_refs=evidence_refs,
            timestamp_utc=datetime.utcnow().isoformat() + "Z",
            workflow_state_at_decision="HUMAN_APPROVAL",
            policy_context=policy_context,
        )

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

    function renderApprovalForm(task) {
      const detailNode = document.getElementById('task-detail');
      if (!detailNode || !task || (task.status || '').toUpperCase() !== 'HUMAN_APPROVAL') {
        return;
      }

      const formHtml = `
        <div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid #d1d5db;">
          <div style="font-weight: bold; margin-bottom: 8px;">HUMAN APPROVAL REQUIRED</div>
          <div style="display: grid; gap: 8px; max-width: 420px;">
            <label>Actor<br /><input id="approval-actor" type="text" placeholder="operator" style="width: 100%; box-sizing: border-box;" /></label>
            <label>Reason<br /><textarea id="approval-reason" rows="3" placeholder="Explain the decision" style="width: 100%; box-sizing: border-box;"></textarea></label>
            <label>Evidence refs (optional, artifact_id:artifact_type, comma-separated)<br /><input id="approval-evidence" type="text" placeholder="artifact-id:safety_result" style="width: 100%; box-sizing: border-box;" /></label>
            <label><input id="approval-confirm" type="checkbox" /> I confirm this decision.</label>
            <div style="display: flex; gap: 8px;">
              <button id="approve-button" type="button">APPROVE</button>
              <button id="reject-button" type="button">REJECT</button>
            </div>
            <div id="approval-message" class="muted"></div>
          </div>
        </div>
      `;
      detailNode.innerHTML = `${renderTaskDetail(task)}${formHtml}`;

      async function submitApproval(decision) {
        const actor = document.getElementById('approval-actor').value.trim();
        const reason = document.getElementById('approval-reason').value.trim();
        const confirm = document.getElementById('approval-confirm').checked;
        const evidenceValue = document.getElementById('approval-evidence').value.trim();

        const evidenceRefs = evidenceValue
          ? evidenceValue.split(',').map(item => item.trim()).filter(Boolean).map(item => {
              const [artifactId, artifactType] = item.split(':').map(part => part.trim());
              if (!artifactId || !artifactType) {
                throw new Error('Evidence must use artifact_id:artifact_type format.');
              }
              return { artifact_id: artifactId, artifact_type: artifactType };
            })
          : [];

        if (!actor) throw new Error('Actor is required.');
        if (!reason) throw new Error('Reason is required.');
        if (!confirm) throw new Error('Confirmation is required.');

        const response = await fetch(`/api/tasks/${encodeURIComponent(task.task_id)}/approval`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, actor, reason, evidence_refs: evidenceRefs, confirm: true }),
        });

        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.error || 'Approval request rejected by the server.');
        }
        return payload;
      }

      document.getElementById('approve-button').addEventListener('click', async () => {
        try {
          const payload = await submitApproval('APPROVE');
          document.getElementById('approval-message').textContent = `APPROVE recorded: ${payload.record.approval_record_id}`;
          const refreshed = await fetchJson(`/api/tasks/${encodeURIComponent(task.task_id)}`);
          document.getElementById('task-detail').innerHTML = renderTaskDetail(refreshed);
          renderApprovalForm(refreshed);
        } catch (error) {
          document.getElementById('approval-message').textContent = error.message || 'Approval failed.';
        }
      });

      document.getElementById('reject-button').addEventListener('click', async () => {
        try {
          const payload = await submitApproval('REJECT');
          document.getElementById('approval-message').textContent = `REJECT recorded: ${payload.record.approval_record_id}`;
          const refreshed = await fetchJson(`/api/tasks/${encodeURIComponent(task.task_id)}`);
          document.getElementById('task-detail').innerHTML = renderTaskDetail(refreshed);
          renderApprovalForm(refreshed);
        } catch (error) {
          document.getElementById('approval-message').textContent = error.message || 'Approval failed.';
        }
      });
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
              renderApprovalForm(detail);
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
            if path.endswith("/approval"):
                return self._send_error(405, "Method not allowed: GET is not allowed for approval actions")
            task_id = path.split("/api/tasks/", 1)[1].strip("/")
            if not task_id:
                return self._send_error(404, "Task not found")
            try:
                task = self._task_payload(task_id)
            except KeyError:
                return self._send_error(404, f"Task not found: {task_id}")
            return self._json_response(task)

        return self._send_error(404, "Not found")

    def _handle_post(self, path: str, raw_body: bytes) -> bytes:
        if not path.startswith("/api/tasks/") or not path.endswith("/approval"):
            return self._send_error(404, "Not found")

        task_id = path[len("/api/tasks/") : -len("/approval")].strip("/")
        if not task_id:
            return self._send_error(404, "Task not found")

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._send_error(400, "invalid JSON body")

        try:
            record = self._approval_payload(task_id, payload)
        except KeyError:
            return self._send_error(404, f"Task not found: {task_id}")
        except ValueError as exc:
            return self._send_error(400, str(exc))
        except Exception as exc:  # pragma: no cover - authoritative contract drives remaining validation
            return self._send_error(409, str(exc))

        return self._json_response({"ok": True, "task_id": task_id, "record": record})

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

            def do_POST(self):
                parsed = urlparse(self.path)
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                    raw_body = self.rfile.read(content_length) if content_length > 0 else b""
                    response = app._handle_post(parsed.path, raw_body)
                    self.wfile.write(response)
                except Exception:
                    payload = {"error": "internal server error"}
                    out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)

            def do_PUT(self):
                payload = {"error": "Method not allowed"}
                out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(405)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_DELETE(self):
                payload = {"error": "Method not allowed"}
                out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(405)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_PATCH(self):
                payload = {"error": "Method not allowed"}
                out = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(405)
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
