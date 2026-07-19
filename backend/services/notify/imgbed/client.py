# -*- coding: utf-8 -*-
"""Cloudflare 图床 HTTP 客户端。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from utils.logger import get_logger
from services.notify.http_client import build_async_client
from services.notify.imgbed.settings import imgbed_is_ready, normalize_imgbed

logger = get_logger("notify.imgbed")


class ImgbedError(RuntimeError):
    """图床操作失败。"""


class ImgbedConfigError(ImgbedError):
    """图床未配置或配置无效。"""


class ImgbedClient:
    """对用户自建 Worker 的封装。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = normalize_imgbed(config)
        self.base_url = str(self.config.get("base_url") or "").rstrip("/")
        self.token = str(self.config.get("upload_token") or "").strip()

    def ensure_ready(self) -> None:
        if not imgbed_is_ready(self.config):
            raise ImgbedConfigError(
                "图片推送需要配置自建图床：请在通知设置中填写图床地址与上传密钥。"
                "可点击「一键部署图床」到 Cloudflare。"
            )

    def _auth_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}"}
        if content_type:
            h["Content-Type"] = content_type
        return h

    async def health(self) -> Dict[str, Any]:
        """探活（无需鉴权）。"""
        self.ensure_ready()
        url = f"{self.base_url}/health"
        async with build_async_client(timeout=15.0) as client:
            resp = await client.get(url)
            text = (resp.text or "")[:300]
            if resp.status_code >= 400:
                raise ImgbedError(f"图床探活失败 HTTP {resp.status_code}: {text}")
            try:
                data = resp.json()
            except Exception as e:
                raise ImgbedError(f"图床探活返回非 JSON: {text}") from e
            if not data.get("ok", True):
                raise ImgbedError(f"图床探活异常: {data}")
            return data if isinstance(data, dict) else {"ok": True, "raw": data}

    async def upload_png(self, image_bytes: bytes, *, filename: str = "card.png") -> str:
        """上传 PNG，返回公开 URL。"""
        self.ensure_ready()
        if not image_bytes:
            raise ImgbedError("上传内容为空")
        url = f"{self.base_url}/upload"
        async with build_async_client(timeout=30.0) as client:
            resp = await client.post(
                url,
                content=image_bytes,
                headers=self._auth_headers("image/png"),
            )
            text = (resp.text or "")[:400]
            if resp.status_code >= 400:
                logger.warning(
                    "图床上传失败 status=%s body=%s",
                    resp.status_code,
                    text,
                )
                if resp.status_code == 401:
                    raise ImgbedError("图床鉴权失败：请检查上传密钥是否与 Cloudflare UPLOAD_TOKEN 一致")
                raise ImgbedError(f"图床上传失败 HTTP {resp.status_code}: {text}")
            try:
                data = resp.json()
            except Exception as e:
                raise ImgbedError(f"图床上传返回非 JSON: {text}") from e
            public = str((data or {}).get("url") or "").strip()
            if not public:
                raise ImgbedError(f"图床上传未返回 url: {data}")
            logger.info("图床上传成功 key=%s", (data or {}).get("key") or "-")
            return public

    async def purge(self) -> int:
        """清理全部图片，返回删除数量。"""
        self.ensure_ready()
        url = f"{self.base_url}/purge"
        async with build_async_client(timeout=60.0) as client:
            resp = await client.post(url, headers=self._auth_headers())
            text = (resp.text or "")[:400]
            if resp.status_code >= 400:
                if resp.status_code == 401:
                    raise ImgbedError("图床鉴权失败：请检查上传密钥")
                raise ImgbedError(f"图床清理失败 HTTP {resp.status_code}: {text}")
            try:
                data = resp.json()
            except Exception as e:
                raise ImgbedError(f"图床清理返回非 JSON: {text}") from e
            deleted = int((data or {}).get("deleted") or 0)
            logger.info("图床清理完成 deleted=%s", deleted)
            return deleted


def get_imgbed_client(config: Dict[str, Any] | None) -> ImgbedClient:
    return ImgbedClient(config or {})
