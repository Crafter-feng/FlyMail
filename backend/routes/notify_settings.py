# -*- coding: utf-8 -*-
"""第三方通知设置 API。

与应用内铃铛通知无关；只读写 ext_notify_* 配置并提供渠道测试。
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Request

from deps import get_uid
from services.notify.settings import load_ext_notify_settings, save_ext_notify_settings
from services.notification_dispatch import send_test
from services.notify.registry import list_channels
from services.notify.imgbed.client import get_imgbed_client
from services.notify.imgbed.settings import imgbed_is_ready, normalize_imgbed
from services.notify.image_card import render_notify_card_png
from services.notify.render import build_test_event
from utils.logger import get_logger

logger = get_logger("routes.notify_settings")

router = APIRouter(tags=["第三方通知"])

# 已注册可测试渠道（与 registry 同步，便于扩展）
_TESTABLE_CHANNELS = frozenset(list_channels())


@router.get("/api/notify/settings", summary="获取第三方通知设置")
async def get_notify_settings(request: Request):
    """返回当前用户的第三方通知配置。"""
    uid = await get_uid(request)
    data = await load_ext_notify_settings(uid)
    return {"success": True, "data": data}


@router.put("/api/notify/settings", summary="保存第三方通知设置")
async def put_notify_settings(request: Request, body: dict = Body(...)):
    """保存全局开关、免打扰、模式、渠道与图床配置。"""
    uid = await get_uid(request)
    body = body or {}
    saved = await save_ext_notify_settings(uid, body)
    logger.info(
        "已保存第三方通知设置 user_uid=%s enabled=%s mode=%s bark=%s telegram=%s webhook=%s imgbed=%s",
        uid,
        saved.get("enabled"),
        saved.get("mode"),
        bool((saved.get("bark") or {}).get("enabled")),
        bool((saved.get("telegram") or {}).get("enabled")),
        bool((saved.get("webhook") or {}).get("enabled")),
        bool((saved.get("imgbed") or {}).get("base_url")),
    )
    return {"success": True, "message": "通知设置已保存", "data": saved}


@router.post("/api/notify/test", summary="测试第三方通知渠道")
async def test_notify_channel(request: Request, body: dict = Body(...)):
    """向指定渠道发送测试消息（绕过总开关与免打扰）。"""
    uid = await get_uid(request)
    body = body or {}
    channel = str(body.get("channel") or "").strip().lower()
    if channel not in _TESTABLE_CHANNELS:
        return {
            "success": False,
            "message": f"channel 须为 {', '.join(sorted(_TESTABLE_CHANNELS))}",
        }

    result = await send_test(uid, channel)
    return result


@router.post("/api/notify/imgbed/test", summary="测试自建图床上传")
async def test_imgbed(request: Request, body: dict = Body(None)):
    """使用当前/请求体中的图床配置上传一张测试卡片，返回公开 URL。"""
    uid = await get_uid(request)
    body = body or {}
    settings = await load_ext_notify_settings(uid)
    # 允许用表单未保存的配置直接测
    cfg = normalize_imgbed(body.get("imgbed") if "imgbed" in body else settings.get("imgbed"))
    if not imgbed_is_ready(cfg):
        return {
            "success": False,
            "message": "请先填写图床地址与上传密钥",
        }
    try:
        client = get_imgbed_client(cfg)
        await client.health()
        png = render_notify_card_png(build_test_event(), background="white")
        url = await client.upload_png(png)
        return {
            "success": True,
            "message": "图床测试成功",
            "data": {"url": url},
        }
    except Exception as e:
        logger.warning("图床测试失败 user_uid=%s: %s", uid, e)
        return {"success": False, "message": str(e) or "图床测试失败"}


@router.post("/api/notify/imgbed/purge", summary="清理自建图床图片")
async def purge_imgbed(request: Request, body: dict = Body(None)):
    """删除图床中全部图片（Bearer 鉴权，调用用户 Worker /purge）。"""
    uid = await get_uid(request)
    body = body or {}
    settings = await load_ext_notify_settings(uid)
    cfg = normalize_imgbed(body.get("imgbed") if "imgbed" in body else settings.get("imgbed"))
    if not imgbed_is_ready(cfg):
        return {
            "success": False,
            "message": "请先填写图床地址与上传密钥",
        }
    try:
        client = get_imgbed_client(cfg)
        deleted = await client.purge()
        return {
            "success": True,
            "message": f"已清理 {deleted} 张图片",
            "data": {"deleted": deleted},
        }
    except Exception as e:
        logger.warning("图床清理失败 user_uid=%s: %s", uid, e)
        return {"success": False, "message": str(e) or "图床清理失败"}
