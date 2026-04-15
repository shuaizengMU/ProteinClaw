import json
import os
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from proteinclaw.core.config import SUPPORTED_MODELS, settings
from proteinclaw.core.nanobot.adapter import WebSocketAdapter
from proteinclaw.core.nanobot.instance import get_nanobot, invalidate_nanobot

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str = settings.default_model
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """One-shot REST endpoint (used by CLI/tests). Collects all streamed tokens."""
    model = request.model if request.model in SUPPORTED_MODELS else settings.default_model
    tokens: list[str] = []
    tool_calls_log: list[dict] = []

    async def collect(event: dict) -> None:
        if event["type"] == "token":
            tokens.append(event["content"])
        elif event["type"] == "tool_call":
            tool_calls_log.append(event)

    bot = get_nanobot(model)
    adapter = WebSocketAdapter(send_json=collect)
    result = await bot.run(
        request.message,
        session_key=f"rest:{uuid.uuid4().hex}",
        hooks=[adapter],
    )
    reply = result.content or "".join(tokens)
    return ChatResponse(reply=reply.strip(), tool_calls=tool_calls_log)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            message = payload.get("message", "")
            model = payload.get("model", settings.default_model)
            api_key = payload.get("api_key", "")
            config_key = payload.get("config_key", "")
            # Use conversation-scoped session_key so nanobot memory persists across
            # sends in the same conversation (frontend opens a new WS per send).
            session_id = payload.get("session_id", "")
            session_key = f"conv:{session_id}" if session_id else f"ws:{uuid.uuid4().hex}"

            if model not in SUPPORTED_MODELS:
                model = settings.default_model

            # Apply API key from frontend if provided, then invalidate the cached
            # Nanobot instance so the next get_nanobot() rebuilds with the fresh key.
            if api_key and config_key:
                os.environ[config_key] = api_key
                invalidate_nanobot(model)

            try:
                bot = get_nanobot(model)
                adapter = WebSocketAdapter(send_json=websocket.send_json)
                await bot.run(message, session_key=session_key, hooks=[adapter])
                await websocket.send_json({"type": "done"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
