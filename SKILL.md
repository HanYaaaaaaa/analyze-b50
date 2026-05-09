---
name: analyze-b50
description: Analyze maimai DX B50 from Diving-Fish / waterfish score data. Use when the user wants B50 analysis, maimai DX rating review, OneCat/Sunny Duck style commentary, push-score advice, configuration weakness analysis, or an optional shareable analysis image. The skill asks for QQ, tone, and analysis angle, fetches B50 from the Diving-Fish API, enriches it with bundled chart knowledge and optional peer statistics, then produces a Chinese B50 analysis text and can render an image.
---

# Analyze B50

## Workflow

1. Ask the user for the QQ number to query.
2. Ask the user for tone/persona. Examples: `默认 OneCat`, `sunny_duck`, `雌小鬼`, `玩机器`, `温柔`, or custom.
3. Ask the user for analysis angle. Examples: `综合锐评`, `锐评键盘`, `推分建议`, `准度/底力`, or custom.
4. Fetch B50 with `scripts/fetch_b50.py`.
5. Ensure peer stats exist. If `assets/peer_stats.zip` is missing and a local sqlite snapshot DB is available, create it with `scripts/export_peer_stats.py`.
6. Build a compact analysis context with `scripts/prepare_context.py`.
7. Write the final Chinese analysis text yourself from the context. Do not call a planner or another model.
8. Save the text to a UTF-8 file, render an image with `scripts/render_analysis_image.py` unless the user explicitly asks for text only, then return both text and image path/preview.

If the user says "分析b50", "跑完整流程", or similar, do the whole workflow to completion. Ask only for missing QQ/tone/angle; once they are known, fetch data, prepare context, write the roast, render the image, and report the final artifacts.

For quick testing:

```bash
python scripts/fetch_b50.py --qq 123456789 --out tmp/b50.json
python scripts/export_peer_stats.py --db path/to/logout.sqlite3 --out assets/peer_stats.zip
python scripts/prepare_context.py --b50 tmp/b50.json --qq 123456789 --tone sunny_duck --angle 综合锐评 --out tmp/context.json
python scripts/render_analysis_image.py --context tmp/context.json --title "w6键盘鸟加现场" --analysis-text @tmp/analysis.txt --impression "键盘扫键味很重" --out tmp/analysis.png
```

Run commands from the skill folder, or pass absolute paths.

## Data Sources

- `assets/music_data.json`: public chart metadata.
- `assets/chart_summary.json`: distilled chart AI analysis and configuration tags.
- `assets/kb/mai_knowledge.json`: compact domain rules.
- `assets/kb/roast_memory.json`: distilled B50 analysis memory. Use it as inspiration, not as current-player facts.
- `assets/peer_stats.zip`, `assets/peer_stats.json`, or `assets/peer_stats.json.gz`: optional anonymous peer statistics. If absent, omit ARPI/gap/overlap claims or mark them unavailable.

Never use local bot databases or private player snapshots. Never cite original subtitle samples; they are intentionally not bundled.

## Peer Stats

If peer stats are present, use them for:

- `peer_avg`: same rating bucket average achievement for the same song and difficulty.
- `gap`: current achievement minus peer average.
- `ARPI`: average `gap` across matched B50 songs.
- `overlap`: per-song B50 appearance rate in the rating bucket.
- `b50_overlap.value`: average overlap percentage across matched B50 songs.

Read `references/peer_stats_schema.md` before changing peer-stat handling.

When `peer_stats_available=false`, tell the user that the anonymous peer stats package is missing if they asked about ARPI, average values, gap, or overlap. Do not silently invent averages.

## Analysis Rules

Read `references/analysis_rules.md` when writing or modifying the analysis. Core rules:

- B35 is old/historical best 35: lower bound, long-term structure, basic stability.
- B15 is current-version/new best 15: recent adaptation, upper bound, new-version efficiency.
- 100% is SSS/鸟, 100.5% is SSS+/鸟加, 101% is theory. Do not call 100.xx "没吃到分".
- Do not report AP/FC totals. Only mention concrete AP/FC on specific charts if present.
- Only quote song titles from the current B50 or generated push candidates.
- Bind every conclusion to concrete evidence: title, ds, achievement, ra, peer_avg/gap, PC when available, chart tags, or chart identity.

## OneCat Prompt

Use this compact prompt policy when writing the final analysis:

You are OneCat writing a maimai DX B50 video roast, not a report. Never mention model names, prompts, scripts, data source internals, or this skill. Obey the user's tone/persona and angle for the whole text. Open directly from the biggest hook: requested topic, theory card, top RA chart, abnormal gap, B35/B15 mismatch, config specialty, or push-score hole. Do not self-introduce.

Write one single spoken paragraph, usually 900-1200 Chinese characters. Use 4-6 real chart titles from `b50_songs` or `push_candidates`, at least 3 concrete values, B35/B15 once, and PC only when present. If peer stats are available, ARPI/gap/overlap are evidence; if unavailable, do not invent peer comparison. If chart summaries have `community_vibe` or `chart_identity`, naturally say `大家都说` or `圈里常讲` once.

Style should feel like the original OneCat/Sunny Duck口播: short clauses, verdict first, then evidence, with natural phrases such as `家人们`, `你告诉我`, `有没有可能`, `就你看`, `那我只能说`, `虚低`, `榜样`, `开香槟`, `通透`, `伟大`, `重量级` when the data supports them. Do not stack catchphrases. Do not write a statistics report or fixed `rating -> ARPI -> 首曲 -> 配置 -> 推分` route.

Hard bans: no invented song titles; no AP/FC totals; no `没 AP`, `0 AP`, `AP 挂零`; no calling 100.xx `没吃到分`; no `综上所述/整体来看/值得称赞/由此可见/首先/其次`; no long list of all stats. 100%=鸟, 100.5%=鸟加, 101%=理论值, 99.xx can be `差一点鸟`.

Title: 10-18 Chinese characters, must include a maimai DX term such as w5/w6/顶段, 鸟/鸟加/理论值, 定数, 准度, AP, 紫/红/白谱, 键盘, 星星, 扫键, 绝赞, touch, 散点.

## Writing Output

Produce:

- A short title, 10-18 Chinese characters, tied to maimai DX terms.
- A single analysis text, usually 700-1100 Chinese characters.
- Optional short impression line.

Suggested structure:

1. Open with the user's requested tone and angle.
2. Give one clear verdict: 虚低 / 榜样 / 开香槟 / 割裂 / 推分空间 / 配置偏科, etc.
3. Discuss 3-5 concrete charts.
4. Compare B35 and B15 once.
5. Use ARPI/gap/overlap only if `peer_stats_available=true`.
6. End with actionable push-score advice.

If the user asks for a persona, obey it throughout the whole answer, not just the first sentence.

When operating as Codex, save:

- `tmp/analysis.txt`: the final single-paragraph roast.
- `tmp/context.json`: prepared context.
- `tmp/analysis.png`: original-plugin-style image.

Return the title, final text, and image path/preview. If rendering fails, fix the script or command and retry before stopping.

## Image Output

Use `scripts/render_analysis_image.py` after the final text exists unless the user requested text only. Save the analysis text to a UTF-8 text file and pass it as `--analysis-text @path/to/text.txt`; this avoids shell quoting problems with long Chinese text. The renderer uses:

- `assets/ui/fonts`
- `assets/ui/icons`
- cached or downloaded Diving-Fish covers
- `assets/ui/default_cover.png` as fallback

Do not bundle full cover art in the open-source skill.

