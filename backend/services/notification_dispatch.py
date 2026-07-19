# -*- coding: utf-8 -*-
"""第三方通知分发编排。

与应用内铃铛（DB + WebSocket）完全独立：
- 仅消费统一事件载荷
- 失败只记日志，绝不反向影响铃铛路径
- HTTP 发送在后台任务中执行，避免阻塞 IDLE/同步
- 图片模式：Telegram / Webhook 直传 PNG；需公网 URL 的渠道（如 Bark）经全局自建图床上传
- 多渠道图片模式只渲染一次卡片 PNG，再按需上传图床或直传
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from utils.logger import get_logger
from utils.tasks import create_background_task
from services.notify.dnd import is_in_dnd
from services.notify.render import build_channel_message, build_test_event
from services.notify.registry import get_channel
from services.notify.settings import load_ext_notify_settings
from services.notify.types import ChannelMessage
from services.notify.imgbed.client import ImgbedConfigError, get_imgbed_client
from services.notify.imgbed.settings import imgbed_is_ready

logger = get_logger("notification_dispatch")


async def dispatch(event: Dict[str, Any]) -> None:
    """入口：立刻调度后台任务，调用方无需 await 发送结果。"""
    try:
        create_background_task(_dispatch_safe(dict(event or {})), name="ext_notify_dispatch")
    except Exception as e:
        logger.debug("调度第三方通知失败（忽略）: %s", e)


async def _dispatch_safe(event: Dict[str, Any]) -> None:
    """后台执行：总开关 → 免打扰 → 渲染 → 各渠道发送。"""
    try:
        await _dispatch_impl(event)
    except Exception as e:
        logger.warning("第三方通知分发异常: %s", e)


def _build_message(event: Dict[str, Any], mode: str) -> ChannelMessage:
    """按模式构建消息；图片模式生成 B 方案卡片 PNG。"""
    message = build_channel_message(event, mode=mode)
    if mode == "image":
        try:
            from services.notify.image_card import render_notify_card_png

            message.image_bytes = render_notify_card_png(event, background="white")
        except Exception as e:
            # 图片生成失败必须明确暴露，禁止静默改走文字
            raise RuntimeError(f"通知卡片图片生成失败: {e}") from e
    return message


async def _prepare_bark_image_message(
    event: Dict[str, Any],
    imgbed_cfg: Dict[str, Any],
    user_uid: str,
    *,
    image_message: Optional[ChannelMessage] = None,
) -> ChannelMessage:
    """为 Bark 构建图片消息：复用已渲染卡片（若有）并上传图床，写入 image_url。

    参数 image_message：分发层共享的图片消息，避免多渠道重复渲染 PNG。
    """
    if not imgbed_is_ready(imgbed_cfg):
        raise ImgbedConfigError(
            "Bark 图片模式需要配置 Cloudflare 图床：请在通知设置填写图床地址与上传密钥，"
            "并可点击 Deploy to Cloudflare 一键部署。"
        )
    message = image_message if image_message is not None else _build_message(event, "image")
    if not message.image_bytes:
        raise RuntimeError("通知卡片图片生成结果为空")

    # 复制一份，避免把 image_url 写回共享对象影响其它渠道
    out = ChannelMessage(
        title=message.title,
        body=message.body,
        mode="image",
        extra=dict(message.extra or {}),
        image_bytes=message.image_bytes,
    )
    client = get_imgbed_client(imgbed_cfg)
    image_url = await client.upload_png(out.image_bytes)
    if not image_url:
        raise RuntimeError("图床上传成功但未返回图片 URL")
    out.extra["image_url"] = image_url
    logger.info(
        "Bark 图片已上传图床 user_uid=%s url=%s",
        user_uid or "-",
        image_url[:160],
    )
    return out


async def _dispatch_impl(event: Dict[str, Any]) -> None:
    user_uid = str(event.get("user_uid") or "").strip()
    if not user_uid:
        logger.debug("第三方通知跳过：事件缺少 user_uid")
        return

    # 仅处理新邮件事件
    evt_type = str(event.get("type") or "new_mail")
    if evt_type not in ("new_mail",):
        return

    settings = await load_ext_notify_settings(user_uid)
    if not settings.get("enabled"):
        return

    if is_in_dnd(settings.get("dnd_start", "21:00"), settings.get("dnd_end", "07:00")):
        logger.debug("第三方通知处于免打扰，跳过 user_uid=%s", user_uid)
        return

    mode = settings.get("mode") or "text"
    bark_cfg = settings.get("bark") or {}
    tg_cfg = settings.get("telegram") or {}
    wh_cfg = settings.get("webhook") or {}
    imgbed_cfg = settings.get("imgbed") or {}
    bark_on = bool(bark_cfg.get("enabled"))
    tg_on = bool(tg_cfg.get("enabled"))
    wh_on = bool(wh_cfg.get("enabled"))
    if not bark_on and not tg_on and not wh_on:
        return

    need_image = mode == "image"
    need_tg_image = need_image and tg_on
    need_bark_image = need_image and bark_on
    # Webhook 图片与 Telegram 一致：直传 PNG 字节（Base64），不经图床
    need_wh_image = need_image and wh_on

    # 文字消息：文字模式各渠道使用；图片模式可不强制成功
    text_message: Optional[ChannelMessage] = None
    try:
        text_message = _build_message(event, "text")
    except Exception as e:
        if not need_image:
            logger.warning("第三方通知文字渲染失败 user_uid=%s: %s", user_uid, e)
            return
        logger.warning("第三方通知文字渲染失败（图片模式可忽略） user_uid=%s: %s", user_uid, e)

    # 图片模式：多渠道只渲染一次 PNG，再分别直传或上传图床
    shared_image_message: Optional[ChannelMessage] = None
    if need_tg_image or need_wh_image or need_bark_image:
        try:
            shared_image_message = _build_message(event, "image")
        except Exception as e:
            logger.warning(
                "第三方通知图片渲染失败，图片渠道本条跳过 user_uid=%s: %s",
                user_uid,
                e,
            )

    bark_image_message = None
    if need_bark_image:
        if shared_image_message is not None:
            try:
                bark_image_message = await _prepare_bark_image_message(
                    event,
                    imgbed_cfg,
                    user_uid,
                    image_message=shared_image_message,
                )
            except Exception as e:
                logger.warning(
                    "Bark 图片准备失败（不降级文字） user_uid=%s: %s",
                    user_uid,
                    e,
                )
        else:
            logger.warning(
                "Bark 图片跳过：卡片未生成 user_uid=%s",
                user_uid,
            )

    if bark_on:
        if need_bark_image:
            if bark_image_message is not None:
                await _send_one("bark", bark_image_message, bark_cfg, user_uid)
            # 失败不降级
        else:
            if text_message is not None:
                await _send_one("bark", text_message, bark_cfg, user_uid)

    if tg_on:
        if need_tg_image:
            if shared_image_message is not None:
                await _send_one("telegram", shared_image_message, tg_cfg, user_uid)
        else:
            if text_message is not None:
                await _send_one("telegram", text_message, tg_cfg, user_uid)

    if wh_on:
        if need_wh_image:
            if shared_image_message is not None:
                await _send_one("webhook", shared_image_message, wh_cfg, user_uid)
        else:
            if text_message is not None:
                await _send_one("webhook", text_message, wh_cfg, user_uid)


async def _send_one(
    channel_name: str,
    message: ChannelMessage,
    config: Dict[str, Any],
    user_uid: str,
) -> None:
    channel = get_channel(channel_name)
    if not channel:
        logger.warning("未知通知渠道: %s", channel_name)
        return
    try:
        await channel.send(message, config, user_uid=user_uid)
    except Exception as e:
        # 单渠道失败不影响其它渠道与铃铛
        logger.warning("渠道 %s 发送失败 user_uid=%s: %s", channel_name, user_uid, e)


async def send_test(user_uid: str, channel_name: str) -> Dict[str, Any]:
    """发送测试通知。

    绕过总开关与免打扰，只校验并发送指定渠道。
    - 文字 / 图片跟随用户当前全局模式
    - 需公网 URL 的渠道（如 Bark）图片模式依赖全局自建图床
    - Telegram / Webhook 图片模式直传 PNG，无需图床
    """
    settings = await load_ext_notify_settings(user_uid)
    channel_name = (channel_name or "").strip().lower()
    channel = get_channel(channel_name)
    if not channel:
        return {"success": False, "message": f"未知渠道: {channel_name}"}

    if channel_name == "bark":
        config = settings.get("bark") or {}
    elif channel_name == "telegram":
        config = settings.get("telegram") or {}
    elif channel_name == "webhook":
        config = settings.get("webhook") or {}
    else:
        config = {}

    err = channel.validate_config(config)
    if err:
        return {"success": False, "message": err}

    mode = settings.get("mode") or "text"
    event = build_test_event()
    imgbed_cfg = settings.get("imgbed") or {}

    try:
        if mode == "image" and channel_name == "bark":
            message = await _prepare_bark_image_message(event, imgbed_cfg, user_uid)
        elif mode == "image" and channel_name in ("telegram", "webhook"):
            message = _build_message(event, "image")
        else:
            message = _build_message(event, "text")
    except Exception as e:
        return {"success": False, "message": str(e) or "渲染失败"}

    try:
        await channel.send(message, config, user_uid=user_uid)
        label = "图片" if mode == "image" else "文字"
        return {"success": True, "message": f"{channel_name} 测试发送成功（{label}模式）"}
    except Exception as e:
        return {"success": False, "message": str(e) or "发送失败"}
