# analyze-b50

一个面向 Codex 的 maimai DX B50 分析 skill。

它会：

- 通过 Diving-Fish API 按 QQ 拉取 B50
- 结合内置 `music_data.json`、`chart_summary.json`、KB 和匿名同段统计做分析
- 生成接近原插件风格的 OneCat 口播文案
- 生成原插件风格的分析图

## 目录

- `SKILL.md`：主使用说明和提示词约束
- `agents/openai.yaml`：UI 默认提示
- `scripts/`：拉取数据、准备上下文、渲染图片
- `assets/`：音乐数据、知识库、字体、图标、匿名 peer stats
- `references/`：字段和规则说明

## 使用方式

在 Codex 里直接说：

> 分析b50

然后按顺序提供：

1. QQ 号
2. 语气 / 人设
3. 分析角度

skill 会继续跑完整流程，直到输出文本和图片。

## 数据来源

- B50：Diving-Fish 公共接口
- 同段平均值 / ARPI / 重合度：匿名聚合的 `peer_stats.zip`
- 谱面知识：内置 `music_data.json`、`chart_summary.json`、KB

不依赖本地数据库，不包含原始字幕样本。

## 输出

- 单段口播式中文分析文案
- 一张接近原插件版式的分析图

## 打包说明

发布包使用 zip 即可，建议排除：

- `tmp/`
- `scripts/__pycache__/`
- `assets/cache/covers/`

## 许可

MIT License。
