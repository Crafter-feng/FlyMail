"""FastAPI 依赖注入模块

提取通用的请求处理逻辑，消除 API 端点中的重复代码。

主要依赖：
- get_uid(): 从飞牛OS网关请求头提取用户 ID
- get_accounts_by_uid(): 获取用户的所有账号
- get_account(): 获取指定账号（自动处理不存在的情况）
"""
from fastapi import Request, HTTPException, Path as FastAPIPath
from db import get_accounts
from models import Account
from utils.logger import get_logger

logger = get_logger("deps")


async def get_uid(request: Request) -> str:
    """从飞牛OS网关的 X-Trim-Userid 请求头提取用户 ID

    飞牛OS 统一网关会在转发请求时注入 X-Trim-Userid 头，
    标识当前登录的飞牛用户。本地开发时该头为空，使用 "default"。
    """
    return request.headers.get("X-Trim-Userid", "default")


async def get_accounts_by_uid(uid: str = None, request: Request = None) -> list[Account]:
    """获取指定用户的所有邮箱账号

    如果未传入 uid，从请求头自动提取。
    """
    if uid is None and request is not None:
        uid = request.headers.get("X-Trim-Userid", "default")
    return await get_accounts(uid or "default")


async def get_account(
    account_id: str = FastAPIPath(..., description="账号 ID"),
    uid: str = None,
    request: Request = None,
) -> Account:
    """获取指定的邮箱账号

    自动从请求头提取 uid，查找指定 ID 的账号。
    账号不存在时抛出 HTTPException 404。

    用法：
        @router.get("/api/accounts/{account_id}/folders")
        async def list_folders(account: Account = Depends(get_account)):
            ...
    """
    if uid is None:
        uid = await get_uid(request or Request)
    accounts = await get_accounts(uid)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        logger.warning("找不到账号 %s，可用账号: %s", account_id, [a.id for a in accounts])
        raise HTTPException(status_code=404, detail="账号不存在或已被删除")
    return account
