# Release Guide

面向维护者的发布说明。

## 发布前检查

发布前确认不要带上运行缓存和测试产物：

```text
tmp/
scripts/__pycache__/
assets/cache/covers/
```

建议执行：

```powershell
Remove-Item -Recurse -Force .\tmp -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\scripts\__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\assets\cache\covers -ErrorAction SilentlyContinue
```

## 验证

```powershell
python -m py_compile scripts\fetch_b50.py scripts\prepare_context.py scripts\render_analysis_image.py scripts\export_peer_stats.py scripts\download_peer_stats.py
$env:PYTHONUTF8='1'; python path\to\quick_validate.py .
```

## 打包

在项目父目录执行：

```powershell
Compress-Archive -Path .\analyze-b50 -DestinationPath .\analyze-b50.zip -Force
```

如果当前目录就是项目根目录，可以使用 Git 打包，避免把 `.git` 放进 zip：

```powershell
git archive --format=zip --prefix=analyze-b50/ --output ..\analyze-b50.zip HEAD
```

## 资源策略

当前仓库直接包含核心资源，用户 clone 后即可使用：

- `assets/music_data.json`
- `assets/chart_summary.json`
- `assets/peer_stats.zip`
- `assets/kb/`
- `assets/ui/fonts/`
- `assets/ui/icons/`

如果后续资源体积继续增长，可以改成 Release 附件模式：

1. 从 Git 仓库移除大资源。
2. 上传到 GitHub Release。
3. 在 `README.md` 写明下载地址和放置路径。
4. 保留 `scripts/download_peer_stats.py` 或扩展一个资源下载脚本。

## 不应发布的内容

- 原始字幕
- 本地数据库
- 私有 bot 配置
- 用户测试输出
- API key / token
- 曲绘缓存

## 授权提示

MIT License 只覆盖项目代码和自有整理内容。字体、游戏 UI 图标、曲绘和 maimai DX 相关素材可能有各自的原始授权限制；如果发布平台要求严格素材授权，建议把这些资源改为 Release 附件或让用户自行提供。

## 仓库定位

这是一个可独立使用的 Codex / Claude Code skill 项目，不是原 NoneBot 插件源码镜像。
