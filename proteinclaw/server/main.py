from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.server.tools import router as tools_router
from proteinclaw.server.chat import router as chat_router

app = FastAPI(title="ProteinClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tools_router)
app.include_router(chat_router)
