import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.server.tools import router as tools_router
from proteinclaw.server.chat import router as chat_router
from proteinclaw.server.feedback import router as feedback_router
from proteinclaw.server.case_studies import router as case_studies_router
from proteinclaw.core.config import load_user_config
from proteinclaw.core.nanobot.instance import set_workspace

# Load API keys from config.toml into environment on startup.
load_user_config()

# Initialize nanobot workspace. Use PROTEINCLAW_APP_DATA env var if set
# (Tauri sets this to the OS app data directory), otherwise ~/.proteinclaw
_app_data = os.environ.get("PROTEINCLAW_APP_DATA", str(Path.home() / ".proteinclaw"))
set_workspace(Path(_app_data) / "nanobot-workspace")

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
app.include_router(case_studies_router)
