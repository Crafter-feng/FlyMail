# 通知卡片资源（图片模式）

| 文件 | 说明 |
|------|------|
| `SourceHanSansSC-Regular.otf` | 中文卡片字体（思源黑体 SC Regular，SIL Open Font License） |
| `icon.png` | 卡片左上角 LOGO |

## 打包策略（只保留一份）

- **源码**：本目录始终保留字体与图标，供本地开发与 CI 拷贝。
- **正式 FPK**：仅拷贝到 `app/server/notify-assets/`（可执行文件旁），**不再**用 Nuitka `--include-data-dir` 内嵌第二份，避免包体积多约 16MB。
- 运行时 `image_card._assets_dir()` 会优先找模块旁 `assets/`（本地），再找可执行文件旁 `notify-assets/`（正式包）。

## 运行时

- 正式环境由 `flymail/cmd/main` 注入 `FLYMAIL_NOTIFY_ASSETS=$TRIM_APPDEST/server/notify-assets`。
- `image_card` 优先选择「含字体文件」的目录（不能仅因 icon.png 命中），避免落到残缺 CJK 字体导致数字/字母空白。
- 加载后会探测拉丁+CJK 覆盖；主字体缺拉丁时按字符混排西文回退字体。
