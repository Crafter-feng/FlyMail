"""邮件备份路由

提供备份配置管理、手动触发备份、归档邮件查询等 API。
所有配置存储在 user_settings 表中，按用户隔离。
"""
import asyncio
from fastapi import APIRouter, Request, Query, Body

from db import (
    get_user_setting,
    set_user_settings,
    get_archived_messages,
    get_archived_message_by_uid,
    get_archive_stats,
    get_archive_folders,
    get_accounts,
)
from deps import get_uid
from services.backup import (
    get_backup_root_async,
    archive_all_accounts,
    archive_single_account,
    get_available_backup_dirs,
    parse_eml_to_message,
    resolve_eml_under_backup_root,
)
from utils.logger import get_logger
from utils.tasks import create_background_task

logger = get_logger("routes.backup")
router = APIRouter(tags=["备份"])


# ==================== 备份配置 ====================

@router.get("/api/backup/settings", summary="获取备份配置")
async def get_backup_settings(request: Request):
    """获取备份配置：总开关、选中邮箱列表、备份目录、可用授权目录"""
    uid = await get_uid(request)

    # 读用户配置
    enabled = await get_user_setting(uid, "backup_enabled", False)
    account_ids = await get_user_setting(uid, "backup_account_ids", [])
    target_dir = await get_user_setting(uid, "backup_target_dir", "")

    # 获取账号列表（供前端选择）
    accounts = await get_accounts(uid)

    # 获取可用备份目录（飞牛OS 授权目录）
    available_dirs = await get_available_backup_dirs(uid)

    return {
        "enabled": enabled,
        "account_ids": account_ids,
        "target_dir": target_dir,
        "available_dirs": available_dirs,
        "accounts": [
            {
                "id": a.id,
                "email": a.email,
                "provider": a.provider,
                "selected": a.id in account_ids,
            }
            for a in accounts
        ],
    }


@router.put("/api/backup/settings", summary="保存备份配置")
async def save_backup_settings(request: Request, body: dict = Body(...)):
    """保存备份配置

    使用 set_user_settings（复数）批量写入 user_settings 表。
    保存前校验 target_dir 必须在飞牛授权目录内，避免用户设置非法路径。
    """
    uid = await get_uid(request)

    target_dir = body.get("target_dir", "")
    # 校验备份目录必须在飞牛授权目录内（空字符串允许保存，归档时降级到飞牛授权目录）
    if target_dir:
        from utils.paths import is_path_authorized
        if not is_path_authorized(target_dir):
            return {"success": False, "message": "备份位置必须在飞牛OS 授权目录内"}

    settings = {
        "backup_enabled": bool(body.get("enabled", False)),
        "backup_account_ids": body.get("account_ids", []),
        "backup_target_dir": target_dir,
    }
    await set_user_settings(uid, settings)

    return {"success": True, "message": "备份设置已保存"}


# ==================== 授权目录浏览 ====================

@router.get("/api/backup/accessible-paths", summary="获取飞牛授权目录列表")
async def get_accessible_paths_api():
    """获取飞牛授权的可访问路径列表

    数据源：accessible_paths.env 落盘文件（config_callback 写入）→ 环境变量兜底。
    前端目录选择器初始显示该列表，用户逐级浏览选择备份目标目录。
    """
    from utils.paths import get_accessible_paths
    paths = await asyncio.to_thread(get_accessible_paths)
    return {"paths": paths}


@router.get("/api/backup/accessible-paths/children", summary="列出授权目录下的子目录/文件")
async def list_accessible_children_api(
    path: str = Query(default="", description="要列出的目录路径，为空时返回所有授权目录"),
    include_files: bool = Query(default=False, description="是否同时列出文件（写信从 NAS 选附件时为 true）"),
):
    """列出指定授权目录下的子目录（一层）；可选同时列文件。

    前端选择备份存储路径时，先选授权目录，再逐级浏览子目录，
    最终路径 = 授权目录 + 选中的子目录路径。
    附件 NAS 通道：include_files=true 时额外返回 files。

    Args:
        path: 要列出的目录路径，为空时返回所有授权目录
        include_files: 是否列出文件
    """
    from pathlib import Path
    from utils.paths import get_accessible_paths, is_path_authorized

    # path 为空：返回所有授权目录
    if not path:
        paths = await asyncio.to_thread(get_accessible_paths)
        return {"dirs": paths, "files": []}

    # 校验 path 在授权范围内
    accessible = await asyncio.to_thread(get_accessible_paths)
    if not is_path_authorized(path, accessible):
        logger.warning("路径不在授权范围内: path=%s", path)
        return {"dirs": [], "files": [], "error": "路径不在授权范围内"}

    # 列出子目录（仅一层）；可选列文件
    def _list_children(p: str, with_files: bool):
        dirs = []
        files = []
        try:
            for entry in sorted(Path(p).iterdir(), key=lambda x: x.name.lower()):
                path_str = str(entry)
                # 跳过包含代理对的路径（非 UTF-8 文件名），避免 JSON 序列化失败
                try:
                    path_str.encode("utf-8")
                except UnicodeEncodeError:
                    continue
                if entry.is_dir():
                    dirs.append(path_str)
                elif with_files and entry.is_file():
                    try:
                        size = entry.stat().st_size
                    except OSError:
                        size = 0
                    files.append({
                        "name": entry.name,
                        "path": path_str,
                        "size": size,
                    })
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.warning("列出子目录失败: path=%s, error=%s", p, e)
        return dirs, files

    dirs, files = await asyncio.to_thread(_list_children, path, include_files)
    return {"dirs": dirs, "files": files}

@router.post("/api/backup/run", summary="手动触发备份")
async def trigger_backup(
    request: Request,
    account_id: str = Query(default="", description="指定账号备份，为空则备份所有选中邮箱"),
):
    """手动触发备份（后台执行，不阻塞 API）

    传入 account_id 时只备份该账号，为空时备份所有选中邮箱。
    手动触发会发送备份结果通知（notify=True）。
    """
    uid = await get_uid(request)
    enabled = await get_user_setting(uid, "backup_enabled", False)
    if not enabled:
        return {"success": False, "message": "备份功能未开启"}

    # 检查授权目录是否存在（无授权目录时直接拒绝，避免后台任务失败）
    backup_root = await get_backup_root_async(uid)
    if backup_root is None:
        return {"success": False, "message": "无飞牛授权目录，请先在飞牛应用设置中授权目录"}

    if account_id:
        # 仅备份指定账号
        create_background_task(
            archive_single_account(uid, account_id, notify=True),
            name=f"backup_single_{uid}_{account_id}"
        )
    else:
        # 备份所有选中邮箱
        create_background_task(
            archive_all_accounts(uid, notify=True),
            name=f"backup_all_{uid}"
        )

    return {"success": True, "message": "备份任务已启动"}


@router.get("/api/backup/status", summary="获取备份状态")
async def get_backup_status(request: Request):
    """获取备份统计：总数量、各邮箱归档数量、最后归档时间、已删除数量

    账号列表来自用户设置的 backup_account_ids（即使没有归档记录也显示），
    这样新增备份邮箱后能立即在备份页面看到，空状态提示点击立即备份。
    """
    uid = await get_uid(request)
    stats = await get_archive_stats(uid)

    # 合并用户设置的备份邮箱列表（以设置为准，归档统计补充）
    account_ids = await get_user_setting(uid, "backup_account_ids", [])
    if account_ids:
        all_accounts = await get_accounts(uid)
        stats_map = {a["account_id"]: a for a in stats.get("accounts", [])}
        accounts = []
        for acc in all_accounts:
            if acc.id in account_ids:
                s = stats_map.get(acc.id, {})
                accounts.append({
                    "account_id": acc.id,
                    "email": acc.email,
                    "provider": acc.provider,
                    "count": s.get("count", 0),
                    "deleted_count": s.get("deleted_count", 0),
                    "last_archived": s.get("last_archived", 0),
                })
        stats["accounts"] = accounts

    return stats


@router.get("/api/backup/folders", summary="获取归档文件夹列表")
async def list_archive_folders(
    request: Request,
    account_id: str = Query(default="", description="筛选账号，为空则返回所有账号文件夹汇总"),
):
    """获取归档邮件的文件夹列表（按文件夹分组统计），供前端左侧文件夹列表展示"""
    uid = await get_uid(request)
    folders = await get_archive_folders(uid, account_id)
    return {"folders": folders}


# ==================== 归档邮件查询 ====================

@router.get("/api/backup/messages", summary="获取归档邮件列表")
async def list_archived_messages(
    request: Request,
    account_id: str = Query(default="", description="筛选账号"),
    folder: str = Query(default="", description="筛选文件夹"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=40, ge=1, le=100),
    deleted_filter: str = Query(
        default="",
        description="删除筛选：deleted=仅已删除, alive=仅存活, 空=全部",
    ),
):
    """分页查询归档邮件列表（按 date 倒序）"""
    uid = await get_uid(request)
    result = await get_archived_messages(
        uid,
        account_id=account_id,
        folder=folder,
        page=page,
        page_size=page_size,
        deleted_filter=deleted_filter,
    )
    return result


@router.get(
    "/api/backup/messages/{account_id}/{folder}/{uid}",
    summary="获取归档邮件详情",
)
async def get_archived_detail(
    request: Request,
    account_id: str,
    folder: str,
    uid: int,
):
    """读取 .eml 文件并解析为邮件详情（不连接 IMAP）

    从本地 .eml 文件读取完整邮件内容，解析为前端可展示的格式。
    如果邮件已在服务器删除，返回的 is_deleted_on_server=1。
    """
    user_uid = await get_uid(request)

    # 查归档记录（含 user_uid 归属校验，避免越权访问）
    archive = await get_archived_message_by_uid(user_uid, account_id, folder, uid)
    if not archive:
        return {"error": "归档记录不存在"}

    # 读取 .eml 文件（无授权目录时无法读取，提示用户先授权）
    # 相对路径必须经 resolve_eml_under_backup_root，防止路径穿越读出备份根外文件
    backup_root = await get_backup_root_async(user_uid)
    if backup_root is None:
        return {"error": "无飞牛授权目录，无法读取备份文件"}
    eml_path = resolve_eml_under_backup_root(backup_root, archive.get("eml_path"))
    if eml_path is None or not eml_path.exists():
        return {"error": ".eml 文件不存在"}

    # 解析 .eml（复用 base_imap 的解析逻辑）
    raw_bytes = eml_path.read_bytes()
    message = parse_eml_to_message(raw_bytes, archive)
    return message
