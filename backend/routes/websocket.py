"""WebSocket 实时推送路由

提供 WebSocket 连接端点，前端连接后自动接收新邮件通知。
服务端通过后台实时监听（IDLE/STATUS/NOOP）检测新邮件，主动推送到所有已连接的客户端。
包含心跳检测机制，自动清理死连接。
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.sync import sync_service
from utils.logger import get_logger

logger = get_logger("websocket")

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接端点（带心跳检测）

    前端连接后自动接收新邮件通知，无需轮询。
    服务端有新邮件时通过后台实时监听检测，主动推送到所有已连接的客户端。

    心跳机制：
    - 每 60 秒内无消息则发送 ping 探活
    - ping 后 10 秒内无响应则判定连接已死，主动关闭并清理
    - 客户端收到 {"type": "ping"} 后应回复 {"type": "pong"}

    用户标识策略（与 deps.get_uid() 保持一致）：
    - 飞牛OS正式环境：网关注入 X-Trim-Userid 头，用该值作为 uid
    - 本地开发环境：该头缺失，fallback 到 "default"
    - 安全性：绕过网关直接访问只能收到 "default" 用户的推送，不会泄露其他用户数据
      （与 HTTP 接口的 get_uid() 安全性一致）
    """
    # 从网关请求头获取用户 uid，缺失时 fallback 到 "default"（与 deps.get_uid() 保持一致）
    uid = websocket.headers.get("X-Trim-Userid", "") or "default"

    await websocket.accept()
    logger.info("WebSocket 客户端已连接，uid=%s，当前连接数: %d", uid, len(sync_service.ws_clients) + 1)
    await sync_service.add_client(websocket, uid)
    try:
        while True:
            try:
                # 等待客户端消息，60 秒超时
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                # 客户端主动发来的 pong 响应或其它消息，正常处理
            except asyncio.TimeoutError:
                # 60 秒内无消息，发送 ping 探活
                try:
                    await websocket.send_json({"type": "ping"})
                    # 等待 pong 响应，10 秒超时
                    data = await asyncio.wait_for(websocket.receive_text(), timeout=10)
                except asyncio.TimeoutError:
                    # pong 超时，判定为死连接
                    logger.warning("WebSocket 心跳超时，关闭死连接")
                    break
                except Exception:
                    # 连接异常，判定为死连接
                    logger.warning("WebSocket 连接异常，关闭死连接")
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开连接")
    except Exception as e:
        logger.warning("WebSocket 异常: %s", e)
    finally:
        await sync_service.remove_client(websocket)
        logger.info("WebSocket 客户端已移除，当前连接数: %d", len(sync_service.ws_clients))
