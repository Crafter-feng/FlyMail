"""
FlyMail MCP Server — MCPServer instance with tool and resource registration.

Mounted as a FastAPI sub-app at /mcp in main.py.  All tools authenticate
via Bearer token (FlyMailTokenVerifier) and get the user identity from
get_access_token().

Usage (standalone):
    python -m backend.flymail_mcp.server                    # SSE on :9000
    python -m backend.flymail_mcp.server --port 9001
    python -m backend.flymail_mcp.server --transport stdio
"""
import argparse
import asyncio
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from mcp.server.mcpserver import MCPServer
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.middleware.auth_context import get_access_token
from db import (
    get_accounts,
    get_account_by_id,
    get_cached_messages_by_folder,
    get_cached_message_detail,
    get_unified_inbox_messages,
    get_folder_stats,
    get_contacts,
    get_contact_by_id,
    get_notifications,
    get_user_settings,
    get_db,
    init_db,
)
from flymail_mcp.auth import FlyMailTokenVerifier
from version import VERSION


# ── MCP Server (with auth) ─────────────────────────────────────────────

server = MCPServer(
    name="FlyMail",
    title="FlyMail MCP Server",
    description="FlyMail (飞邮) MCP Server — self-hosted email client. "
                "Search/read cached emails, browse accounts and contacts, "
                "check unread counts and notifications.",
    version=VERSION,
    instructions=(
        "This MCP server provides access to FlyMail's email system. "
        "Use flymail_search_emails to find emails by keyword, "
        "flymail_get_email to read full email content, "
        "flymail_list_accounts to see all configured email accounts, "
        "and flymail_get_unread_counts to check unread mail."
    ),
    token_verifier=FlyMailTokenVerifier(),
    auth=AuthSettings(
        issuer_url="http://localhost:8080",
        resource_server_url=None,
    ),
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _get_uid() -> str:
    """Get the current user_uid from the authenticated connection.

    Called inside tool handlers.  Falls back to "default" when no
    auth context is available (e.g. during testing or standalone).
    """
    token = get_access_token()
    return token.subject if token and token.subject else "default"


def _format_message(msg: dict) -> dict:
    return {
        "id": msg.get("id", ""),
        "account_id": msg.get("account_id", ""),
        "uid": msg.get("uid", 0),
        "folder": msg.get("folder", ""),
        "subject": msg.get("subject", ""),
        "from_addr": msg.get("from_addr", ""),
        "to_addr": msg.get("to_addr", ""),
        "cc": msg.get("cc", ""),
        "date": msg.get("date", ""),
        "is_read": msg.get("is_read", False),
        "is_starred": msg.get("is_starred", False),
        "has_attachments": msg.get("has_attachments", False),
        "body_text": (msg.get("body_text") or "")[:5000],
        "body_html": (msg.get("body_html") or "")[:5000] if msg.get("body_html") else "",
        "message_id": msg.get("message_id", ""),
        "cached_at": msg.get("cached_at", 0),
    }


def _format_account(account) -> dict:
    return {
        "id": account.id,
        "email": account.email,
        "provider": account.provider,
        "status": account.status,
        "remark": account.remark or "",
        "group_name": account.group_name or "",
        "hide_email": account.hide_email,
        "sort_order": account.sort_order,
        "created_at": account.created_at,
    }


def _format_contact(contact: dict) -> dict:
    return {
        "id": contact.get("id", 0),
        "name": contact.get("name", ""),
        "emails": contact.get("emails", []),
        "phone": contact.get("phone", ""),
        "company": contact.get("company", ""),
        "remark": contact.get("remark", ""),
        "group_name": contact.get("group_name", ""),
        "created_at": contact.get("created_at", 0),
        "updated_at": contact.get("updated_at", 0),
    }


def _format_notification(notification) -> dict:
    return {
        "id": notification.id,
        "type": notification.type,
        "title": notification.title,
        "content": (notification.content or "")[:200],
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "account_id": notification.account_id or "",
        "batch_count": notification.batch_count or 1,
    }


# ── Email Tools ─────────────────────────────────────────────────────────

@server.tool(
    name="flymail_search_emails",
    description="Search cached emails by keyword across subject, sender, recipient, and body. "
                "Supports filtering by account and folder.",
)
async def search_emails(
    query: str,
    account_id: str | None = None,
    folder: str = "INBOX",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    """Search cached emails by keyword.

    Args:
        query: Search keyword (matches subject, from, to, cc, body)
        account_id: Optional account ID. Omit for all-account search.
        folder: Folder path (default: INBOX)
        limit: Max results (default: 20, max: 100)
        offset: Pagination offset
    """
    uid = _get_uid()
    limit = min(limit, 100)

    if account_id:
        result = await get_cached_messages_by_folder(
            user_uid=uid, account_id=account_id, folder=folder,
            limit=limit, offset=offset, search_query=query,
        )
    else:
        accounts = await get_accounts(uid)
        ids = [a.id for a in accounts]
        if not ids:
            return []
        result = await get_unified_inbox_messages(
            user_uid=uid, account_ids=ids,
            limit=limit, offset=offset, search_query=query,
        )
    return [_format_message(m) for m in result.get("messages", [])]


@server.tool(
    name="flymail_get_email",
    description="Get the full detail of a single cached email, including body text and HTML.",
)
async def get_email(
    account_id: str,
    uid: int,
    folder: str = "INBOX",
) -> dict | None:
    """Get full email detail.

    Args:
        account_id: The email account ID
        uid: IMAP UID of the message
        folder: Folder path (default: INBOX)
    """
    msg = await get_cached_message_detail(account_id, uid, folder)
    return _format_message(msg) if msg else None


@server.tool(
    name="flymail_get_recent_emails",
    description="Get the most recent N emails from a specific account+folder, "
                "or from the unified inbox across all accounts.",
)
async def get_recent_emails(
    account_id: str | None = None,
    folder: str = "INBOX",
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """Get recent emails.

    Args:
        account_id: Optional account ID. Omit for unified inbox.
        folder: Folder path (default: INBOX)
        limit: Number of emails (default: 10, max: 50)
        offset: Pagination offset
    """
    uid = _get_uid()
    limit = min(limit, 50)

    if account_id:
        result = await get_cached_messages_by_folder(
            user_uid=uid, account_id=account_id, folder=folder,
            limit=limit, offset=offset,
        )
    else:
        accounts = await get_accounts(uid)
        ids = [a.id for a in accounts]
        if not ids:
            return []
        result = await get_unified_inbox_messages(
            user_uid=uid, account_ids=ids, limit=limit, offset=offset,
        )
    return [_format_message(m) for m in result.get("messages", [])]


@server.tool(
    name="flymail_get_unread_counts",
    description="Get unread email counts per account. "
                "Returns a summary of unread emails across all accounts.",
)
async def get_unread_counts() -> list[dict]:
    """Get unread email counts for all accounts."""
    uid = _get_uid()
    accounts = await get_accounts(uid)
    results = []
    for a in accounts:
        stats = await get_folder_stats(a.id, "INBOX")
        results.append({
            "account_id": a.id, "email": a.email, "provider": a.provider,
            "total_count": stats.get("total_count", 0),
            "unread_count": stats.get("unread_count", 0),
        })
    return results


@server.tool(
    name="flymail_list_folders",
    description="List all folders for a specific email account with message counts.",
)
async def list_folders(account_id: str) -> list[dict]:
    """List folders for an email account.

    Args:
        account_id: The email account ID
    """
    db = await get_db()
    cursor = await db.execute(
        "SELECT folder, total_count, unread_count FROM folder_stats "
        "WHERE account_id = ? ORDER BY folder", (account_id,),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [
        {"folder": r[0], "total_count": r[1], "unread_count": r[2]}
        for r in rows
    ]


# ── Account Tools ───────────────────────────────────────────────────────

@server.tool(
    name="flymail_list_accounts",
    description="List all configured email accounts with their provider, status, and metadata.",
)
async def list_accounts() -> list[dict]:
    """List all email accounts."""
    accounts = await get_accounts(_get_uid())
    return [_format_account(a) for a in accounts]


@server.tool(
    name="flymail_get_account",
    description="Get detailed information about a specific email account.",
)
async def get_account(account_id: str) -> dict | None:
    """Get a single email account by ID.

    Args:
        account_id: The email account ID
    """
    account = await get_account_by_id(account_id)
    if not account or account.user_uid != _get_uid():
        return None
    return _format_account(account)


# ── Contact Tools ───────────────────────────────────────────────────────

@server.tool(
    name="flymail_search_contacts",
    description="Search contacts by name or email address. Returns matching contacts with all their email addresses.",
)
async def search_contacts(query: str, limit: int = 10) -> list[dict]:
    """Search contacts by name or email.

    Args:
        query: Name or email to search for
        limit: Max results (default: 10, max: 50)
    """
    limit = min(limit, 50)
    contacts = await get_contacts(_get_uid(), search=query)
    return [_format_contact(c) for c in contacts[:limit]]


@server.tool(
    name="flymail_get_contact",
    description="Get full details of a single contact, including all associated email addresses.",
)
async def get_contact(contact_id: int) -> dict | None:
    """Get a single contact by ID.

    Args:
        contact_id: The contact ID
    """
    contact = await get_contact_by_id(contact_id, _get_uid())
    return _format_contact(contact) if contact else None


# ── Notification Tools ─────────────────────────────────────────────────

@server.tool(
    name="flymail_list_notifications",
    description="List recent notifications (new email alerts, send results, etc.). "
                "Sorted newest-first.",
)
async def list_notifications(limit: int = 20) -> list[dict]:
    """List recent notifications.

    Args:
        limit: Number of notifications (default: 20, max: 100)
    """
    limit = min(limit, 100)
    notifications = await get_notifications(_get_uid(), limit=limit)
    return [_format_notification(n) for n in notifications]


# ── System Tools ────────────────────────────────────────────────────────

@server.tool(
    name="flymail_get_health",
    description="Check if the FlyMail MCP server is running and healthy. "
                "Returns version, account count, and database status.",
)
async def get_health() -> dict:
    """Health check."""
    try:
        db = await get_db()
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
        await cursor.close()
        accounts = await get_accounts(_get_uid())
        return {
            "status": "ok", "app": "flymail", "version": VERSION,
            "account_count": len(accounts), "database": "connected",
        }
    except Exception as e:
        return {
            "status": "error", "app": "flymail", "version": VERSION,
            "error": str(e), "database": "disconnected",
        }


@server.tool(
    name="flymail_get_settings",
    description="Get FlyMail application settings (proxy config, etc.).",
)
async def get_settings() -> dict:
    """Get application settings."""
    settings = await get_user_settings(_get_uid(), keys=["gmail_proxy_enabled", "gmail_proxy_url"])
    return {
        "gmail_proxy_enabled": settings.get("gmail_proxy_enabled", False),
        "gmail_proxy_url": settings.get("gmail_proxy_url", ""),
    }


@server.tool(
    name="flymail_get_summary",
    description="Get a high-level summary of the FlyMail setup: "
                "number of accounts, total cached emails, unread count, and recent activity.",
)
async def get_summary() -> dict:
    """Get a summary of the FlyMail setup."""
    uid = _get_uid()
    accounts = await get_accounts(uid)

    total_unread = 0
    total_cached = 0
    account_summaries = []
    for a in accounts:
        stats = await get_folder_stats(a.id, "INBOX")
        total_unread += stats.get("unread_count", 0)
        total_cached += stats.get("total_count", 0)
        account_summaries.append({
            "id": a.id, "email": a.email, "provider": a.provider,
            "status": a.status, "unread": stats.get("unread_count", 0),
            "total": stats.get("total_count", 0),
        })

    notifs = await get_notifications(uid, limit=1)
    return {
        "account_count": len(accounts),
        "total_cached_emails": total_cached,
        "total_unread": total_unread,
        "last_notification_at": notifs[0].created_at if notifs else 0,
        "accounts": account_summaries,
    }


# ── Resources ───────────────────────────────────────────────────────────

@server.resource(
    uri="flymail://accounts",
    name="All Email Accounts",
    description="List of all configured email accounts.",
    mime_type="application/json",
)
async def accounts_resource() -> list[dict]:
    accounts = await get_accounts(_get_uid())
    return [_format_account(a) for a in accounts]


@server.resource(
    uri="flymail://accounts/{account_id}",
    name="Single Email Account",
    description="Details of a specific email account.",
    mime_type="application/json",
)
async def account_resource(account_id: str) -> dict | None:
    account = await get_account_by_id(account_id)
    if not account:
        return None
    return _format_account(account)


@server.resource(
    uri="flymail://emails/{account_id}/{folder}",
    name="Folder Email List",
    description="List of cached emails in a folder (newest first, max 20).",
    mime_type="application/json",
)
async def folder_emails_resource(account_id: str, folder: str = "INBOX") -> list[dict]:
    result = await get_cached_messages_by_folder(
        user_uid=_get_uid(), account_id=account_id, folder=folder, limit=20, offset=0,
    )
    return [_format_message(m) for m in result.get("messages", [])]


@server.resource(
    uri="flymail://emails/{account_id}/{folder}/{uid}",
    name="Single Email Detail",
    description="Full detail of a single cached email including body.",
    mime_type="application/json",
)
async def email_detail_resource(account_id: str, folder: str, uid: int) -> dict | None:
    msg = await get_cached_message_detail(account_id, uid, folder)
    return _format_message(msg) if msg else None


@server.resource(
    uri="flymail://contacts",
    name="All Contacts",
    description="List of all contacts with their email addresses.",
    mime_type="application/json",
)
async def contacts_resource() -> list[dict]:
    contacts = await get_contacts(_get_uid())
    return [_format_contact(c) for c in contacts]


@server.resource(
    uri="flymail://notifications",
    name="Recent Notifications",
    description="Recent notifications, newest first.",
    mime_type="application/json",
)
async def notifications_resource() -> list[dict]:
    notifications = await get_notifications(_get_uid(), limit=20)
    return [_format_notification(n) for n in notifications]


@server.resource(
    uri="flymail://health",
    name="Health Status",
    description="Server health — status, version, database connectivity.",
    mime_type="application/json",
)
async def health_resource() -> dict:
    try:
        db = await get_db()
        cursor = await db.execute("SELECT 1")
        await cursor.fetchone()
        await cursor.close()
        accounts = await get_accounts(_get_uid())
        return {
            "status": "ok", "app": "flymail", "version": VERSION,
            "account_count": len(accounts), "database": "connected",
        }
    except Exception as e:
        return {
            "status": "error", "app": "flymail", "version": VERSION,
            "error": str(e), "database": "disconnected",
        }


# ── CLI Entry Point ─────────────────────────────────────────────────────

def main():
    """Run the MCP server via CLI."""
    parser = argparse.ArgumentParser(description="FlyMail MCP Server")
    parser.add_argument("--port", type=int, default=9000, help="Port (default: 9000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--transport", type=str, default="sse", choices=["sse", "stdio"],
                        help="Transport (default: sse)")
    args = parser.parse_args()

    if "FLYMAIL_DATA_DIR" not in os.environ:
        os.environ["FLYMAIL_DATA_DIR"] = os.path.join(
            os.path.dirname(_backend_dir), "data",
        )
        os.makedirs(os.environ["FLYMAIL_DATA_DIR"], exist_ok=True)

    asyncio.run(init_db())

    print(f"FlyMail MCP Server v{VERSION}  transport={args.transport}")
    if args.transport == "sse":
        print(f"  SSE: http://{args.host}:{args.port}/sse")
        print(f"  POST: http://{args.host}:{args.port}/messages/")
        asyncio.run(server.run_sse_async(host=args.host, port=args.port))
    else:
        print("  stdio mode")
        asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()