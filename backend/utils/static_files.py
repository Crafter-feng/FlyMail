"""前端静态资源路径解析（SPA 兜底用）

防止 `/{full_path:path}` 通过 `../` 或绝对路径读出 UI 目录外的文件。
"""
from pathlib import Path
from typing import Optional


def resolve_ui_file(ui_dir: Path, full_path: str) -> Optional[Path]:
    """将请求路径解析为 UI 目录内的安全文件路径。

    规则：
    1. 空路径 → None（由调用方回退 index.html）
    2. 绝对路径 / 含 ``..`` 段 / 空字节 → None
    3. resolve 后不在 ui_dir 内 → None
    4. 目标不是已存在的普通文件 → None
    5. 合法且存在 → 返回 resolve 后的 Path
    """
    if full_path is None:
        return None
    rel = str(full_path).strip().replace("\\", "/")
    # 去掉前导 /，避免部分平台把 "/etc/passwd" 当绝对路径拼接
    rel = rel.lstrip("/")
    if not rel or "\x00" in rel:
        return None
    try:
        candidate = Path(rel)
        if candidate.is_absolute():
            return None
        if ".." in candidate.parts:
            return None
        root = ui_dir.resolve()
        full = (root / candidate).resolve()
        if not full.is_relative_to(root):
            return None
        if full.is_file():
            return full
        return None
    except Exception:
        return None
