---
name: motiongit-paper
description: 使用 adunext 的 608 号「纸面透视」9:16 模板剪口播。用纸色引语卡、墨绿提示卡和翻面问答拆解方法。适用于本风格的审核版复剪、作者原生场景和新素材制作。
---

# 纸面透视 · 竖屏口播

审核版复剪使用本人领取的 608 号 `2.7.18-alpha.15` 包。[领取审核版所用版本](https://motiongit.com/adunext/template-02-expanded-portrait/download/2.7.18-alpha.15)。环境准备见 安装说明 `docs/安装.md`。以下命令从安装后的本技能目录执行；在源码仓库内从 `portrait-five/` 执行。

本款审核片使用 quote.card、tip.card、qa.flip。精确的镜头起止、文字、人物窗口、转场、字幕和口播对齐参数保存在 审核版镜头表 `examples/reviewed/paper.json`。

- 复剪同一段时，绑定与时间线对齐的人物视频和 WAV 原声，直接使用审核版镜头表。
- 换素材时，先根据新口播和核对过的字幕调整镜头时长、画面文字及 `narrationMap`。可用 `--init-timeline` 生成另一份可编辑示范。`duration` 应与本次要保留的口播时长一致。
- 保留本期原声及组件自带的动作音效。审核版没有另加背景音乐。
- 查看导出结果中间帧，核对字幕、人物裁切和动作，对照最终音轨确认所需声音。

```sh
python scripts/render.py --style paper --template "我的608.motion" --video "人物.mp4" --voice "原声.wav" --timeline examples/reviewed/paper.json --out "本次成片"
```

## 作者原生剪法

领取 [608 原生试剪所用的 .14 版](https://motiongit.com/adunext/template-02-expanded-portrait/download/2.7.18-alpha.14)。原生参数 `native/examples/paper.json`把整段口播绑定到 `02-P:question-progress-punch`，依次播放纸面提问、进度卡和墨色收尾。对应的七条双语字幕和中文逐词时间见试剪用字幕 `native/examples/modern-captions.json`。这一个场景只需要人物视频和字幕，口播音轨取自视频。

按原生流程 `native/PIPELINE.md`执行，风格设为 `--style paper`，用本款参数和字幕路径替换示例命令中的参数。新稿需要对照实际原声，另存本期字幕、文稿、内容依据和动作时间点。进度卡在此例中表示本期口播进度，换稿时要明确百分比所指。

```sh
python native/pipeline.py --style paper --package "我的608-原生.motion" --video "原口播.mp4" --captions native/examples/modern-captions.json --params native/examples/paper.json --work paper-job --output native-paper.mp4 --stage plan
```

检查计划中的文稿、时长和动作后生成预览；核对预览的人物、字幕和动作后导出。

```sh
python native/pipeline.py --work paper-job --stage preview --approve-plan
python native/pipeline.py --work paper-job --stage render --approve-preview
```
