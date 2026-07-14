"""飞牛OS 授权路径管理模块

统一管理飞牛授权目录的读取和解析，供备份等功能复用。

数据源优先级：
1. 落盘文件 accessible_paths.env（由 cmd/config_callback 写入的最新值）
2. 环境变量 TRIM_DATA_ACCESSIBLE_PATHS（进程启动时的快照，兜底）

飞牛修改授权目录后会调用 config_callback 脚本，将新值写入文件。
Python 进程内 os.environ 是启动快照不会更新，所以飞牛环境
必须优先读文件才能拿到最新授权路径。
"""
import os
from pathlib import Path
from typing import List, Optional

from utils.logger import get_logger

logger = get_logger("paths")

# ==================== 飞牛环境变量 ====================
# TRIM_PKGVAR: 飞牛应用数据目录（数据库、日志、运行时配置）
# TRIM_DATA_ACCESSIBLE_PATHS: 飞牛授权的可访问路径列表（冒号分隔）
TRIM_PKGVAR = os.environ.get("TRIM_PKGVAR", "")

# ==================== 数据根目录 ====================
# 飞牛环境：TRIM_PKGVAR
# 本地开发：FLYMAIL_DATA_DIR 或 backend/data
DATA_DIR = Path(TRIM_PKGVAR) if TRIM_PKGVAR else Path(
    os.environ.get("FLYMAIL_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
)

# ==================== 飞牛授权路径落盘文件 ====================
# 由 flymail/cmd/config_callback 写入，供后端读取最新授权路径
# 本地开发时可手动创建 data/accessible_paths.env 模拟飞牛授权目录
ACCESSIBLE_PATHS_FILE = DATA_DIR / "accessible_paths.env"


def split_accessible_paths(raw: str) -> List[str]:
    """解析飞牛授权路径列表

    飞牛正式环境用冒号分隔多个 Linux 路径，例如：
        /vol1/media:/vol2/downloads

    本地 Windows 测试时，路径可能是：
        D:\\飞邮\\strm-test
    这里不能直接按冒号拆，否则会被错误拆成 "D" 和 "\\飞邮\\strm-test"。

    本地如需配置多个 Windows 路径，建议每行一个路径，或使用英文分号分隔。
    """
    if not raw:
        return []

    items: List[str] = []
    # 先按行拆，方便本地 accessible_paths.env 一行一个路径。
    for line in raw.replace("\r", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue

        # Windows 本地测试：D:\\xxx 或 D:/xxx 是单个路径，不能按冒号拆盘符。
        is_windows_drive_path = len(line) >= 3 and line[1] == ":" and line[2] in ("\\", "/")
        if is_windows_drive_path:
            parts = line.split(";") if ";" in line else [line]
        else:
            # 飞牛/Linux 正式环境：冒号分隔多个路径；本地也兼容分号。
            separator = ";" if ";" in line else ":"
            parts = line.split(separator)

        for part in parts:
            part = part.strip()
            if part:
                items.append(part)

    # 去重但保持顺序，避免前端重复显示。
    result: List[str] = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def get_accessible_paths() -> List[str]:
    """获取飞牛授权的可访问路径列表

    数据源优先级：
    1. 落盘文件 ACCESSIBLE_PATHS_FILE（config_callback 写入的最新值）
    2. 环境变量 TRIM_DATA_ACCESSIBLE_PATHS（进程启动时的快照，兜底）

    Returns:
        去重后的授权路径列表，无授权路径时返回空列表
    """
    # 优先读落盘文件（飞牛 config_callback 写入 / 本地开发模拟）
    if ACCESSIBLE_PATHS_FILE.exists():
        try:
            raw = ACCESSIBLE_PATHS_FILE.read_text(encoding="utf-8").strip()
            if raw:
                return split_accessible_paths(raw)
        except Exception as e:
            logger.warning("读取授权路径文件失败: %s", e)

    # 兜底：环境变量（进程启动时的快照）
    raw = os.environ.get("TRIM_DATA_ACCESSIBLE_PATHS", "")
    return split_accessible_paths(raw)


def is_path_authorized(path: str, accessible: Optional[List[str]] = None) -> bool:
    """校验给定路径是否位于某个授权目录下

    Args:
        path: 待校验路径
        accessible: 授权路径列表，为 None 时自动调用 get_accessible_paths()

    Returns:
        是否在授权范围内
    """
    if accessible is None:
        accessible = get_accessible_paths()
    if not accessible:
        return False

    try:
        target = Path(path).resolve()
    except Exception:
        return False

    for ap in accessible:
        try:
            base = Path(ap).resolve()
            # 检查 target 是否等于 base 或在 base 之下
            if target == base or base in target.parents:
                return True
        except Exception:
            continue
    return False
