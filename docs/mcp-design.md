# FlyMail MCP Server 设计方案

## 1. 概述

为 FlyMail（飞邮）增加 MCP (Model Context Protocol) Server 支持，让 AI 助手（Claude Desktop 等）通过 MCP 协议直接读取邮件、搜索联系人、查看通知等。

MCP Server 以 **FastAPI 子应用** 形式挂载在主服务中，**同进程、同端口**，无需额外部署。

## 2. 架构

```
┌──────────────────────────────────────────────────────────────┐
│  FastAPI 主应用 (:8080)                                       │
│                                                               │
│  ┌──────────────────────┐   ┌────────────────────────────┐   │
│  │  API Routes          │   │  MCP Server (子应用)        │   │
│  │  /api/*              │   │  /mcp/sse                  │   │
│  │  /api/settings/mcp   │   │  /mcp/messages/            │   │
│  │  ...                 │   │                             │   │
│  └──────────┬───────────┘   │  BearerAuthBackend         │   │
│             │               │  AuthContextMiddleware     │   │
│             │               │  RequireAuthMiddleware     │   │
│             │               │                             │   │
│             │               │  @tool  → db/services 调用  │   │
│             │               └────────────┬────────────────┘   │
│             │                            │                    │
│             └──────────┬─────────────────┘                    │
│                        ▼                                      │
│             ┌────────────────────┐                            │
│             │  Services Layer    │                            │
│             │  sync.py, backup   │                            │
│             └────────┬───────────┘                            │
│                      ▼                                        │
│             ┌────────────────────┐                            │
│             │  db (SQLite WAL)   │                            │
│             └────────────────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

### 2.1 子应用挂载

```python
# main.py
from flymail_mcp.server import mcp_server
from flymail_mcp.auth import FlyMailTokenVerifier

# 启动时创建并挂载一次
_mcp_starlette_app = mcp_server.sse_app(
    sse_path="/sse",
    message_path="/messages/",
)
app.mount("/mcp", _mcp_starlette_app)
```

- 同一进程、同一端口 (8080)
- 无需额外端口管理
- 共享主应用的生命周期

### 2.2 通信协议

| 协议 | 路径 | 说明 |
|------|------|------|
| SSE | `GET /mcp/sse` | 建立 SSE 连接，接收服务端推送 |
| POST | `POST /mcp/messages/` | 发送 JSON-RPC 请求 |
| Auth | `Authorization: Bearer <token>` | 所有请求需携带 Bearer Token |

## 3. 认证机制

### 3.1 认证链

```
MCP Client                          FastAPI (:8080) / MCP Sub-app
   │                                        │
   │ GET /mcp/sse                           │
   │ Authorization: Bearer fm_mcp_xxx       │
   │────────────────────────────────────────>│
   │                                        │
   │  ┌─ 1. BearerAuthBackend               │
   │  │    ├─ 提取 Bearer token             │
   │  │    ├─ verify_token(token)           │
   │  │    │    ↓                           │
   │  │    │ 查 user_settings 表            │
   │  │    │ WHERE key='mcp_token'           │
   │  │    │   AND value=token              │
   │  │    │    ↓                           │
   │  │    │ 返回 AccessToken(              │
   │  │    │   subject=user_uid,            │
   │  │    │   client_id="flymail",         │
   │  │    │   scopes=["email:read"]        │
   │  │    │ )                              │
   │  │    └─ scope["user"] = AuthUser      │
   │  │                                     │
   │  ├─ 2. AuthContextMiddleware            │
   │  │    └─ auth_context_var.set(user)    │
   │  │                                     │
   │  ├─ 3. RequireAuthMiddleware            │
   │  │    └─ scope["user"] 不存在 → 401    │
   │  │                                     │
   │  └─ 4. handle_sse → 低层 Server 运行   │
   │                                        │
   │<──── SSE 连接建立 ──────────────────────│
   │                                        │
   │ POST /mcp/messages/ (JSON-RPC)         │
   │────────────────────────────────────────>│
   │                                        │
   │  ┌─ 5. 工具 handler 内                  │
   │  │    get_access_token().subject        │
   │  │    → 获得 user_uid                  │
   │  │    → 传入 db 函数实现数据隔离        │
   │  │                                     │
   │<──── SSE event: 工具结果 ───────────────│
```

### 3.2 TokenVerifier 实现

```python
# flymail_mcp/auth.py
from mcp.server.auth.provider import AccessToken, TokenVerifier

class FlyMailTokenVerifier(TokenVerifier):
    """验证 Bearer token → 返回用户身份"""

    async def verify_token(self, token: str) -> AccessToken | None:
        # 1. 检查 MCP 是否启用
        enabled = await get_user_setting("default", "mcp_enabled")
        if enabled != "true":
            return None

        # 2. 查找 token 所属用户
        uid = await get_user_uid_by_mcp_token(token)
        if not uid:
            return None

        # 3. 返回身份信息
        return AccessToken(
            token=token,
            client_id="flymail",
            scopes=["email:read"],
            subject=uid,          # 用户标识，工具内通过 get_access_token().subject 获取
        )
```

### 3.3 Token 存储与查询

```python
# db/__init__.py 新增
async def get_user_uid_by_mcp_token(token: str) -> str | None:
    """通过 MCP token 查找用户 ID"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT user_uid FROM user_settings WHERE key='mcp_token' AND value=?",
        (token,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row[0] if row else None
```

### 3.4 工具 handler 中获取用户身份

```python
from mcp.server.auth.middleware.auth_context import get_access_token

@server.tool(name="flymail_search_emails")
async def search_emails(query: str, limit: int = 20) -> list[dict]:
    token = get_access_token()
    if token is None:
        raise ValueError("Authentication required")

    user_uid = token.subject or "default"

    # 用 user_uid 查询，天然用户隔离
    result = await get_cached_messages_by_folder(user_uid=user_uid, ...)
    return result
```

### 3.5 禁用 MCP 时的行为

用户关闭 MCP 开关后：
1. `mcp_enabled` 设为 `false`
2. `verify_token()` 返回 `None`
3. `BearerAuthBackend` 不设置 `scope["user"]`
4. `RequireAuthMiddleware` 拒绝请求 → 401

MCP 子应用始终挂载，无需重启服务。

## 4. MCPServer 配置

### 4.1 AuthSettings 说明

`AuthSettings` 是 MCPServer 开启认证的开关。虽然设计用于 OAuth，但我们只需要其路由验证能力：

```python
from mcp.server.auth import AuthSettings

server = MCPServer(
    name="FlyMail",
    token_verifier=FlyMailTokenVerifier(),
    auth=AuthSettings(
        issuer_url="http://localhost:8080",   # 必填，仅用于 OAuth metadata 通告
        resource_server_url=None,              # 必填，传 None 即可
    ),
)
```

### 4.2 认证中间件栈

当 `auth` 和 `token_verifier` 同时设置时，`sse_app()` 自动构建：

| 中间件 | 作用 |
|--------|------|
| `AuthenticationMiddleware` | 提取 Bearer token，调用 `verify_token()` |
| `AuthContextMiddleware` | 将 `AuthenticatedUser` 存入 `auth_context_var` |
| `RequireAuthMiddleware` | 包裹 SSE 和 POST 端点，拒绝未认证请求 |

### 4.3 contextvar 传播

`AuthContextMiddleware` 使用 `contextvars.ContextVar` 存储认证用户。Python 3.11+ 自动将 contextvar 传播到子任务，因此工具 handler 中调用 `get_access_token()` 总能获取到当前连接的认证信息。

## 5. 后端 API

### 5.1 MCP 设置端点

在 `routes/settings.py` 中新增：

| 方法 | 路径 | 请求体 | 响应 | 说明 |
|------|------|--------|------|------|
| `GET` | `/api/settings/mcp` | — | `McpSettingsResponse` | 获取 MCP 配置 |
| `PUT` | `/api/settings/mcp` | `McpSettingsRequest` | `StatusResponse` | 更新 MCP 配置 |
| `POST` | `/api/settings/mcp/regenerate` | — | `TokenResponse` | 刷新 token |

### 5.2 数据模型

```python
# schemas.py 新增

class McpSettingsRequest(BaseModel):
    enabled: bool = Field(description="是否启用 MCP 服务器")
    port: int = Field(default=9000, ge=1024, le=65535, description="独立运行端口")

class McpSettingsResponse(BaseModel):
    enabled: bool = Field(description="是否启用")
    port: int = Field(description="端口")
    has_token: bool = Field(description="是否已配置 token")
    token: str = Field(default="", description="token 掩码（仅首次创建时返回完整值）")

class McpTokenResponse(BaseModel):
    success: bool = Field(description="是否成功")
    token: str = Field(description="新生成的 token")
```

### 5.3 端点实现

```python
# routes/settings.py 新增

import secrets
from schemas import McpSettingsRequest, McpSettingsResponse, McpTokenResponse

@router.get("/api/settings/mcp", response_model=McpSettingsResponse)
async def get_mcp_settings(request: Request):
    """获取 MCP 配置"""
    uid = await get_uid(request)
    settings = await get_user_settings(uid, ["mcp_enabled", "mcp_port", "mcp_token"])
    token = settings.get("mcp_token", "")
    return McpSettingsResponse(
        enabled=settings.get("mcp_enabled") == "true",
        port=int(settings.get("mcp_port", "9000")),
        has_token=bool(token),
        token=token[:12] + "..." if token else "",
    )


@router.put("/api/settings/mcp")
async def update_mcp_settings(request: Request, body: McpSettingsRequest):
    """更新 MCP 配置"""
    uid = await get_uid(request)

    # 首次启用 → 自动生成 token
    token = await get_user_setting(uid, "mcp_token")
    if body.enabled and not token:
        token = "fm_mcp_" + secrets.token_urlsafe(32)
        await set_user_setting(uid, "mcp_token", token)

    await set_user_settings(uid, {
        "mcp_enabled": "true" if body.enabled else "false",
        "mcp_port": str(body.port),
    })

    return {"success": True, "token": token[:12] + "..." if token else "", "has_token": bool(token)}


@router.post("/api/settings/mcp/regenerate", response_model=McpTokenResponse)
async def regenerate_mcp_token(request: Request):
    """刷新 MCP token（旧 token 立即失效）"""
    uid = await get_uid(request)
    token = "fm_mcp_" + secrets.token_urlsafe(32)
    await set_user_setting(uid, "mcp_token", token)
    return McpTokenResponse(success=True, token=token)
```

### 5.4 配置存储

复用 `user_settings` 表，Key-Value 结构：

| Key | Value | 默认 | 说明 |
|-----|-------|------|------|
| `mcp_enabled` | `"true"` / `"false"` | `"false"` | 是否启用 |
| `mcp_port` | `"9000"` | `"9000"` | 独立运行端口 |
| `mcp_token` | `"fm_mcp_<base64>"` | 空 | 认证令牌 |

## 6. MCP 工具清单

所有工具通过 `@server.tool()` 注册，内部调用 `db` 或 `services` 模块（同 API routes 层）。

### 6.1 邮件工具

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_search_emails(query, account_id, folder, limit, offset)` | `db.get_cached_messages_by_folder()` / `get_unified_inbox_messages()` | 按关键词搜索缓存邮件 |
| `flymail_get_email(account_id, uid, folder)` | `db.get_cached_message_detail()` | 获取单封邮件完整详情 |
| `flymail_get_recent_emails(account_id, folder, limit, offset)` | `db.get_cached_messages_by_folder()` / `get_unified_inbox_messages()` | 最近 N 封邮件 |
| `flymail_get_unread_counts()` | `db.get_folder_stats()` | 所有账号未读数 |
| `flymail_list_folders(account_id)` | `db` 直接查询 `folder_stats` | 文件夹列表 |

### 6.2 账号工具

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_list_accounts()` | `db.get_accounts()` | 所有邮箱账号 |
| `flymail_get_account(account_id)` | `db.get_account_by_id()` | 单账号详情 |

### 6.3 联系人工具

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_search_contacts(query, limit)` | `db.get_contacts()` | 搜索联系人 |
| `flymail_get_contact(contact_id)` | `db.get_contact_by_id()` | 单联系人详情 |

### 6.4 通知工具

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_list_notifications(limit)` | `db.get_notifications()` | 最近通知 |

### 6.5 系统工具

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_get_health()` | `db.get_db()` + `version` | 健康检查 |
| `flymail_get_settings()` | `db.get_user_settings()` | 应用设置 |
| `flymail_get_summary()` | 复合查询 | 全局概览 |

### 6.6 扩展能力（后续）

| 工具 | 后端调用 | 说明 |
|------|---------|------|
| `flymail_mark_read(account_id, uid, folder)` | IMAP STORE | 标记已读 |
| `flymail_send_email(to, subject, body, account_id)` | SMTP | 发送邮件 |
| `flymail_sync_folder(account_id, folder)` | `services.sync` | 触发同步 |
| `flymail_star_email(account_id, uid, folder)` | IMAP STORE | 标记星标 |

### 6.7 MCP 资源

| URI | 说明 |
|-----|------|
| `flymail://accounts` | 所有账号 |
| `flymail://accounts/{account_id}` | 单账号 |
| `flymail://emails/{account_id}/{folder}` | 文件夹邮件列表 |
| `flymail://emails/{account_id}/{folder}/{uid}` | 单封邮件 |
| `flymail://contacts` | 所有联系人 |
| `flymail://notifications` | 最近通知 |
| `flymail://health` | 健康状态 |

## 7. 前端 UI 设计

### 7.1 页面位置

在 `Settings.vue` 中新增一个折叠卡片，位置在「第三方通知设置」和「配置教程」之间。

### 7.2 卡片结构

完全复用现有三张卡片（Gmail 代理 / 备份 / 通知）的 design pattern：

```
.provider-card
  .gmail-toggle (点击展开/折叠)
    .gmail-toggle-left
      .gmail-toggle-icon (机器人 SVG)
      .gmail-toggle-text
        .gmail-toggle-title  "MCP Server"
        .gmail-toggle-desc   "AI 助手接入"
    .guide-arrow

  .card-body (v-if="mcpOpen")
    .field (启用开关)
      .toggle-switch (v-model="mcpForm.enabled")

    .field (端口)
      .input (type="number", v-model="mcpForm.port")
      .field-hint "子应用挂载模式自动使用主端口 (8080)"

    .field (令牌)
      .field-input
        .input (type="password"/"text", v-model="mcpForm.token_display")
        button.btn-secret-toggle (显示/隐藏)
        button.btn-copy (复制到剪贴板)
        button.btn-regenerate (刷新 token)

    .mcp-guide (连接方式说明)
      .mcp-guide-title "连接方式"
      .mcp-config-code (JSON 代码块)
        {
          "mcpServers": {
            "flymail": {
              "url": "http://192.168.1.100:8080/mcp/sse",
              "headers": {
                "Authorization": "Bearer fm_mcp_xxx..."
              }
            }
          }
        }
      .mcp-status (运行状态)
        ● 运行中 · 端口 8080

    .save-bar
      .btn-save (保存设置)
      .status-msg.success/error
```

### 7.3 交互细节

| 元素 | 行为 |
|------|------|
| 启用开关 | 关闭时端口/令牌区域灰色禁用（`.notify-dim` 模式） |
| 令牌显示/隐藏 | 默认 `password` 类型，点击切换可见性 |
| 复制令牌 | `navigator.clipboard.writeText()` + 短暂提示「已复制」 |
| 刷新令牌 | 弹出确认框：「刷新后旧令牌立即失效，已连接的 AI 助手需更新配置。确定继续？」 |
| 保存设置 | 调用 `PUT /api/settings/mcp`，成功后显示 ✓ 保存成功 |
| 首次启用无 token | 显示「启用后自动生成」提示，不显示空输入框 |

### 7.4 新增样式

```css
/* 代码块（Claude Desktop 配置） */
.mcp-config-code {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
  color: var(--text-primary);
  margin: 8px 0;
}

/* 状态指示 */
.mcp-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 12px;
}

.mcp-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}

/* 复制/刷新按钮 — 复用 .check-proxy-btn 样式 */
```

### 7.5 交互逻辑

```typescript
// Settings.vue script 新增

const mcpOpen = ref(false);
const mcpForm = ref({
  enabled: false,
  port: 9000,
  token_display: '',
  has_token: false,
});
const mcpTokenVisible = ref(false);
const mcpSaving = ref(false);
const mcpSuccess = ref(false);
const mcpError = ref('');
const mcpRegenerating = ref(false);

async function loadMcpSettings() {
  try {
    const data = await api.get('/settings/mcp') as any;
    mcpForm.value = {
      enabled: data.enabled,
      port: data.port || 9000,
      token_display: data.has_token ? '••••••••••••••••' : '',
      has_token: data.has_token,
    };
  } catch (e) {
    console.error('加载 MCP 设置失败:', e);
  }
}

async function saveMcpSettings() {
  mcpSaving.value = true;
  mcpSuccess.value = false;
  mcpError.value = '';
  try {
    const res = await api.put('/settings/mcp', {
      enabled: mcpForm.value.enabled,
      port: mcpForm.value.port,
    }) as any;
    if (res.success) {
      mcpSuccess.value = true;
      // 如果首次启用时生成了 token，更新显示
      if (res.has_token && !mcpForm.value.has_token) {
        mcpForm.value.has_token = true;
        mcpForm.value.token_display = '••••••••••••••••';
      }
      await loadMcpSettings();
      setTimeout(() => { mcpSuccess.value = false; }, 3000);
    }
  } catch (e: any) {
    mcpError.value = e.message || '保存失败';
    setTimeout(() => { mcpError.value = ''; }, 5000);
  } finally {
    mcpSaving.value = false;
  }
}

async function regenerateMcpToken() {
  // 确认弹窗
  if (!confirm('刷新后旧令牌立即失效，已连接的 AI 助手需更新配置。确定继续？')) {
    return;
  }
  mcpRegenerating.value = true;
  try {
    const res = await api.post('/settings/mcp/regenerate') as any;
    if (res.success) {
      mcpForm.value.token_display = res.token;
      mcpForm.value.has_token = true;
      // 复制到剪贴板
      await navigator.clipboard.writeText(res.token);
    }
  } catch (e: any) {
    mcpError.value = e.message || '刷新失败';
  } finally {
    mcpRegenerating.value = false;
  }
}

async function copyMcpToken() {
  if (!mcpForm.value.has_token) return;
  try {
    // 先从 API 获取完整 token（或从 regenerate 的结果缓存）
    const data = await api.get('/settings/mcp') as any;
    // 但 token 是掩码的，所以复制需要另寻方式
    // 用户刚 regenerate 时 token 在变量中
  } catch (e) {
    // 提示用户 regenerate 后复制
  }
}
```

> 注意：复制令牌的流程需要特殊处理。`GET /api/settings/mcp` 返回掩码 token，因此复制操作需要在 regenerate 时同时完成（将完整 token 写入剪贴板），或在保存时返回完整 token。

## 8. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/flymail_mcp/__init__.py` | **新建** | 包说明 |
| `backend/flymail_mcp/server.py` | **新建** | MCPServer 实例 + 13 个工具 + 7 个资源 + CLI |
| `backend/flymail_mcp/auth.py` | **新建** | FlyMailTokenVerifier |
| `backend/routes/settings.py` | **修改** | 新增 3 个 MCP 设置端点 |
| `backend/schemas.py` | **修改** | 新增 McpSettingsRequest / McpSettingsResponse / McpTokenResponse |
| `backend/db/__init__.py` | **修改** | 新增 get_user_uid_by_mcp_token() |
| `backend/main.py` | **修改** | lifespan 中挂载 MCP 子应用 |
| `frontend/src/views/Settings.vue` | **修改** | 新增 MCP 配置卡片 |
| `docs/mcp-design.md` | **新建** | 本文档 |

## 9. 部署方式

### 9.1 子应用挂载（默认）

```bash
cd backend
pip install -r requirements.txt
python dev.py
# MCP 服务在 http://localhost:8080/mcp/sse
```

通过 `FLYMAIL_MCP_PORT` 环境变量控制（已实现），但子应用挂载模式下端口配置无效。

### 9.2 独立运行

```bash
cd backend
python -m flymail_mcp.server                    # SSE on :9000
python -m flymail_mcp.server --port 9001         # 自定义端口
python -m flymail_mcp.server --transport stdio   # stdio 模式
```

独立运行模式通过 `--port` 参数配置端口，使用 `FLYMAIL_DATA_DIR` 环境变量指定数据目录。

## 10. 安全考虑

| 维度 | 措施 |
|------|------|
| Token 强度 | `secrets.token_urlsafe(32)` = 256-bit |
| Token 传输 | 仅通过 Bearer header 传递，不暴露在 URL 中 |
| Token 存储 | SQLite 明文（自托管 NAS 场景可接受） |
| 数据隔离 | 每个请求通过 `get_access_token().subject` 获取用户标识 |
| 拒绝服务 | `RequireAuthMiddleware` 拒绝无 token 请求 |
| 路径安全 | 子应用挂载在 `/mcp` 前缀下，不干扰主应用路由 |
| 本地访问 | `sse_app()` 自动启用 DNS rebinding 保护 |

## 11. 与直接读 DB 方案的对比

| 维度 | 直接读 DB | 本方案 |
|------|-----------|--------|
| 数据访问 | `db` 直调，无认证 | `db` 直调，但经 **Token → user_uid** 认证 |
| 权限校验 | 无 | `BearerAuthBackend` + `RequireAuthMiddleware` |
| 用户隔离 | 调用方自报 `user_uid` | 从 **token 映射** 获取，不可伪造 |
| 读写能力 | 只读 | 可扩展写操作 |
| 部署 | 独立进程 + 额外端口 | **同进程、同端口**，子应用挂载 |
| 管理 | 无 UI | 设置页有完整 UI：开关/令牌/状态 |
| 认证实现 | 无 | 3 层：提取 → 验证 → 拒绝 |