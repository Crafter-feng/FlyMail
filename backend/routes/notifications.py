"""通知管理路由

处理新邮件通知的查询、标记已读、清空等操作。
通知由后台 IDLE/STATUS/NOOP 监听检测到新邮件时自动创建。
"""
from fastapi import APIRouter, Request, Query, Path as FastAPIPath
from db import get_notifications, mark_notification_read, mark_all_notifications_read, clear_notifications

from errors import AppError
from deps import get_uid
from schemas import NotificationListResponse, NotificationReadResponse, NotificationReadAllResponse, NotificationClearResponse

router = APIRouter(prefix="/api/notifications", tags=["通知"])


@router.get("", response_model=NotificationListResponse, summary="获取通知列表")
async def list_notifications(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200, description="返回通知数量上限"),
):
    """获取当前用户的新邮件通知列表，按时间倒序（从数据库读取）"""
    uid = await get_uid(request)
    notifications = await get_notifications(uid, limit)
    return {
        "notifications": [
            {
                "id": n.id,
                "account_id": n.account_id,
                "provider": n.provider,
                "email": n.email,
                "folder": n.folder,
                "is_read": n.is_read,
                "time": n.created_at * 1000,
                "type": n.type,
                "message": n.message,
                "message_cache_id": getattr(n, "message_cache_id", "") or "",
                "message_uid": int(getattr(n, "message_uid", 0) or 0),
                "rfc_message_id": getattr(n, "rfc_message_id", "") or "",
                "subject": getattr(n, "subject", "") or "",
                "from_addr": getattr(n, "from_addr", "") or "",
                "to_addr": getattr(n, "to_addr", "") or "",
                "cc": getattr(n, "cc", "") or "",
                "mail_date": getattr(n, "mail_date", "") or "",
                "body_preview": getattr(n, "body_preview", "") or "",
                "has_attachments": bool(getattr(n, "has_attachments", False)),
                "batch_count": int(getattr(n, "batch_count", 1) or 1),
            }
            for n in notifications
        ]
    }


@router.post("/{notification_id}/read", response_model=NotificationReadResponse, summary="标记单条通知已读")
async def mark_notification_as_read(
    notification_id: str = FastAPIPath(description="通知ID"),
    request: Request = None,
):
    """点击单条通知后标记为已读"""
    uid = await get_uid(request)
    updated = await mark_notification_read(notification_id, uid)
    if updated:
        return {"success": True}
    raise AppError(404, "Notification not found")


@router.post("/read-all", response_model=NotificationReadAllResponse, summary="标记全部通知已读")
async def mark_all_notifications_as_read(request: Request):
    """一键标记所有通知为已读"""
    uid = await get_uid(request)
    count = await mark_all_notifications_read(uid)
    return {"success": True, "updated": count}


@router.delete("", response_model=NotificationClearResponse, summary="清空所有通知")
async def delete_all_notifications(request: Request):
    """清空当前用户的所有通知记录"""
    uid = await get_uid(request)
    count = await clear_notifications(uid)
    return {"success": True, "deleted": count}
