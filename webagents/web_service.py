import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


class ChatInput(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None


app = FastAPI(title="pythonAgents Web Service", version="0.1.0")


HTML_PAGE = """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>pythonAgents Web UI</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 16px; }
    textarea { width: 100%; min-height: 100px; padding: 8px; }
    button { margin-top: 8px; padding: 8px 14px; }
    pre { background: #f5f5f5; padding: 12px; white-space: pre-wrap; border-radius: 6px; }
    .row { margin: 16px 0; }
  </style>
</head>
<body>
  <h1>pythonAgents</h1>
  <p>Send a prompt to the agent container.</p>
  <div class=\"row\">
    <textarea id=\"prompt\" placeholder=\"Ask the agent to read, write, list files, or run calculations\"></textarea>
    <br />
    <button id=\"send\">Send</button>
    <div id=\"status\" style=\"margin-top:8px; font-size:14px; color:#555;\">Idle</div>
  </div>
  <div class=\"row\">
    <h3>Response</h3>
    <pre id=\"response\">(waiting for prompt)</pre>
  </div>
  <div class=\"row\">
    <h3>Metadata</h3>
    <pre id=\"metadata\">(no metadata yet)</pre>
  </div>
  <div class=\"row\">
    <h3>Tool Trace</h3>
    <pre id=\"trace\">(no tool calls yet)</pre>
  </div>
  <script>
    const sendButton = document.getElementById('send');
    const promptBox = document.getElementById('prompt');
    const responseBox = document.getElementById('response');
    const metadataBox = document.getElementById('metadata');
    const traceBox = document.getElementById('trace');
    const statusBox = document.getElementById('status');
    const SESSION_KEY = 'pythonagents.session_id';

    function createSessionId() {
      if (window.crypto && typeof window.crypto.randomUUID === 'function') {
        return window.crypto.randomUUID();
      }
      return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    }

    let sessionId = window.localStorage.getItem(SESSION_KEY);
    if (!sessionId) {
      sessionId = createSessionId();
      window.localStorage.setItem(SESSION_KEY, sessionId);
    }

    let processingTimer = null;
    let processingStartedAt = null;

    function setProcessingState(isProcessing) {
      if (isProcessing) {
        sendButton.disabled = true;
        sendButton.textContent = 'Processing...';
        processingStartedAt = Date.now();
        let dots = 0;
        statusBox.textContent = 'Processing request (0s)';
        processingTimer = setInterval(() => {
          dots = (dots + 1) % 4;
          const elapsedSeconds = Math.floor((Date.now() - processingStartedAt) / 1000);
          statusBox.textContent = `Processing request${'.'.repeat(dots)} (${elapsedSeconds}s)`;
        }, 400);
      } else {
        sendButton.disabled = false;
        sendButton.textContent = 'Send';
        if (processingTimer) {
          clearInterval(processingTimer);
          processingTimer = null;
        }
        processingStartedAt = null;
      }
    }

    sendButton.addEventListener('click', async () => {
      const prompt = promptBox.value.trim();
      if (!prompt) return;

      setProcessingState(true);
      responseBox.textContent = 'Running...';
      metadataBox.textContent = 'Running...';
      traceBox.textContent = 'Running...';
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, session_id: sessionId })
        });

        const data = await response.json();
        if (!response.ok) {
          responseBox.textContent = `Error: ${data.detail || 'Unknown error'}`;
          metadataBox.textContent = '(request failed)';
          traceBox.textContent = '(request failed)';
          statusBox.textContent = 'Request failed';
          return;
        }

        if (data.session_id) {
          sessionId = data.session_id;
          window.localStorage.setItem(SESSION_KEY, sessionId);
        }

        responseBox.textContent = data.response;
        metadataBox.textContent = JSON.stringify({
          model: data.model,
          session_id: data.session_id || sessionId,
          iterations: data.iterations,
          tool_calls: data.tool_calls,
          completed: data.completed,
          stop_reason: data.stop_reason
        }, null, 2);

        const toolTrace = Array.isArray(data.tool_trace) ? data.tool_trace : [];
        if (!toolTrace.length) {
          traceBox.textContent = '(no tool calls for this response)';
        } else {
          const lines = toolTrace.map((item, index) => {
            const args = JSON.stringify(item.args ?? {}, null, 0);
            return [
              `${index + 1}. iteration=${item.iteration} tool=${item.tool} status=${item.status}`,
              `   args: ${args}`,
              `   result_preview: ${item.result_preview}`
            ].join('\\n');
          });
          traceBox.textContent = lines.join('\\n\\n');
        }

        statusBox.textContent = 'Completed';
      } catch (error) {
        responseBox.textContent = `Request failed: ${error}`;
        metadataBox.textContent = '(request failed)';
        traceBox.textContent = '(request failed)';
        statusBox.textContent = 'Request failed';
      } finally {
        setProcessingState(false);
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict:
    """Return web service health status."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the embedded HTML user interface."""
    return HTML_PAGE


@app.post("/api/chat")
async def api_chat(chat_input: ChatInput) -> dict:
    """Forward chat requests to the agent service and relay JSON responses."""
    agent_base_url = os.getenv("AGENT_BASE_URL", "http://127.0.0.1:8001")
    request_timeout_seconds = float(os.getenv("AGENT_REQUEST_TIMEOUT", "300"))
    # Use explicit per-phase timeout values to handle long-running tool workflows.
    timeout = httpx.Timeout(
      connect=10.0,
      read=request_timeout_seconds,
      write=request_timeout_seconds,
      pool=10.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
      try:
        # Forward UI prompt/session to the agent service; agent owns conversation state.
        response = await client.post(
          f"{agent_base_url}/chat",
          json={"prompt": chat_input.prompt, "session_id": chat_input.session_id},
        )
      except httpx.HTTPError as exc:
        raise HTTPException(
          status_code=502, detail=f"Agent request failed: {str(exc)}"
        ) from exc

    if response.status_code >= 400:
      detail = response.text
      raise HTTPException(status_code=response.status_code, detail=detail)

    return response.json()
