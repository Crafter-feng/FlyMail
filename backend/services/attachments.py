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
    """解析并校验路径是否属于当前用户的临时上传目录。

    仅用于：本机上传后的删除、仅临时目录场景。
    写信发送请用 resolve_compose_attachment_path（支持 NAS 授权目录）。
    """
    if not path:
        raise AppError(400, "附件路径不能为空")

    file_path = Path(path).resolve()
    user_dir = get_user_attachment_dir(user_uid).resolve()
    if not file_path.is_relative_to(user_dir):
        raise AppError(403, "无权访问该附件")
    return file_path


def is_temp_upload_path(user_uid: str, path: str) -> bool:
    """判断路径是否落在用户临时上传目录内（不要求文件已存在）。"""
    if not path:
        return False
    try:
        file_path = Path(path).resolve()
        user_dir = get_user_attachment_dir(user_uid).resolve()
        return file_path.is_relative_to(user_dir)
    except Exception:
        return False


def resolve_compose_attachment_path(user_uid: str, path: str) -> Path:
    """解析写信附件路径：允许用户临时目录，或飞牛 NAS 授权目录内的已有文件。

    NAS 路径直接引用，发送时按路径读盘；不复制到临时目录。
    """
    if not path:
        raise AppError(400, "附件路径不能为空")

    try:
        file_path = Path(path).resolve()
    except Exception:
        raise AppError(400, "非法附件路径")

    # 1) 用户临时上传目录
    user_dir = get_user_attachment_dir(user_uid).resolve()
    if file_path.is_relative_to(user_dir):
        if not file_path.exists() or not file_path.is_file():
            raise AppError(404, "附件文件不存在")
        return file_path

    # 2) 飞牛授权目录内的文件（NAS 直接引用）
    from utils.paths import is_path_authorized

    if not is_path_authorized(str(file_path)):
        raise AppError(403, "无权访问该附件路径（不在临时目录或授权目录内）")
    if not file_path.exists() or not file_path.is_file():
        raise AppError(404, "附件文件不存在")
    return file_path


def validate_attachment_paths(user_uid: str, paths: Iterable[str] | None) -> list[str]:
    """校验写信附件路径（临时上传 + NAS 授权），返回规范化绝对路径字符串。"""
    if not paths:
        return []

    safe_paths: list[str] = []
    for path in paths:
        file_path = resolve_compose_attachment_path(user_uid, path)
        safe_paths.append(str(file_path))
    return safe_paths


def unique_target_file(target_dir: Path, filename: str) -> Path:
    """在目标目录生成不冲突的文件路径；同名时追加 (1)、(2)..."""
    safe_name = sanitize_attachment_filename(filename)
    candidate = target_dir / safe_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        alt = target_dir / f"{stem} ({index}){suffix}"
        if not alt.exists():
            return alt
        index += 1
