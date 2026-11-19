---
name: motiongit-dark
description: 使用 adunext 的 610 号「深色立体」9:16 模板剪口播。用深色舞台、蓝色关键词和上下对照介绍产品或案例。适用于本风格的审核版复剪、作者原生场景和新素材制作。
---

# 深色立体 · 竖屏口播

需要本人领取的 610 号 `.motion`，版本 `2.7.18-alpha.15`。初次使用从[作者固定版本](https://motiongit.com/adunext/template-03-native-portrait/download/2.7.18-alpha.15)领取。环境准备见 安装说明 `docs/安装.md`。以下命令从安装后的本技能目录执行；在源码仓库内从 `portrait-five/` 执行。

本款审核片使用 title.split、keyword.focus、compare.panels。精确的镜头起止、文字、人物窗口、转场、字幕和口播对齐参数保存在 审核版镜头表 `examples/reviewed/dark.json`。

- 复剪同一段时，绑定与时间线对齐的人物视频和 WAV 原声，直接使用审核版镜头表。
- 换素材时，先根据新口播和核对过的字幕调整镜头时长、画面文字及 `narrationMap`。可用 `--init-timeline` 生成另一份可编辑示范。`duration` 应与本次要保留的口播时长一致。
- 保留本期原声及组件自带的动作音效。审核版没有另加背景音乐。
- 查看导出结果中间帧，核对字幕、人物裁切和动作，对照最终音轨确认所需声音。

```sh
python scripts/render.py --style dark --template "我的610.motion" --video "人物.mp4" --voice "原声.wav" --timeline examples/reviewed/dark.json --out "本次成片"
```

## 作者原生场景

原生样片使用 `03-X:universal-summary`，共 680 帧。请领取[作者固定原生版本 2.7.18-alpha.14](https://motiongit.com/adunext/template-03-native-portrait/download/2.7.18-alpha.14)。此示例的七句字幕和场景参数对应审核用的 11.33 秒口播。

```sh
python native/pipeline.py --style dark --package "我的610-原生.motion" --video "原口播.mp4" --captions native/examples/captions-bilingual-words.json --params native/examples/dark.json --work dark-job --output native-dark.mp4
```

查看计划中的动作、文案和时长后生成预览；核对预览的人物裁切、字幕和转场后导出。

```sh
python native/pipeline.py --work dark-job --stage preview --approve-plan
python native/pipeline.py --work dark-job --stage render --approve-preview
```

换素材时，按实际原声重新对齐中英字幕和逐词时间，更新 `brief.contentEvidence` 的全文、摘要和分段引用，并按各段时长调整 `durationFrames` 和动作锚点。更多场景可从已验签包读取 `capacity-matrix.json` 与 `params.schema.json`。原生流程 `native/README.md`
