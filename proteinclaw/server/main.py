from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.server.tools import router as tools_router
from proteinclaw.server.chat import router as chat_router
from proteinclaw.server.feedback import router as feedback_router
from proteinclaw.core.config import load_user_config

# Load API keys from config.toml into environment on startup.
load_user_config()

app = FastAPI(title="ProteinClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(tools_router)
app.include_router(chat_router)
app.include_router(feedback_router)
