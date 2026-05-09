# 发布说明

这个发布包是 `analyze-b50` 的开源版，目标是让别人可以直接在 Codex 里使用，不依赖原来的 NoneBot 插件环境。

## 发布内容

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/`
- `assets/`
- `references/`
- `README.md`
- `LICENSE`

## 已处理的内容

- B50 数据改为直接走 Diving-Fish 公共接口
- 分析上下文改为 skill 内脚本生成
- 图像渲染改为独立脚本，版式尽量贴近原插件
- 提示词收紧为 OneCat / Sunny Duck 口播风格
- 加入匿名同段统计，用于 ARPI、gap、重合度

## 不包含的内容

- 原始字幕
- 本地数据库
- 私有 bot 运行环境
- 生产环境缓存文件

## 使用建议

发布到仓库后，用户只需要把整个 skill 目录放进 Codex 可发现的位置，或者直接使用 zip 包。

如果想更新发布包，重新执行：

```powershell
Compress-Archive -Path .\analyze-b50 -DestinationPath .\analyze-b50.zip -Force
```

## 注意事项

- `assets/cache/covers/` 是运行时缓存，发布时不建议保留
- `tmp/` 仅用于本地测试
- 由于水鱼接口返回内容会变化，输出图中的部分字段可能因账号数据不同而略有差异

## 版本定位

这是一个可直接开源发布的 skill 包，不是原插件源码仓库的镜像。
