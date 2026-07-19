# 通知卡片内置资源

| 文件 | 用途 |
|------|------|
| `SourceHanSansSC-Regular.otf` | 中文卡片字体（思源黑体 SC Regular，SIL Open Font License） |
| `icon.png` | 卡片顶栏 LOGO |

正式环境为 Nuitka onefile，系统未必有中文字体；必须随二进制打包本目录。
CI 使用：`--include-data-dir=.../services/notify/assets=services/notify/assets`
