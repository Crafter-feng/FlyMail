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
