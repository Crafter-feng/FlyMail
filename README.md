<div align="center">

# FlyMail 飞邮

**专为多邮箱用户打造的自托管邮件客户端**

[![Version](https://img.shields.io/badge/version-1.0.7-blue?style=flat-square)](VERSION)
[![License](https://img.shields.io/badge/license-GPL--3.0-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=flat-square&logo=python)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3-brightgreen?style=flat-square&logo=vue.js)](https://vuejs.org/)

</div>

---

## 项目简介

FlyMail（飞邮）是一款运行在飞牛 OS 上的自托管邮件客户端，让用户在一个界面统一管理 Gmail、Outlook、QQ 邮箱、网易邮箱、iCloud、新浪邮箱等主流平台的邮件。所有邮件数据存储在用户自己的 NAS 上，隐私可控，无需依赖第三方云服务。

## 核心功能

- **多邮箱聚合**：所有邮箱邮件混排展示，按时间统一排序，支持按邮箱筛选与身份标识
- **邮件收发**：支持纯文本 / HTML 富文本编辑、附件上传下载、草稿保存、定时发送
- **实时同步**：IMAP IDLE 长连接秒级推送新邮件，Poll 轮询兜底兼容更多平台
- **智能缓存**：SQLite 摘要缓存 + 增量同步，收件箱秒开，断网仍可浏览已缓存邮件
- **本地备份**：邮件以 `.eml` 格式归档到飞牛 OS 授权目录，支持附件完整保存与独立下载
- **桌面通知**：WebSocket 实时推送新邮件通知，通知中心统一管理
- **联系人管理**：左右分栏布局，支持同名联系人与多邮箱关联
- **用户隔离**：不同 NAS 用户数据完全隔离，账号、邮件、设置互不可见
- **移动端适配**：响应式布局，手机端触控友好

## 支持的邮箱平台

| 邮箱平台 | 认证方式 | 实时同步 | 发送邮件 |
|:--------|:---------|:---------|:---------|
| Gmail | OAuth 2.0 | IDLE | SMTP |
| Outlook | OAuth 2.0 | IDLE | SMTP |
| QQ 邮箱 | 授权码 | IDLE | SMTP |
| 网易邮箱 (163/126/yeah.net) | 授权码 | Poll | SMTP |
| iCloud | 应用专用密码 | Poll | SMTP |
| 新浪邮箱 | 授权码 | Poll | SMTP |
| 自定义 IMAP/SMTP | 账号密码 | Poll | SMTP |

## 技术栈

| 层级 | 技术 |
|:-----|:-----|
| 前端 | Vue 3 + TypeScript + Pinia + Vite |
| 后端 | Python 3.11 + FastAPI + aiosqlite |
| 数据库 | SQLite (WAL 模式) |
| 邮件协议 | IMAP (IDLE/Poll) + SMTP |
| 实时通信 | WebSocket |
| 构建工具 | Nuitka (二进制编译) + fnpack |

## 开源协议

本项目基于 [GPL-3.0](LICENSE) 协议开源。

版权所有 © 2026 DinDing1

任何人都可以自由使用、修改和分发本项目，但派生作品必须同样以 GPL-3.0 协议开源，并保留原始版权声明。

## 商标声明

**FlyMail™ 和飞邮™ 是 DinDing1 的未注册商标。**

未经授权，不得在派生项目或相关宣传中使用 "FlyMail"、"飞邮" 名称或其变体来暗示与本项目的关联或背书。本商标声明不限制 GPL-3.0 协议赋予你的代码使用、修改和分发权利，仅用于保护项目名称的识别性，防止混淆。

---

<div align="center">

Made for 飞牛 OS

[![GitHub Stars](https://img.shields.io/github/stars/DinDing1/FlyMail?style=social)](https://github.com/DinDing1/FlyMail/stargazers)

</div>
