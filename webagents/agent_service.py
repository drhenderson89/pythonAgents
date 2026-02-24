import json
import logging
import os
from functools import lru_cache
from threading import Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama.chat_models import ChatOllama
from pydantic import BaseModel, Field

from core.runtime import build_system_prompt, configure_runtime_logger, prompt_likely_requires_tools, run_agent_turns
import functions


LOGGER = logging.getLogger("pythonagents.agent_service")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str = Field(default_factory=lambda: os.getenv(
        "OLLAMA_MODEL", "qwen2.5:7b-instruct"))
    max_iterations: int = Field(default=20, ge=1, le=30)
    system_prompt: str | None = None
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    iterations: int
    tool_calls: int
    model: str
    session_id: str
    completed: bool
    stop_reason: str
    tool_trace: list[dict]


@lru_cache(maxsize=1)
def load_config() -> dict:
    """Load and cache service configuration from config.json."""
    # Cache config to avoid repeated file I/O per request.
    with open("config.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


app = FastAPI(title="pythonAgents Agent Service", version="0.1.0")
configure_runtime_logger(os.getenv("AGENT_LOG_LEVEL", "INFO"))
SESSION_LOCK = Lock()
SESSION_MESSAGES: dict[str, list] = {}
MAX_SESSION_COUNT = int(os.getenv("AGENT_MAX_SESSIONS", "200"))
MAX_MESSAGES_PER_SESSION = int(
    os.getenv("AGENT_MAX_MESSAGES_PER_SESSION", "200"))


def _trim_session_messages(messages: list) -> None:
    """Trim session history to configured limits while preserving system prompt."""
    # Bound memory growth by keeping the system message plus newest turns.
    if len(messages) <= MAX_MESSAGES_PER_SESSION:
        return

    if not messages:
        return

    system_message = messages[0]
    trimmed_tail = messages[-(MAX_MESSAGES_PER_SESSION - 1):]
    messages[:] = [system_message, *trimmed_tail]


def _get_or_create_session_messages(session_id: str, system_prompt: str) -> list:
    """Return session message history, creating or refreshing system prompt as needed."""
    # Session store keeps conversational continuity for the web client.
    with SESSION_LOCK:
        if session_id not in SESSION_MESSAGES:
            if len(SESSION_MESSAGES) >= MAX_SESSION_COUNT:
                oldest_session = next(iter(SESSION_MESSAGES))
                del SESSION_MESSAGES[oldest_session]

            SESSION_MESSAGES[session_id] = [
                SystemMessage(content=system_prompt)]

        session_messages = SESSION_MESSAGES[session_id]

        if not session_messages or not isinstance(session_messages[0], SystemMessage):
            session_messages.insert(0, SystemMessage(content=system_prompt))
        elif session_messages[0].content != system_prompt:
            session_messages[0] = SystemMessage(content=system_prompt)

        return session_messages


def _update_session_messages(session_id: str, messages: list) -> None:
    """Persist bounded session history for the given session id."""
    # Apply trimming before storing updated history.
    _trim_session_messages(messages)
    with SESSION_LOCK:
        SESSION_MESSAGES[session_id] = messages


@app.get("/health")
def health() -> dict:
    """Return a basic health status for liveness checks."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Process a chat prompt through model/tool runtime and return trace metadata."""
    # Resolve prompt, model, and runtime policy for this request.
    config = load_config()
    base_system_prompt = request.system_prompt or config["llm_options"]["system_prompt"]
    system_prompt = build_system_prompt(
        base_system_prompt, request.max_iterations)
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    session_id = request.session_id or str(uuid4())

    model = ChatOllama(
        model=request.model,
        base_url=ollama_base_url,
        temperature=config["llm_options"]["temperature"],
        num_ctx=config["llm_options"].get("num_ctx", 4096),
        num_predict=config["llm_options"]["tokens_to_generate"],
    )

    available_tools = functions.get_tools()
    model_with_tools = model.bind_tools(available_tools)
    # Shared loop expects a direct name-indexed tool map.
    tool_map = {tool.name: tool for tool in available_tools}

    messages = _get_or_create_session_messages(session_id, system_prompt)
    messages.append(HumanMessage(content=request.prompt))

    try:
        runtime_result = run_agent_turns(
            model_with_tools=model_with_tools,
            tool_map=tool_map,
            messages=messages,
            max_iterations=request.max_iterations,
            likely_requires_tools=prompt_likely_requires_tools(request.prompt),
            run_label=f"web:{session_id}",
        )
    except Exception as exc:
        LOGGER.exception("chat_runtime_exception session_id=%s", session_id)
        raise HTTPException(
            status_code=502, detail=f"Agent execution failed: {str(exc)}") from exc

    _update_session_messages(session_id, messages)

    return ChatResponse(
        response=runtime_result["response"],
        iterations=runtime_result["iterations"],
        tool_calls=runtime_result["tool_calls"],
        model=request.model,
        session_id=session_id,
        completed=runtime_result["completed"],
        stop_reason=runtime_result["stop_reason"],
        tool_trace=runtime_result["tool_trace"],
    )
