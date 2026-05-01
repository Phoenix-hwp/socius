"""FastAPI entrypoint for the Cursor 工作间 · Notion 作业 backend.

启动：
    uvicorn app.main:app --host 127.0.0.1 --port 8787 --reload

若 `frontend/dist` 已构建（`npm run build`），则挂载为站点根路径，与 `/health`、`/notion` 同源；
换机只需 Python + 仓库 + dist，无需为「使用」单独装 Node。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from .config import find_frontend_dist_dir, load_env_into_process
from .routes import cascader, databases, health, notion, pages

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
app.include_router(pages.router)
app.include_router(databases.router)
app.include_router(cascader.router)

_dist = find_frontend_dist_dir()
_dist_ready = _dist.is_dir() and (_dist / "index.html").is_file()

if _dist_ready:
    # 必须在所有 API 路由注册之后挂载；`html=True` 便于 React Router 刷新深链。
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """无前端构建产物时的占位说明。"""
        return {
            "service": "cursor-workspace-notion-backend",
            "docs": "/docs",
            "health": "/health",
            "hint": "前端未就绪：在 20-Projects/Cursor-Workspace/frontend 执行 npm install && npm run build",
        }
