# 五款竖屏口播技能

用 adunext 发布的五款 9:16 模板制作 1080×1920、60 fps 口播。每款技能都有一份审核版镜头表，保存出场时刻、字幕、镜头文案、人物窗口、配色和转场。导出使用领取者本人的固定版本模板，自带动作和音效由作者提供的工具渲染。

| 技能 | 命令中的风格名 | 审核版镜头 | 审核版个人包 | 原生场景个人包 |
| --- | --- | --- | --- | --- |
| 现代图文 | `modern` | definition.dictionary、compare.panels | [606 · alpha.15](https://motiongit.com/adunext/template-01-integrated-portrait/download/2.7.18-alpha.15) | [alpha.14](https://motiongit.com/adunext/template-01-integrated-portrait/download/2.7.18-alpha.14) |
| 纸面透视 | `paper` | quote.card、tip.card、qa.flip | [608 · alpha.15](https://motiongit.com/adunext/template-02-expanded-portrait/download/2.7.18-alpha.15) | [alpha.14](https://motiongit.com/adunext/template-02-expanded-portrait/download/2.7.18-alpha.14) |
| 深色立体 | `dark` | title.split、keyword.focus、compare.panels | [610 · alpha.15](https://motiongit.com/adunext/template-03-native-portrait/download/2.7.18-alpha.15) | [alpha.14](https://motiongit.com/adunext/template-03-native-portrait/download/2.7.18-alpha.14) |
| 鲜色角色 | `character` | title.split、kinetic.wave、chat.thread | [614 · alpha.15](https://motiongit.com/adunext/template-05-native-portrait/download/2.7.18-alpha.15) | [alpha.14](https://motiongit.com/adunext/template-05-native-portrait/download/2.7.18-alpha.14) |
| 活力海报 | `poster` | title.slam、keyword.slam、quote.card | [624 · alpha.8](https://motiongit.com/adunext/vibrant-poster-portrait/download/2.7.18-alpha.8) | [alpha.7](https://motiongit.com/adunext/vibrant-poster-portrait/download/2.7.18-alpha.7) |

### 用已导出的原生场景开始

| 风格 | 原生示例 | 复剪命令与对应字幕 |
| --- | --- | --- |
| 现代图文 | 概要卡 `01-D:basic-summary` | [现代图文用法](https://github.com/fagezhuanshu-lang/tech-console-video-workflow/blob/main/portrait-five/skills/motiongit-modern/SKILL.md) |
| 纸面透视 | 透视提问与进度卡 `02-P:question-progress-punch` | [纸面透视用法](https://github.com/fagezhuanshu-lang/tech-console-video-workflow/blob/main/portrait-five/skills/motiongit-paper/SKILL.md) |
| 深色立体 | 总结场景 `03-X:universal-summary` | [深色立体用法](https://github.com/fagezhuanshu-lang/tech-console-video-workflow/blob/main/portrait-five/skills/motiongit-dark/SKILL.md) |
| 鲜色角色 | 总结场景 `05-A:universal-summary` | [鲜色角色用法](https://github.com/fagezhuanshu-lang/tech-console-video-workflow/blob/main/portrait-five/skills/motiongit-character/SKILL.md) |
| 活力海报 | 故障勾选、制卡 `06-A:check-glitch` → `06-A:making-card` | [海报用法](https://github.com/fagezhuanshu-lang/tech-console-video-workflow/blob/main/portrait-five/skills/motiongit-poster/SKILL.md) |

上表覆盖六个已用真人口播导出的原生场景。更多动作的输入要求可从个人包中读取，已知的场景组合问题列在[原生实测记录](native/KNOWN-ISSUES.md)。

## 从仓库链接开始

1. 从 GitHub 仓库首页选择 **Code → Download ZIP** 并解压，或用 Git 克隆。首次从表中领取想使用的模板并保存在本机。相同版本的个人包因签发给不同用户而有所不同。
2. 安装 Python 3.12、Node.js 22.12 或以上及 npm、带 libx264 的 FFmpeg 和 ffprobe，将它们加入 PATH。首次准备官方渲染依赖需要联网。完整步骤见[安装说明](docs/安装.md)。
3. 在解压后的仓库根目录运行以下两条命令。安装器会打印各技能的安装位置。

```sh
python portrait-five/scripts/bootstrap.py doctor
python portrait-five/scripts/install.py
```

重开剪辑助手的会话，提供模板、素材及已核对的口播时间轴。例如：“用纸面透视剪我的口播，开头引用观点，中段做提示卡，结尾翻面回答问题。按我的原声对齐字幕。”

## 先跑一个镜头样例

在仓库的 `portrait-five` 目录，或安装器打印的某款技能目录中执行。以下例子使用纸面透视。自测程序生成彩条人物占位和短测试音，便于确认一台新电脑能渲染图层、字幕和音轨。要对照原样片，可在同一指令中换回原口播的两份媒体。

```sh
python examples/make_inputs.py demo-input
python scripts/render.py --style paper --template "我的608.motion" --video demo-input/presenter.mp4 --voice demo-input/voice.wav --timeline examples/reviewed/paper.json --out paper-check
```

运行其他风格时同时替换 `--style`、`--template` 和 `--timeline`。审核镜头表的时长是 11.33 秒，适合做同一段内容的回放。做新片前，按实际口播重新对齐镜头、字幕和每个画面里的文字。下面的命令生成可编辑的新片示例。

```sh
python scripts/render.py --style paper --init-timeline new-paper.json
```

## 作者场景

现代图文、纸面透视、深色立体和鲜色角色使用作者的 `motion-kit` 组件流程；活力海报使用 `poster-kit`。使用表格最后一列的历史版个人包，可以进入作者的原生编排流程。需要这些场景时，按[原生工作流说明](native/README.md)调用对应的参数合同和官方工具。当前完整还原的验证范围见[实测结果](docs/验证.md)。

原生海报的复剪示例用两个原作场景，分别占 440 和 328 帧。先从原 11.33 秒口播生成画面素材；辅助脚本复用完整原声，在末尾补 1.47 秒静止画面与静音，使结尾动作完整。

```sh
python native/examples/prepare_poster.py "原口播.mp4" poster-inputs
python native/pipeline.py --style poster --package "我的海报-alpha.7.motion" --video poster-inputs/talk-with-outro.mp4 --inputs poster-inputs --captions native/examples/captions-bilingual-words.json --params native/examples/poster.json --work poster-job --output native-poster.mp4
```

此命令生成可检查的计划。在同一个工程中按[原生流程](native/README.md)预览、复核后导出。仓库提供的七句字幕属于审核口播，换稿时需要换成对应录音的实际字幕和词级时码。

## 来源与使用范围

镜头安排及接入代码由本仓库提供。模板由各使用者从 [adunext 作者主页](https://motiongit.com/adunext)领取。官网说明允许按模板许可制作和发布视频，搬运、转售模板包或源码需另获授权。仓库的 [MIT 许可](LICENSE)适用于本仓库的工作流代码。
