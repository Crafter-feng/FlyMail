"""
FlyMail MCP (Model Context Protocol) Server

Exposes FlyMail's email, account, contact, and notification functionality
as MCP tools and resources for AI assistants.

Usage:
    python -m backend.flymail_mcp.server                    # SSE on port 9000
    python -m backend.flymail_mcp.server --port 9001         # custom port
    python -m backend.flymail_mcp.server --transport stdio   # stdio mode
    python -m backend.flymail_mcp.server --help              # full help

Environment:
    FLYMAIL_DATA_DIR    Path to FlyMail data directory (default: ./data)
    FLYMAIL_MCP_PORT    Enable MCP server in-process (set to port number)
"""