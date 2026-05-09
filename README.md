# analyze-b50

面向 Codex / Claude Code 的 maimai DX B50 分析 skill。

`analyze-b50` 会按 QQ 从 Diving-Fish 拉取玩家 B50，结合谱面知识库、匿名同段统计和内置规则，生成 OneCat / Sunny Duck 风格的口播锐评，并输出一张接近原插件版式的分析图。

## 功能

- 按 QQ 查询 Diving-Fish B50
- 计算 B35 / B15 均值、同段均值、ARPI、gap、B50 重合度
- 分析亮点谱面、短板谱面、配置特化、推分候选
- 生成单段中文口播锐评
- 渲染分享图，支持曲绘缓存和默认封面兜底
- 不依赖 NoneBot、本地数据库或原插件运行环境

## 快速使用

在 Codex 或 Claude Code 里可以直接说：

```text
帮我安装 https://github.com/HanYaaaaaaa/analyze-b50 这个 skill，然后分析 b50
```

随后按提示提供：

1. QQ 号
2. 语气 / 人设，例如 `默认 OneCat`、`sunny_duck`、`雌小鬼`、`玩机器`
3. 分析角度，例如 `综合锐评`、`锐评键盘`、`推分建议`、`准度/底力`

拿到信息后，skill 会继续完成拉取数据、准备上下文、生成文本和渲染图片。

## 兼容性说明

- Codex：可以按 Codex skill 使用，主要入口是 `SKILL.md`。
- Claude Code：可以 clone 本仓库后，让 Claude Code 阅读 `README.md` 和 `SKILL.md` 执行同样流程；这不是 Anthropic 官方 Claude skill 包格式。

## 本地运行

需要 Python 3.10+。

```bash
pip install -r requirements.txt
python scripts/fetch_b50.py --qq 123456789 --out tmp/b50.json
python scripts/prepare_context.py --b50 tmp/b50.json --qq 123456789 --tone "默认 OneCat" --angle "综合锐评" --out tmp/context.json
python scripts/render_analysis_image.py --context tmp/context.json --title "w6键盘鸟加现场" --analysis-text @tmp/analysis.txt --out tmp/analysis.png
```

`tmp/analysis.txt` 需要先写入最终分析文案。推荐让 Codex / Claude Code 根据 `tmp/context.json` 和 `SKILL.md` 写。

## 资源文件

仓库内已包含运行所需的核心资源：

| 文件 | 作用 |
| --- | --- |
| `assets/music_data.json` | 谱面基础数据 |
| `assets/chart_summary.json` | 谱面配置和社区印象摘要 |
| `assets/kb/mai_knowledge.json` | 舞萌分析规则 |
| `assets/kb/roast_memory.json` | 口播风格和样本记忆 |
| `assets/peer_stats.zip` | 匿名同段统计，用于 ARPI / gap / 重合度 |
| `assets/ui/fonts/` | 制图字体 |
| `assets/ui/icons/` | rating、rank、FC/AP 图标 |
| `assets/ui/default_cover.png` | 曲绘下载失败时的默认封面 |

运行时会自动下载曲绘到：

```text
assets/cache/covers/
```

这个目录是缓存，不需要提交到仓库。如果网络无法访问 Diving-Fish 曲绘接口，图片会使用 `default_cover.png` 兜底。

## 资源更新

如果你维护了自己的匿名同段统计，可以替换：

```text
assets/peer_stats.zip
```

也可以从本地快照数据库重新导出：

```bash
python scripts/export_peer_stats.py --db path/to/logout.sqlite3 --out assets/peer_stats.zip
```

如果资源不随仓库分发，也可以让用户下载后放回固定路径：

```bash
python scripts/download_peer_stats.py --url "https://example.com/peer_stats.zip" --out assets/peer_stats.zip
```

如果你想把大资源放到 Release 而不是 Git 仓库，可以删除对应资源后，让用户下载并放回原路径。最少需要保留：

```text
assets/music_data.json
assets/chart_summary.json
assets/peer_stats.zip
assets/ui/fonts/
assets/ui/icons/
```

## 数据来源

- B50：Diving-Fish 公共接口
- 同段平均值 / ARPI / 重合度：匿名聚合 `peer_stats.zip`
- 谱面知识：内置谱面数据、谱面摘要和 KB

项目不包含：

- 原始字幕
- 本地用户数据库
- 私有 bot 配置
- API key 或 token

## 授权与资源声明

项目代码使用 MIT License。

内置字体、游戏 UI 图标、曲绘接口返回的封面以及 maimai DX 相关素材可能受各自原始权利方约束。它们仅用于生成本项目的分析图和本地测试，不代表这些第三方素材也按 MIT 授权。公开分发时请按所在地和平台规则自行确认资源授权。

## 目录结构

```text
analyze-b50/
├─ SKILL.md
├─ agents/openai.yaml
├─ assets/
├─ references/
├─ scripts/
├─ README.md
├─ RELEASE.md
└─ LICENSE
```

## 待优化

- 样本和谱面知识库仍需要持续补充
- 提示词还可以继续压缩 token
- 后续可选支持多模型协作
- 口播语气和用词还可以继续拟人化

## License

MIT License
