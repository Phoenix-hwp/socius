"""FastAPI entrypoint for the Cursor 工作间 · Notion 作业 backend.

启动：
    uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_env_into_process
from .routes import databases, health, notion

load_env_into_process()

app = FastAPI(
    title="Cursor 工作间 · Notion 作业 — Local API",
    version="0.1.0",
    description="本机 API；浏览器只调用 localhost，Notion Token 仅由后端读取。",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(health.router)
app.include_router(notion.router)
app.include_router(databases.router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "service": "cursor-workspace-notion-backend",
        "docs": "/docs",
        "health": "/health",
    }
