"""飞邮 FastAPI 应用入口

本文件仅负责：
1. 应用创建、中间件配置、生命周期管理
2. 路由模块注册
3. 通用端点（健康检查、用户信息）
4. 静态文件服务（SPA）
5. 双服务启动（Unix Socket + OAuth TCP 端口）

业务 API 端点已拆分到 routes/ 目录下的独立模块。
"""
import os
import sys
import io

# Nuitka 编译后在 Linux 环境下默认使用 ASCII 编码，强制设置为 UTF-8 以支持中文日志
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from config import GATEWAY_PREFIX
from db import init_db
from errors import AppError, app_error_handler
from schemas import HealthResponse, UserResponse
from services.settings import async_load_settings
from services.sync import sync_service
from utils.logger import setup_logging, get_logger
from version import VERSION

# 路由模块
from routes.accounts import router as accounts_router
from routes.auth import oauth_callback_app
from routes.backup import router as backup_router
from routes.compose import router as compose_router
from routes.contacts import router as contacts_router
from routes.folders import router as folders_router
from routes.messages import router as messages_router
from routes.notifications import router as notifications_router
from routes.settings import router as settings_router
from routes.signatures import router as signatures_router
from routes.websocket import router as websocket_router


# ==================== 日志配置 ====================

LOG_DIR = os.environ.get("FLYMAIL_DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
setup_logging(data_dir=LOG_DIR)
logger = get_logger("main")

# 前端静态文件目录（打包后位于 app/server/ui/，本地开发时位于 ../dist/ui/）
_ui_dir_env = os.environ.get("FLYMAIL_UI_DIR")
if _ui_dir_env and Path(_ui_dir_env).exists():
    UI_DIR = Path(_ui_dir_env)
else:
    _app_dir = Path(__file__).parent
    _candidate_dirs = [_app_dir / "ui", _app_dir.parent / "dist" / "ui"]
    _valid_ui_dirs = [path for path in _candidate_dirs if (path / "index.html").exists()]
    if _valid_ui_dirs:
        UI_DIR = max(_valid_ui_dirs, key=lambda path: (path / "index.html").stat().st_mtime)
    else:
        UI_DIR = _app_dir.parent / "dist" / "ui"
logger.info("UI_DIR selected: %s", UI_DIR)


# ==================== 生命周期 ====================

@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理（替代废弃的 on_event）"""
    # ---- startup ----
    await init_db()

    # Gmail 代理按用户存 user_settings，连接时经 Credentials.extra 注入，
    # 启动阶段不写进程全局 gmail_config，避免多用户共用同一代理。

    # 非阻塞启动后台 IMAP 监听和定时发送调度器
    from utils.tasks import create_background_task
    create_background_task(sync_service._start_all_idle(), name="start_all_idle")
    from services.scheduler import start_scheduler
    start_scheduler()

    logger.info("启动完成，日志目录: %s", LOG_DIR)
    yield

    # ---- shutdown ----
    await sync_service._stop_all_idle()
    from services.scheduler import shutdown_scheduler
    shutdown_scheduler()


# ==================== 应用创建 ====================

app = FastAPI(
    title="FlyMail 飞邮",
    description="飞邮 - 飞牛OS自托管邮件客户端，让您的邮件数据安全存储在本地 NAS。",
    version=VERSION,
    lifespan=lifespan,
    tags_metadata=[
        {"name": "通用", "description": "健康检查、用户信息"},
        {"name": "设置", "description": "应用配置（代理、聚合收件箱等）"},
        {"name": "账号", "description": "邮箱账号的增删改查、授权认证"},
        {"name": "邮件", "description": "邮件列表、详情、已读标记、删除、发送"},
        {"name": "通知", "description": "新邮件通知的持久化与管理"},
        {"name": "WebSocket", "description": "实时推送新邮件通知"},
    ],
)


# ==================== 中间件 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)


class StripPrefixMiddleware:
    """飞牛OS 网关前缀剥离中间件

    飞牛OS 统一网关将请求转发到 /app/flymail 前缀下，
    此中间件剥离该前缀，使路由定义无需包含网关前缀。
    同时支持 HTTP 和 WebSocket。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") in ("http", "websocket"):
            path = scope.get("path", "")
            if path.startswith(GATEWAY_PREFIX):
                new_path = path[len(GATEWAY_PREFIX):] or "/"
                scope["path"] = new_path
                scope["root_path"] = GATEWAY_PREFIX
        await self.app(scope, receive, send)


app.add_middleware(StripPrefixMiddleware)


# ==================== 路由注册 ====================

app.include_router(accounts_router)
app.include_router(backup_router)
app.include_router(compose_router)
app.include_router(contacts_router)
app.include_router(folders_router)
app.include_router(messages_router)
app.include_router(notifications_router)
app.include_router(settings_router)
app.include_router(signatures_router)
app.include_router(websocket_router)


# ==================== 通用端点 ====================

@app.get("/api/health", response_model=HealthResponse, tags=["通用"], summary="健康检查")
async def health():
    """检查服务是否正常运行，返回应用名和版本号"""
    return {"status": "ok", "app": "flymail", "version": VERSION}


@app.get("/api/user", response_model=UserResponse, tags=["通用"], summary="获取当前用户信息")
async def get_user(request: Request):
    """从飞牛OS网关的请求头中提取用户ID和用户名"""
    uid = request.headers.get("X-Trim-Userid", "")
    username = request.headers.get("X-Trim-Username", "")
    return {"uid": uid, "username": username}


# ==================== 静态文件 & SPA ====================

from utils.static_files import resolve_ui_file


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """SPA 兜底：静态文件优先，其余返回 index.html。

    C5：必须经 resolve_ui_file 约束在 UI_DIR 内，禁止 ../ 路径穿越读任意文件。
    """
    safe = resolve_ui_file(UI_DIR, full_path)
    if safe is not None:
        return FileResponse(str(safe))
    return FileResponse(str(UI_DIR / "index.html"))


# ==================== 双服务启动 ====================

if __name__ == "__main__":
    socket_path = os.environ.get("SOCKET_PATH", "flymail.sock")
    # OAuth 回调专用 TCP 端口（绕过飞牛网关认证，Google/Microsoft 回调是浏览器重定向不带 token）
    oauth_port = int(os.environ.get("OAUTH_PORT", "51010"))
    oauth_host = os.environ.get("OAUTH_HOST", "0.0.0.0")
    oauth_ipv6_host = os.environ.get("OAUTH_IPV6_HOST", "::")
    logger.info(
        "启动服务，socket: %s, OAuth端口: %d, IPv4监听: %s, IPv6监听: %s",
        socket_path, oauth_port, oauth_host, oauth_ipv6_host,
    )

    from uvicorn import Config, Server
    from uvicorn.config import WS_PROTOCOLS

    async def run_dual_servers():
        """在同一进程内并发运行 Unix Socket（主服务）和 TCP 端口（OAuth 回调）"""
        ws_protocol = "websockets-sansio" if "websockets-sansio" in WS_PROTOCOLS else "auto"
        socket_config = Config(app, uds=socket_path, log_level="warning", ws=ws_protocol)
        socket_server = Server(socket_config)

        # 分别监听 IPv4 和 IPv6，避免某些系统开启 IPV6_V6ONLY 后 host="::" 只能 IPv6 访问
        tcp_v4_config = Config(oauth_callback_app, host=oauth_host, port=oauth_port, log_level="warning")
        tcp_v4_server = Server(tcp_v4_config)
        tcp_v6_config = Config(oauth_callback_app, host=oauth_ipv6_host, port=oauth_port, log_level="warning")
        tcp_v6_server = Server(tcp_v6_config)

        async def safe_tcp_serve(server, host: str):
            """TCP 端口绑定失败时不影响主 Unix Socket 服务"""
            try:
                await server.serve()
            except OSError as e:
                logger.error("TCP %s:%d 绑定失败: %s，OAuth回调该地址族将不可用", host, oauth_port, e)

        logger.info("同时启动 Unix Socket + TCP IPv4/IPv6 端口服务")
        await asyncio.gather(
            socket_server.serve(),
            safe_tcp_serve(tcp_v4_server, oauth_host),
            safe_tcp_serve(tcp_v6_server, oauth_ipv6_host),
        )

    asyncio.run(run_dual_servers())
