---
name: motiongit-poster
description: 使用 adunext 的 624 号「活力海报」9:16 模板剪口播。用渐变大字、关键词和引语框突出观点。适用于本风格的审核版复剪、作者原生场景和新素材制作。
---

# 活力海报 · 竖屏口播

需要本人领取的 624 号 `.motion`，版本 `2.7.18-alpha.8`。初次使用从[作者固定版本](https://motiongit.com/adunext/vibrant-poster-portrait/download/2.7.18-alpha.8)领取。环境准备见 安装说明 `docs/安装.md`。以下命令从安装后的本技能目录执行；在源码仓库内从 `portrait-five/` 执行。

本款审核片使用 title.slam、keyword.slam、quote.card。精确的镜头起止、文字、人物窗口、转场、字幕和口播对齐参数保存在 审核版镜头表 `examples/reviewed/poster.json`。

- 复剪同一段时，绑定与时间线对齐的人物视频和 WAV 原声，直接使用审核版镜头表。
- 换素材时，先根据新口播和核对过的字幕调整镜头时长、画面文字及 `narrationMap`。可用 `--init-timeline` 生成另一份可编辑示范。`duration` 应与本次要保留的口播时长一致。
- 保留本期原声及组件自带的动作音效。审核版没有另加背景音乐。
- 查看导出结果中间帧，核对字幕、人物裁切和动作，对照最终音轨确认所需声音。

```sh
python scripts/render.py --style poster --template "我的624.motion" --video "人物.mp4" --voice "原声.wav" --timeline examples/reviewed/poster.json --out "本次成片"
```

## 作者原生场景

原生样片使用 `06-A:check-glitch`、`06-A:making-card`，共 768 帧。请领取[作者固定原生版本 2.7.18-alpha.7](https://motiongit.com/adunext/vibrant-poster-portrait/download/2.7.18-alpha.7)。先生成纹理、首段所用人物视频，以及为结尾动作留出时间的完整口播轨道。下面的辅助命令对应审核用的 11.33 秒口播。

```sh
python native/examples/prepare_poster.py "原口播.mp4" poster-inputs
python native/pipeline.py --style poster --package "我的624-原生.motion" --video poster-inputs/talk-with-outro.mp4 --inputs poster-inputs --captions native/examples/captions-bilingual-words.json --params native/examples/poster.json --work poster-job --output native-poster.mp4
```

查看计划中的动作、文案和时长后生成预览；核对预览的人物裁切、字幕和转场后导出。

```sh
python native/pipeline.py --work poster-job --stage preview --approve-plan
python native/pipeline.py --work poster-job --stage render --approve-preview
```

换素材时，按实际原声重新对齐中英字幕和逐词时间，更新 `brief.contentEvidence` 的全文、摘要和分段引用，并按各段时长调整 `durationFrames` 和动作锚点。更多场景可从已验签包读取 `capacity-matrix.json` 与 `params.schema.json`。原生流程 `native/README.md`
