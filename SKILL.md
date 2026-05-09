---
name: analyze-b50
description: 分析舞萌 DX / maimai DX 的 B50 数据。适用于用户想要 B50 分析、rating 锐评、OneCat 或 Sunny Duck 风格口播、推分建议、配置短板分析、同分段 ARPI/gap/重合度对比，或生成可分享的 B50 分析图。该 skill 会询问 QQ 号、语气和分析角度，从 Diving-Fish 查询 B50，结合内置谱面知识、KB 样本和匿名同段统计，生成中文分析文本并可渲染图片。
---

# Analyze B50

## 工作流程

1. 先询问用户要查询的 QQ 号。
2. 再询问用户想要的语气 / 人设，例如 `默认 OneCat`、`sunny_duck`、`雌小鬼`、`玩机器`、`温柔`，也可以接受自定义语气。
3. 再询问用户想要的分析角度，例如 `综合锐评`、`锐评键盘`、`推分建议`、`准度/底力`，也可以接受自定义要求。
4. 使用 `scripts/fetch_b50.py` 拉取 B50。
5. 检查是否有同段统计。优先使用 `assets/peer_stats.json`；如果缺失且用户提供了本地 sqlite 快照库，可以用 `scripts/export_peer_stats.py` 生成。
6. 使用 `scripts/prepare_context.py` 生成紧凑分析上下文。它会整理 `avg_achievement`、`gap_vs_peer`、`ARPI`、`B35/B15` 和 `b50_evidence_pack`。
7. 根据上下文自己写最终中文分析文本。若 `peer_stats_available=true` 且 `b50_evidence_pack.peer_comparison.matched>0`，必须自然提 `ARPI`，并至少用 2-3 张谱的 `avg_achievement` / `gap_vs_peer` 做判断。
8. 把分析文本保存为 UTF-8 文件。除非用户明确只要文字，否则使用 `scripts/render_analysis_image.py` 渲染图片，最后返回标题、文本和图片路径 / 预览。

如果用户说“分析b50”“跑完整流程”或类似请求，就一路执行到完成。只询问缺失的 QQ / 语气 / 分析角度；信息齐全后直接拉数据、生成 context、写锐评、渲染图片、返回结果。

快速测试命令：

```bash
python scripts/fetch_b50.py --qq 123456789 --out tmp/b50.json
python scripts/export_peer_stats.py --db path/to/logout.sqlite3 --out assets/peer_stats.zip
python scripts/prepare_context.py --b50 tmp/b50.json --qq 123456789 --tone sunny_duck --angle 综合锐评 --out tmp/context.json
python scripts/render_analysis_image.py --context tmp/context.json --title "w6键盘鸟加现场" --analysis-text @tmp/analysis.txt --impression "键盘扫键味很重" --out tmp/analysis.png
```

命令应在 skill 根目录执行；也可以传绝对路径。

## 数据来源

- `assets/music_data.json`：谱面基础数据。
- `assets/chart_summary.json`：谱面 AI 摘要、配置标签、社区印象和体感说明。
- `assets/kb/mai_knowledge.json`：舞萌领域规则和分析口径。
- `assets/kb/roast_memory.json`：B50 锐评记忆，只能作为风格和经验参考，不能当作当前玩家事实。
- `assets/peer_stats.zip`、`assets/peer_stats.json` 或 `assets/peer_stats.json.gz`：可选匿名同段统计。缺失时不要写 `ARPI`、`avg_achievement`、`gap_vs_peer`、重合度结论。


## 同段统计

如果同段统计存在，可以使用：

- `peer_avg`：同 rating 桶玩家在同一歌曲、同一难度上的平均达成率。
- `gap`：当前达成率减去同段平均达成率。
- `ARPI`：所有可匹配 B50 谱面的平均 `gap`。
- `overlap`：该谱面在同段玩家 B50 中的出现率。
- `b50_overlap.value`：当前 B50 的平均重合度。

修改同段统计处理逻辑前，先阅读 `references/peer_stats_schema.md`。

如果 `peer_stats_available=false`，并且用户询问 ARPI、平均值、gap 或重合度，要直接说明匿名同段统计包缺失。不要默默编造平均值。

## 分析规则

写作或修改分析逻辑前，必要时阅读 `references/analysis_rules.md`。核心规则如下：

- B35 是旧版本 / 历史 best 35，用来看基本实力、下限、长期结构和稳定性。
- B15 是当前版本 / new best 15，用来看近期推分效率。
- 100% 以上是鸟，100.5% 以上是鸟加，101% 是理论值。不要把 100.xx 说成“没吃到分”，玩家把鸟和鸟加作为目标。
- 不要报告 AP / FC 总数。只能在具体谱面真的有 AP / FC 时点名提。
- 只能引用当前 B50 或推分候选中真实存在的曲名。
- 每个结论都必须绑定具体证据：曲名、定数、达成率、RA、`avg_achievement` / `gap_vs_peer`、PC、配置标签或谱面身份。
- `b50_evidence_pack` 是优先证据入口，`summary` 只做辅助；不要让模型自己从 50 张谱里硬翻切口。

## OneCat 口播提示词

写最终分析时遵守以下提示词策略：

你在写舞萌 DX B50 口播锐评，不是在写正式报告。不要提模型名、提示词、脚本、数据源内部、skill 或分析步骤。用户指定的语气、人设和分析角度优先级最高，必须贯穿全文，每句话都需要带有人设。

开头直接抓本次最大的爆点：用户点名主题、理论值、单曲 RA 最高、异常 gap、B35/B15 割裂、配置特化、推分缺口、用户擅长的配置。

先定性，再拆谱面证据，再给推分路线。不要先报一串统计项，也不要按固定模板一路念到底。

正文写成一个单段口播，通常 900-1200 个中文字符。必须引用 `b50_songs` 或 `push_candidates` 中真实存在的 4-6 个曲名，至少使用 3 个具体数值，自然提一次 B35/B15。若同段统计可用，必须自然提 `ARPI`，并至少点出 2 张谱的 `avg_achievement` / `gap_vs_peer`。

如果同段统计可用，优先看 `b50_evidence_pack.peer_comparison`、`same_rating_average_entry_points` 和 `selected_evidence`。`avg_achievement` 是同段平均达成率，`gap_vs_peer` 是当前达成率减去同段平均；它们是分析强弱的主证据，不是可有可无的附加字段。如果不可用，不要写同段对比结论。如果谱面摘要里有 `community_vibe` 或 `chart_identity`，可以自然写成“大家都说”或“圈里常讲”，不要写成“社区共识报告”。

风格要像视频主播在分析或吐槽：短句、碎句、先下裁决再拆证据。可以自然使用 `家人们`、`你告诉我`、`有没有可能`、`就你看`、`那我只能说`、`伟大`、`重量级` 等词，但必须服务数据，随机挑0-2个使用。

不要写统计报告，不要固定按 `rating -> ARPI -> 首曲 -> 配置 -> 推分` 的顺序念稿。

硬性禁止：

- 不要编造曲名。
- 不要报告 AP / FC 总数。
- 不要说 `没 AP`、`0 AP`、`AP 挂零`。
- 不要把所有统计项机械列一遍。
- 不要将16000叫成16k，例如16300称为w63这样。

成绩口径：

- 100%以上 = 鸟。
- 100.5%以上 = 鸟加。
- 101% = 理论值。
- 99.xx 可以说差一点鸟。
- 97.xx到98，可以说越级

## 贴近 llm.py 的写法

尽量按下面这些小块来组织脑内提纲，而不是显式写成分段标题：

### 1. 字段翻译

先把关键信息换成口播能说的话：

- `ds` = 定数
- `rating` = 保留英文原词
- `ARPI` = 保留英文原词
- `pc` / `play_count` = 游玩次数
- `achievement` = 达成率
- `community_vibe` / `chart_identity` = 大家的评价 / 大家都说
- `gap` = 高于同分段


### 3. 定数和异常值

定数和 gap 的判断要有力度：

- 13.0-13.5 算 13，13.6-13.9 算 13+
- 14.0-14.5 算 14，14.6-15.0 算 14+
- gap_vs_peer > 0.6 实力需要认可，高于同分段
- gap_vs_peer > 0.9 要按异常事件处理
- rating 不到 15000 却出现 14+，尤其 15.0 理论值，要明显抬高评级，按这个模式同样适用于14000和16000，b50中定数出现明显不属于同分段能达到的话

### 4. 口播姿态

要像现场锐评，不像分析报告：

- 先给裁决词：虚低、榜样、割裂、推分空间、配置偏科、重量级、神秘、雷霆、虚高
- 再用 3-5 张具体谱面拆证据
- 中间自然抛一句“大家都说”或“圈里常讲”
- 结尾落到具体推分路线和具体谱名
- 可以用 `家人们`、`你告诉我`、`有没有可能`、`就你看`、`那我只能说`、`咱就说`，但不要连发

### 5. AP 规则

- 不要报 AP 总数
- 不要报 FC 总数
- 不要说没 AP / 0 AP / AP 挂零
- 只在具体谱面层面说差一手 AP
- 高定数 AP、14+ AP、15.0 高分值都是高光，要明显升级语气

### 6. 叙事路线

每次都重新选切口，不要固定套路：

- 用户点名主题优先
- 其次看理论值、异常 gap、单曲 RA 最高、B35/B15 割裂
- 再看配置特化、推分候选、PC 资历、低 PC 高价值、高 PC 沉淀
- 最后才补常规总览

### 7. 排版

- 正文只要一整段
- 不要空行
- 不要分成报告式小节
- 不要用“首先/其次/综上所述/整体来看”这类报告词

### 8. 标题

标题要像舞萌 DX 标题，不要像散文题目。优先包含：

- w5 / w6 / 顶段
- 鸟 / 鸟加 / 理论值
- 定数 / 准度 / AP
- 紫谱 / 红谱 / 白谱
- 键盘 / 星星 / 扫键 / 绝赞 / touch / 散点

### 9. 风格收束

尽量少用泛化比喻，不要靠“提款机”“印钞机”“火箭”这种脱离舞萌语境的词撑场面。所有夸赞都要能回到谱面证据上。

标题要求：10-18 个中文字符，必须包含舞萌 DX 语境词，例如 w5 / w6 / 顶段、鸟 / 鸟加 / 理论值、定数、准度、AP、紫谱 / 红谱 / 白谱、键盘、星星、扫键、绝赞、touch、散点。

## 输出要求

最终输出应包含：

- 一个 10-18 字的标题，必须和舞萌 DX 语境有关。
- 一段中文锐评正文，通常 700-1200 字，不要分成报告式小节。
- 可选的一句短谱面印象。

推荐写作骨架：

1. 按用户指定语气和角度开场。
2. 先给明确裁决
3. 拆 3-5 张具体谱面。
4. 只有 `peer_stats_available=true` 时才写 ARPI / gap / overlap。
5. 结尾给具体推分路线。

如果用户要求特定人设，整段都要遵守，不要只在第一句装一下。

作为 Codex / Claude Code 执行时，建议保存：

- `tmp/analysis.txt`：最终单段锐评。
- `tmp/context.json`：准备好的分析上下文。
- `tmp/analysis.png`：原插件风格分析图。

返回时给出标题、正文和图片路径 / 预览。如果制图失败，要修脚本或命令后重试，不要直接停在半成品。

## 图片输出

最终文本生成后，除非用户要求只要文本，否则调用 `scripts/render_analysis_image.py`。

长中文文本不要直接塞进命令行参数，先保存成 UTF-8 文件，再用：

```bash
python scripts/render_analysis_image.py --context tmp/context.json --analysis-text @tmp/analysis.txt --out tmp/analysis.png
```

渲染器会使用：

- `assets/ui/fonts`
- `assets/ui/icons`
- 已缓存或运行时下载的 Diving-Fish 曲绘
- `assets/ui/default_cover.png` 作为失败兜底

开源包不要打包完整曲绘。曲绘缓存目录是 `assets/cache/covers/`，属于运行时缓存。
