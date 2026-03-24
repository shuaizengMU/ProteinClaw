import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from proteinclaw.agent.loop import run_agent
from proteinclaw.config import SUPPORTED_MODELS, settings

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str = settings.default_model
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    model = request.model if request.model in SUPPORTED_MODELS else settings.default_model
    reply_parts = []
    tool_calls_log = []

    async for event in run_agent(
        message=request.message,
        model=model,
        history=request.history,
    ):
        if event["type"] == "token":
            reply_parts.append(event["content"])
        elif event["type"] == "tool_call":
            tool_calls_log.append(event)
        elif event["type"] == "error":
            reply_parts.append(f"\n[Error: {event['message']}]")

    return ChatResponse(reply="".join(reply_parts).strip(), tool_calls=tool_calls_log)


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
            history = payload.get("history", [])

            if model not in SUPPORTED_MODELS:
                model = settings.default_model

            async for event in run_agent(message=message, model=model, history=history):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
