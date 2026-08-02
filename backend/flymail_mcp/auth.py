"""
FlyMail MCP TokenVerifier — validates Bearer tokens against user_settings.

Token storage format:
    user_settings: key="mcp_token", value="fm_mcp_<base64url>"

Token lifecycle:
    - Generated on first enable (auto) or via regenerate API
    - Stored in user_settings table per user_uid
    - Verified on every MCP SSE connection
    - Regenerate invalidates old token immediately
"""
import json
import os
import sys

_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from mcp.server.auth.provider import AccessToken, TokenVerifier
from db import get_db


class FlyMailTokenVerifier(TokenVerifier):
    """Validate Bearer token → AccessToken with user_uid as subject."""

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a Bearer token and return the corresponding user identity.

        Checks mcp_enabled flag first, then looks up the token in
        user_settings.  Returns None if MCP is disabled or token is invalid.

        NOTE: user_settings stores values as JSON-encoded strings, so we
        must query with json.dumps() to match the storage format.
        """
        db = await get_db()

        # 1. Check MCP is enabled (any user)
        # Note: values are JSON-encoded by set_user_setting, so "true" → '"true"'
        cursor = await db.execute(
            "SELECT 1 FROM user_settings WHERE key='mcp_enabled' AND value=? LIMIT 1",
            (json.dumps("true"),),
        )
        enabled = await cursor.fetchone()
        await cursor.close()
        if not enabled:
            return None

        # 2. Look up the token owner (values are JSON-encoded by set_user_setting)
        cursor = await db.execute(
            "SELECT user_uid FROM user_settings WHERE key='mcp_token' AND value=?",
            (json.dumps(token),),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if not row:
            return None

        return AccessToken(
            token=token,
            client_id="flymail",
            scopes=["email:read", "email:write"],
            subject=row[0],
        )