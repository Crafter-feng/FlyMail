# -*- coding: utf-8 -*-
"""通用 Webhook 通知渠道。

向用户配置的 HTTP URL 发送 JSON。

平台自动识别（按 URL，无需用户手动选类型）：
- 通用：飞邮结构化 JSON（文字 / 图片 Base64）
- 企业微信：msgtype markdown / image（图片直传 Base64+md5）
- 钉钉：msgtype markdown；图片需图床后以 Markdown 插图
- 飞书/Lark：msg_type post / interactive；图片需图床后发卡片链接

可选 secret：
- 通用：Authorization Bearer
- 钉钉：加签密钥（SEC 开头，写入 URL 的 timestamp/sign）
- 飞书：签名校验密钥（写入 body 的 timestamp/sign）
- 企业微信：忽略（key 在 URL 中）

可选复用 Gmail 网络代理。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from utils.logger import get_logger
from services.notify.channels.base import NotifyChannel
from services.notify.http_client import build_async_client
from services.notify.render import build_body_markdown, _format_mail_date, _s
from services.notify.types import ChannelMessage

logger = get_logger("notify.webhook")

# 各平台文本长度保守上限（UTF-8 字节）
_CONTENT_MAX_BYTES = {
    "wecom": 4000,
    "dingtalk": 18000,
    "feishu": 28000,
    "generic": 100000,
}

# 平台中文名（日志 / 报错）
_PLATFORM_LABEL = {
    "wecom": "企业微信",
    "dingtalk": "钉钉",
    "feishu": "飞书",
    "generic": "通用",
}


def _valid_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def detect_webhook_platform(url: str) -> str:
    """根据 URL 识别目标平台：wecom / dingtalk / feishu / generic。"""
    try:
        p = urlparse((url or "").strip())
        host = (p.hostname or "").lower()
        path = (p.path or "").lower()
    except Exception:
        return "generic"

    # 企业微信
    if "qyapi.weixin.qq.com" in host and "webhook" in path:
        return "wecom"
    if path.rstrip("/").endswith("/cgi-bin/webhook/send"):
        return "wecom"

    # 钉钉
    if "oapi.dingtalk.com" in host and "robot" in path:
        return "dingtalk"
    if "dingtalk.com" in host and ("robot/send" in path or ("robot" in path and "send" in path)):
        return "dingtalk"

    # 飞书 / Lark
    if any(
        h in host
        for h in (
            "open.feishu.cn",
            "open.larksuite.com",
            "www.feishu.cn",
            "open.feishu.net",
        )
    ) and ("hook" in path or "bot" in path):
        return "feishu"
    if "feishu.cn" in host and "hook" in path:
        return "feishu"
    if "larksuite.com" in host and "hook" in path:
        return "feishu"

    return "generic"


def _truncate_utf8(text: str, max_bytes: int) -> str:
    """按 UTF-8 字节截断。"""
    raw = (text or "").strip()
    if not raw:
        return raw
    data = raw.encode("utf-8")
    if len(data) <= max_bytes:
        return raw
    cut = data[: max(0, max_bytes - 3)]
    while cut:
        try:
            return cut.decode("utf-8") + "…"
        except UnicodeDecodeError:
            cut = cut[:-1]
    return "…"


def _plain_body_text(message: ChannelMessage) -> str:
    """生成与各渠道一致的 Markdown/纯文本正文。"""
    extra = dict(message.extra or {})
    if extra:
        content = build_body_markdown(extra, dialect="common")
    else:
        content = message.body or ""
    title = (message.title or "飞邮").strip()
    if title and content and not content.lstrip().startswith(title):
        content = f"**{title}**\n\n{content}"
    elif title and not content:
        content = title
    return (content or "飞邮通知").strip()


class WebhookChannel(NotifyChannel):
    """通用 Webhook：按 URL 自动适配平台格式。"""

    name = "webhook"

    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        cfg = config or {}
        url = str(cfg.get("url") or "").strip()
        if not url:
            return "请填写 Webhook URL"
        if not _valid_http_url(url):
            return "Webhook URL 须为合法 http/https 地址"
        return None

    async def _resolve_proxy(self, config: Dict[str, Any], user_uid: str) -> Optional[str]:
        """若开启 use_gmail_proxy，则读取 Gmail 代理 URL。"""
        if not config.get("use_gmail_proxy"):
            return None
        if not user_uid:
            logger.debug("Webhook 已勾选代理但 user_uid 为空，直连")
            return None
        try:
            from services.settings import get_gmail_proxy_settings

            ps = await get_gmail_proxy_settings(user_uid)
            if ps.get("gmail_proxy_enabled") and ps.get("gmail_proxy_url"):
                return str(ps["gmail_proxy_url"]).strip()
            logger.debug(
                "Webhook 已勾选复用 Gmail 代理，但代理未启用或 URL 为空，将直连"
            )
        except Exception as e:
            logger.warning("读取 Gmail 代理失败，Webhook 将直连: %s", e)
        return None

    def _auth_headers(self, config: Dict[str, Any], *, platform: str) -> Dict[str, str]:
        """构建请求头。

        企业微信 / 钉钉 / 飞书：不使用 Bearer（密钥用于加签或已在 URL）。
        通用：可选 Authorization Bearer。
        """
        headers: Dict[str, str] = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "FlyMail-Webhook/1.0",
        }
        if platform != "generic":
            return headers
        secret = str(config.get("secret") or "").strip()
        if secret:
            if secret.lower().startswith("bearer "):
                headers["Authorization"] = secret
            else:
                headers["Authorization"] = f"Bearer {secret}"
        return headers

    def _build_generic_text(self, message: ChannelMessage) -> Dict[str, Any]:
        extra = dict(message.extra or {})
        if extra:
            body_md = build_body_markdown(extra, dialect="common")
        else:
            body_md = message.body or ""
        subject = _s(extra.get("subject"), "(无主题)")
        cc = str(extra.get("cc") or "").strip()
        payload: Dict[str, Any] = {
            "event": str(extra.get("type") or "new_mail"),
            "mode": "text",
            "title": message.title or "飞邮",
            "subject": subject,
            "body": body_md,
            "from": _s(extra.get("from_addr"), ""),
            "to": _s(extra.get("to_addr"), ""),
            "time": _format_mail_date(extra.get("mail_date")),
            "account": _s(extra.get("email"), ""),
            "preview": str(extra.get("body_preview") or "").strip(),
            "message_cache_id": str(extra.get("message_cache_id") or "").strip(),
        }
        if cc:
            payload["cc"] = cc
        return payload

    def _build_generic_image(self, message: ChannelMessage) -> Dict[str, Any]:
        if not message.image_bytes:
            raise RuntimeError("图片模式缺少卡片数据，无法推送 Webhook")
        extra = dict(message.extra or {})
        b64 = base64.b64encode(message.image_bytes).decode("ascii")
        return {
            "event": str(extra.get("type") or "new_mail"),
            "mode": "image",
            "image_base64": b64,
            "image_content_type": "image/png",
            "filename": "flymail-notify.png",
            "subject": _s(extra.get("subject"), "(无主题)"),
            "message_cache_id": str(extra.get("message_cache_id") or "").strip(),
        }

    def _build_wecom_text(self, message: ChannelMessage) -> Dict[str, Any]:
        content = _truncate_utf8(_plain_body_text(message), _CONTENT_MAX_BYTES["wecom"])
        return {"msgtype": "markdown", "markdown": {"content": content or "飞邮通知"}}

    def _build_wecom_image(self, message: ChannelMessage) -> Dict[str, Any]:
        if not message.image_bytes:
            raise RuntimeError("图片模式缺少卡片数据，无法推送企业微信 Webhook")
        raw = message.image_bytes
        if len(raw) > 2 * 1024 * 1024:
            raise RuntimeError(
                f"企业微信图片超过 2MB 限制（当前 {len(raw)} 字节），请缩短正文或改用文字模式"
            )
        return {
            "msgtype": "image",
            "image": {
                "base64": base64.b64encode(raw).decode("ascii"),
                "md5": hashlib.md5(raw).hexdigest(),
            },
        }

    def _dingtalk_sign_url(self, url: str, secret: str) -> str:
        """钉钉加签：在 URL 上追加 timestamp 与 sign。"""
        secret = (secret or "").strip()
        if not secret:
            return url
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
        h = hmac.new(secret.encode("utf-8"), string_to_sign, digestmod=hashlib.sha256).digest()
        sign = quote_plus(base64.b64encode(h))
        p = urlparse(url)
        q = [
            (k, v)
            for k, v in parse_qsl(p.query, keep_blank_values=True)
            if k not in ("timestamp", "sign")
        ]
        q.append(("timestamp", timestamp))
        q.append(("sign", sign))
        return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))

    def _build_dingtalk_text(self, message: ChannelMessage) -> Dict[str, Any]:
        extra = dict(message.extra or {})
        title = (message.title or "飞邮").strip() or "飞邮"
        subject = _s(extra.get("subject"), "飞邮通知")
        text = _truncate_utf8(_plain_body_text(message), _CONTENT_MAX_BYTES["dingtalk"])
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": subject if subject != "—" else title,
                "text": text or title,
            },
        }

    def _build_dingtalk_image(self, image_url: str, message: ChannelMessage) -> Dict[str, Any]:
        """钉钉无原生 Base64 图，使用 Markdown 插图展示公网图。"""
        extra = dict(message.extra or {})
        subject = _s(extra.get("subject"), "飞邮通知")
        text = f"![{subject}]({image_url})"
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": subject if subject != "—" else "飞邮",
                "text": text,
            },
        }

    def _feishu_sign_fields(self, secret: str) -> Dict[str, Any]:
        """飞书签名校验字段（开启签名时必填）。"""
        secret = (secret or "").strip()
        if not secret:
            return {}
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{secret}"
        h = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        sign = base64.b64encode(h).decode("utf-8")
        return {"timestamp": timestamp, "sign": sign}

    def _build_feishu_text(self, message: ChannelMessage) -> Dict[str, Any]:
        """飞书富文本 post：标题 + 分行正文。"""
        extra = dict(message.extra or {})
        title = (message.title or "飞邮").strip() or "飞邮"
        subject = _s(extra.get("subject"), "(无主题)")
        body = _truncate_utf8(_plain_body_text(message), _CONTENT_MAX_BYTES["feishu"])
        lines = []
        for line in body.replace("\r\n", "\n").split("\n"):
            plain = line.replace("**", "").replace("__", "").replace("`", "")
            lines.append([{"tag": "text", "text": plain if plain else " "}])
        if not lines:
            lines = [[{"tag": "text", "text": title}]]
        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": subject if subject not in ("—", "(无主题)") else title,
                        "content": lines,
                    }
                }
            },
        }

    def _build_feishu_image(self, image_url: str, message: ChannelMessage) -> Dict[str, Any]:
        """飞书自定义机器人无法直传图片字节，用卡片 + 打开图片按钮。"""
        extra = dict(message.extra or {})
        subject = _s(extra.get("subject"), "飞邮通知")
        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "blue",
                    "title": {
                        "tag": "plain_text",
                        "content": subject if subject != "—" else "飞邮",
                    },
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"飞邮通知卡片\n[点击查看大图]({image_url})",
                        },
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "打开图片"},
                                "type": "primary",
                                "url": image_url,
                            }
                        ],
                    },
                ],
            },
        }

    async def _upload_image_url(self, message: ChannelMessage, user_uid: str, platform: str) -> str:
        """上传卡片到用户图床，返回公网 URL。"""
        if not message.image_bytes:
            raise RuntimeError("图片模式缺少卡片数据")
        label = _PLATFORM_LABEL.get(platform, platform)
        try:
            from services.notify.imgbed.client import ImgbedConfigError, get_imgbed_client
            from services.notify.imgbed.settings import load_imgbed_settings
        except Exception as e:
            raise RuntimeError(f"{label} 图片模式需要图床模块: {e}") from e

        cfg = await load_imgbed_settings(user_uid or "")
        try:
            client = get_imgbed_client(cfg)
            client.ensure_ready()
        except ImgbedConfigError as e:
            raise RuntimeError(
                f"{label} 图片模式需配置 Cloudflare 图床（地址 + 上传密钥）。{e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"{label} 图床未就绪: {e}") from e

        url = await client.upload_png(message.image_bytes, filename="flymail-notify.png")
        if not url:
            raise RuntimeError(f"{label} 图床上传未返回 URL")
        return url

    def _parse_biz_error(
        self, resp, *, platform: str
    ) -> Optional[Tuple[Any, str]]:
        """解析业务错误，返回 (code, message)；成功返回 None。

        注意：HTTP 已成功响应时，绝不能因业务瞬时码自动重试 POST，
        否则（尤其钉钉图片）可能重复推送到群。
        """
        text = (resp.text or "").strip()
        if resp.status_code >= 400:
            return (
                resp.status_code,
                f"HTTP {resp.status_code}: {text[:300]}",
            )

        data: Any = None
        if text.startswith("{") or text.startswith("["):
            try:
                data = json.loads(text)
            except Exception:
                data = None

        if not isinstance(data, dict):
            if platform in ("wecom", "dingtalk", "feishu"):
                logger.warning(
                    "%s Webhook 响应非 JSON: %s",
                    _PLATFORM_LABEL.get(platform, platform),
                    text[:200],
                )
            return None

        # 企业微信 / 钉钉：errcode
        if "errcode" in data:
            raw_code = data.get("errcode")
            try:
                code_i = int(raw_code)
            except Exception:
                return (None, f"无法解析 errcode={raw_code!r}: {text[:200]}")
            if code_i == 0:
                return None
            errmsg = str(data.get("errmsg") or data.get("message") or text)[:300]
            return (code_i, errmsg)

        # 飞书：code / StatusCode
        if platform == "feishu":
            code = data.get("code", data.get("StatusCode", data.get("statusCode")))
            if code is not None:
                try:
                    code_i = int(code)
                except Exception:
                    return (None, f"无法解析飞书 code={code!r}: {text[:200]}")
                if code_i == 0:
                    return None
                msg = str(
                    data.get("msg")
                    or data.get("StatusMessage")
                    or data.get("message")
                    or text
                )[:300]
                return (code_i, msg)
            return None

        # 通用：明确错误码
        for key in ("code", "error_code"):
            if key not in data:
                continue
            val = data.get(key)
            if val in (0, "0", "ok", "OK", "success", "Success", True, "true"):
                return None
            try:
                n = int(val)
            except Exception:
                continue
            if n != 0:
                msg = str(
                    data.get("message") or data.get("msg") or data.get("errmsg") or text
                )[:300]
                return (n, msg)
        return None

    def _is_ambiguous_delivery(
        self, platform: str, code: Any, errmsg: str
    ) -> bool:
        """请求是否「可能已送达」——此时不得重试 POST，也避免误报失败诱使连点。

        钉钉常见：errcode=-1 系统繁忙，群里其实已收到。
        """
        try:
            code_i = int(code) if code is not None else None
        except Exception:
            code_i = None
        msg = (errmsg or "").lower()
        if platform in ("dingtalk", "wecom") and code_i == -1:
            return True
        if "系统繁忙" in (errmsg or "") or "system busy" in msg:
            return True
        return False

    def _format_biz_error(self, platform: str, code: Any, errmsg: str) -> str:
        """生成可读的中文错误信息。"""
        label = _PLATFORM_LABEL.get(platform, "Webhook")
        if code is None:
            return f"{label} 业务失败: {errmsg}"
        return f"{label} 业务失败 errcode={code}: {errmsg}"

    def _raise_if_failed(self, resp, *, platform: str) -> None:
        """根据 HTTP 与业务 JSON 判断失败。

        歧义送达（如钉钉 -1）按成功处理并打警告日志，避免自动重试导致重复推送。
        """
        err = self._parse_biz_error(resp, platform=platform)
        if err is None:
            return
        code, errmsg = err
        if self._is_ambiguous_delivery(platform, code, errmsg):
            logger.warning(
                "Webhook 返回歧义结果，按已送达处理（不重试、不报失败）"
                " platform=%s code=%s msg=%s",
                platform,
                code,
                errmsg[:200],
            )
            return
        raise RuntimeError(self._format_biz_error(platform, code, errmsg))

    async def send(
        self,
        message: ChannelMessage,
        config: Dict[str, Any],
        *,
        user_uid: str = "",
    ) -> None:
        err = self.validate_config(config)
        if err:
            raise ValueError(err)

        base_url = str(config.get("url") or "").strip()
        secret = str(config.get("secret") or "").strip()
        platform = detect_webhook_platform(base_url)
        proxy_url = await self._resolve_proxy(config, user_uid)
        headers = self._auth_headers(config, platform=platform)
        mode = (message.mode or "text").strip().lower()
        timeout = 45.0 if mode == "image" else 20.0

        # 构造 payload（图片只上传一次，避免重复图床）
        if platform == "wecom":
            payload = (
                self._build_wecom_image(message)
                if mode == "image"
                else self._build_wecom_text(message)
            )
        elif platform == "dingtalk":
            if mode == "image":
                image_url = await self._upload_image_url(message, user_uid, platform)
                payload = self._build_dingtalk_image(image_url, message)
            else:
                payload = self._build_dingtalk_text(message)
        elif platform == "feishu":
            if mode == "image":
                image_url = await self._upload_image_url(message, user_uid, platform)
                payload = self._build_feishu_image(image_url, message)
            else:
                payload = self._build_feishu_text(message)
        else:
            payload = (
                self._build_generic_image(message)
                if mode == "image"
                else self._build_generic_text(message)
            )

        # 只 POST 一次：业务侧瞬时码（如钉钉 errcode=-1）可能表示已送达，
        # 绝不能自动重试，否则图片/文本会重复进群。
        post_url = base_url
        post_payload = dict(payload)
        if platform == "dingtalk" and secret:
            post_url = self._dingtalk_sign_url(base_url, secret)
        if platform == "feishu" and secret:
            for k in ("timestamp", "sign"):
                post_payload.pop(k, None)
            post_payload = {**self._feishu_sign_fields(secret), **post_payload}

        async with build_async_client(proxy_url=proxy_url, timeout=timeout) as client:
            resp = await client.post(post_url, json=post_payload, headers=headers)

        self._raise_if_failed(resp, platform=platform)

        via = "代理" if proxy_url else "直连"
        logger.info(
            "Webhook 推送成功 user_uid=%s target=%s mode=%s via=%s status=%s",
            user_uid or "-",
            _PLATFORM_LABEL.get(platform, platform),
            mode,
            via,
            getattr(resp, "status_code", "-"),
        )