# 飞邮通知图床（flymail-imgbed）

每用户自建的 Cloudflare Worker + R2 图床，用于**图片通知模式**下需要公网 HTTPS 图片 URL 的渠道（如 Bark）。
Telegram 图片走 Bot API multipart 直传，**不依赖**本服务。

## 一键部署（推荐）

1. 打开飞邮「设置 → 通知设置 → Cloudflare 图床」中的 **to Cloudflare**，或访问：

   [Deploy to Cloudflare](https://deploy.workers.cloudflare.com/?url=https://github.com/DinDing1/FlyMail/tree/main/flymail-imgbed)

2. 使用**你自己的** Cloudflare 账号登录并完成部署。
3. 在 Worker 中设置 Secret：`UPLOAD_TOKEN`（随机长串，自己生成）。
4. 记下 Worker 地址，例如：`https://flymail-imgbed.<你的子域>.workers.dev`
5. 回到飞邮填写：
   - 图床地址 = 上面的根地址（不要带 `/upload`）
   - 上传密钥 = 与 `UPLOAD_TOKEN` 相同

## 本地部署

```bash
npm install
npx wrangler login
npx wrangler r2 bucket create flymail-imgbed
npx wrangler secret put UPLOAD_TOKEN
npx wrangler deploy
```

## API

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/health` | 无 | 探活 |
| POST | `/upload` | Bearer | 上传 PNG/JPEG，返回 `{ url, key }` |
| GET | `/i/:key` | 无 | 公开读图（Bark 拉取） |
| POST | `/purge` | Bearer | 删除全部对象 |
| DELETE | `/i/:key` | Bearer | 删除单张 |

上传示例：

```bash
curl -X POST "https://你的域名/upload" \
  -H "Authorization: Bearer 你的TOKEN" \
  -H "Content-Type: image/png" \
  --data-binary @card.png
```

## 防超标（强烈建议）

在 Cloudflare 控制台 → R2 → `flymail-imgbed` → 生命周期规则：

- 对象创建 **3～7 天后**自动删除

通知卡片仅供即时拉取，无需长期保存。飞邮设置页也提供「清理图床」手动清空。

## 安全说明

- 上传/清理必须带 Token；Token 只填在飞邮服务端配置，不要泄露。
- 读图接口公开，是因为 Bark 服务端需要无鉴权 GET。
- 请勿把本 Worker 当通用网盘使用。

## 与飞邮 OAuth Broker 的关系

本模板与 `cloudflare/`（OAuth 中转）**完全独立**，请勿混用同一 Worker。
