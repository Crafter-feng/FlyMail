"""FastAPI 依赖注入模块

提取通用的请求处理逻辑，消除 API 端点中的重复代码。

主要依赖：
- get_uid(): 从飞牛OS网关请求头提取用户 ID
- get_accounts_by_uid(): 获取用户的所有账号
- get_account(): 获取指定账号（自动处理不存在的情况）

注意：get_account / get_accounts_by_uid 的 request 必须由 FastAPI
依赖注入为真实 Request 实例，不可把 Request 类当作默认值回退。
"""
from fastapi import Request, HTTPException, Path as FastAPIPath
from db import get_accounts, get_account_by_id
from models import Account
from utils.logger import get_logger

logger = get_logger("deps")


async def get_uid(request: Request) -> str:
    """从飞牛OS网关的 X-Trim-Userid 请求头提取用户 ID

    飞牛OS 统一网关会在转发请求时注入 X-Trim-Userid 头，
    标识当前登录的飞牛用户。本地开发时该头为空，使用 "default"。
    """
    return request.headers.get("X-Trim-Userid", "default")


async def get_accounts_by_uid(request: Request) -> list[Account]:
    """获取当前请求用户的所有邮箱账号。

    request 必须由 FastAPI Depends 注入为 Request 实例。
    """
    uid = await get_uid(request)
    return await get_accounts(uid)


async def get_account(
    request: Request,
    account_id: str = FastAPIPath(..., description="账号 ID"),
) -> Account:
    """获取指定的邮箱账号（当前用户范围内）。

    request 必须由 FastAPI 依赖注入为真实 Request 实例；
    不可用 Request 类做回退（类不是实例，会导致异常）。

    查找策略：
    1. 按主键 get_account_by_id（高效）
    2. 校验 account.user_uid 与请求用户一致（防越权）

    用法：
        @router.get("/api/accounts/{account_id}/folders")
        async def list_folders(account: Account = Depends(get_account)):
            ...
    """
    # 防御：极少数手动调用场景传入了非法对象
    if not isinstance(request, Request):
        logger.error("get_account 缺少有效 Request 依赖，type=%s", type(request))
        raise HTTPException(
            status_code=500,
            detail="内部错误：缺少请求上下文，请使用 Depends(get_account)",
        )

    uid = await get_uid(request)

    # 优先主键查询，避免加载该用户全部账号
    account = await get_account_by_id(account_id)
    if account is not None and account.user_uid == uid:
        return account

    # 主键命中但属其他用户 → 当作不存在（不泄露）
    if account is not None and account.user_uid != uid:
        logger.warning(
            "账号越权访问拒绝: account_id=%s 请求用户=%s 归属=%s",
            account_id, uid, account.user_uid,
        )
        raise HTTPException(status_code=404, detail="账号不存在或已被删除")

    # 主键未命中：再扫当前用户列表（兼容极端数据不一致）
    accounts = await get_accounts(uid)
    account = next((a for a in accounts if a.id == account_id), None)
    if not account:
        logger.warning("找不到账号 %s，可用账号: %s", account_id, [a.id for a in accounts])
        raise HTTPException(status_code=404, detail="账号不存在或已被删除")
    return account
