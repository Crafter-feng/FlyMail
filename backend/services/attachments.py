"""Attachment upload path helpers.

All compose attachments must come from the current user's temporary upload
directory.  Keep the checks here so immediate sends, scheduled sends, and
delete operations enforce the same boundary.
"""
import os
import re
import uuid
from pathlib import Path
from typing import Iterable

from errors import AppError


# ==================== 附件大小限制 ====================
# 各邮箱平台 SMTP 服务器对邮件总大小有上限，Base64 编码会膨胀约 33%，
# 此处限制的是"附件原始大小总和"，已留安全余量避免临界值被服务器拒绝。
_PROVIDER_ATTACHMENT_LIMITS = {
    "gmail": 18 * 1024 * 1024,    # Gmail SMTP 25MB → 附件上限 ~18MB
    "qq": 35 * 1024 * 1024,       # QQ/企业邮箱 SMTP 50MB → 附件上限 ~35MB
    "netease": 35 * 1024 * 1024,  # 网易(163/126) SMTP 50MB → 附件上限 ~35MB
    "icloud": 15 * 1024 * 1024,   # iCloud SMTP 20MB → 附件上限 ~15MB
    "outlook": 15 * 1024 * 1024,  # Outlook SMTP 20MB → 附件上限 ~15MB
    "sina": 15 * 1024 * 1024,     # 新浪 SMTP 20MB → 附件上限 ~15MB
    "custom": 20 * 1024 * 1024,   # 自定义邮箱默认 20MB
}

# 默认限制（未知 provider 时使用）
_DEFAULT_ATTACHMENT_LIMIT = 15 * 1024 * 1024  # 15MB

# 单个文件上传的绝对上限（防止内存溢出，所有平台通用）
MAX_SINGLE_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_attachment_size_limit(provider: str) -> int:
    """获取指定邮箱平台的附件总大小限制（字节）"""
    return _PROVIDER_ATTACHMENT_LIMITS.get(provider, _DEFAULT_ATTACHMENT_LIMIT)


def check_attachment_total_size(attachment_paths: list[str], provider: str) -> None:
    """检查附件总大小是否超过平台限制，超过则抛出 AppError

    在发送邮件前调用，给用户明确的中文提示。
    """
    if not attachment_paths:
        return
    limit = get_attachment_size_limit(provider)
    total = sum(os.path.getsize(p) for p in attachment_paths)
    if total > limit:
        limit_mb = limit // (1024 * 1024)
        total_mb = total / (1024 * 1024)
        provider_name = {
            "gmail": "Gmail", "qq": "QQ邮箱", "netease": "网易邮箱",
            "icloud": "iCloud", "outlook": "Outlook", "sina": "新浪邮箱",
            "custom": "当前邮箱",
        }.get(provider, "当前邮箱")
        raise AppError(
            413,
            f"附件总大小 {total_mb:.1f}MB 超过{provider_name}限制（最大 {limit_mb}MB），"
            f"请减少附件数量或使用更小的文件"
        )


_DATA_DIR = os.environ.get(
    "FLYMAIL_DATA_DIR",
    os.path.join(os.path.dirname(__file__), "..", "data"),
)
ATTACHMENT_ROOT = Path(_DATA_DIR).resolve() / "attachments"


def _safe_user_segment(user_uid: str) -> str:
    """Turn a gateway uid into a single safe path segment."""
    value = re.sub(r"[^A-Za-z0-9_.-]", "_", user_uid or "default").strip("._")
    return value or "default"


def get_user_attachment_dir(user_uid: str) -> Path:
    return ATTACHMENT_ROOT / _safe_user_segment(user_uid)


def sanitize_attachment_filename(filename: str) -> str:
    """Keep only the client filename, accepting both Windows and POSIX paths."""
    safe_filename = os.path.basename((filename or "").replace("\\", "/"))
    if not safe_filename or safe_filename in (".", ".."):
        raise AppError(400, "非法文件名")
    return safe_filename


def build_upload_path(user_uid: str, filename: str) -> tuple[str, Path]:
    """Create a per-upload directory and return the sanitized target path."""
    safe_filename = sanitize_attachment_filename(filename)
    upload_dir = get_user_attachment_dir(user_uid) / uuid.uuid4().hex[:8]
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = (upload_dir / safe_filename).resolve()

    if not file_path.is_relative_to(upload_dir.resolve()):
        raise AppError(400, "非法文件路径")
    return safe_filename, file_path


def resolve_user_attachment_path(user_uid: str, path: str) -> Path:
    """Resolve and validate that a path belongs to the current user."""
    if not path:
        raise AppError(400, "附件路径不能为空")

    file_path = Path(path).resolve()
    user_dir = get_user_attachment_dir(user_uid).resolve()
    if not file_path.is_relative_to(user_dir):
        raise AppError(403, "无权访问该附件")
    return file_path


def validate_attachment_paths(user_uid: str, paths: Iterable[str] | None) -> list[str]:
    """Validate compose attachment paths and return canonical string paths."""
    if not paths:
        return []

    safe_paths: list[str] = []
    for path in paths:
        file_path = resolve_user_attachment_path(user_uid, path)
        if not file_path.exists() or not file_path.is_file():
            raise AppError(404, "附件文件不存在")
        safe_paths.append(str(file_path))
    return safe_paths
