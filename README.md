# 竖屏口播剪辑技能

[安装五款竖屏技能](portrait-five/README.md) · [原作者场景入口](portrait-five/native/README.md) · [复剪验证](portrait-five/docs/验证.md)

**现代图文、纸面透视、深色立体、鲜色角色、活力海报**各有独立技能，可替换人物、原声和字幕。五份审核版镜头表和原作者场景的运行入口都在 `portrait-five/`。

**首次使用**，下载整份仓库，在仓库根目录运行安装命令，再从安装页表格领取所选风格、对应模式的个人模板。审核版与原生场景使用不同的固定版本，可按需要分别领取。

```sh
python portrait-five/scripts/install.py
```

安装后可以告诉助手：“用纸面透视剪这段口播，保留我的原声，按说话时刻对齐字幕。” 要使用作者场景，可说：“用纸面透视的原生场景，先给我看镜头预览。” [查看环境要求、个人模板和自测命令](portrait-five/README.md)

## 612 科技控制台

用 adunext 的 MotionGit **612 号原模板**制作 1080×1920、60 fps 中文口播。一次选定本期的真人素材、原声、字幕和镜头表，再决定要哪种成片。

| 我想要的效果 | 模式 | 最终得到什么 |
| --- | --- | --- |
| 和已认可的试片一样 | **认可版**，默认 | 612 的镜头与动作音效，首帧深蓝人物封面，人声与指定 BGM 的混音。另交 9:16、3:4 两张封面。 |
| 看作者模板本身的效果 | **原作者模板直出**，`--mode native` | 直接交付官方渲染器生成的 MP4，保留原生首帧、原声和动作音效。交付时核对整份 MP4 的校验值。 |

**第一次使用**，请用自己的 MotionGit 账号领取 **2.7.18-alpha.14** 个人包，并保存到本机。GitHub 提供工作流、镜头预设和认可版封面源码。[免费领取固定版本](https://motiongit.com/adunext/template-04-dark-console-portrait/download/2.7.18-alpha.14) · [作者模板说明与预览](https://motiongit.com/adunext/template-04-dark-console-portrait)

## 交给剪辑助手

下载整份仓库，将个人模板、口播视频和校对好的字幕交给能运行本地程序的助手。以下两句话任选其一。

> 读取 SKILL.md，按认可版剪。使用我指定的配乐，制作深蓝人物标题封面。如果缺音乐，告诉我缺哪个文件。

> 读取 SKILL.md，用原作者模板直出。沿用本期镜头和字幕，把作者渲染出的原始 MP4 交给我。

WorkBuddy 或其他助手需要能访问本地素材和运行命令。同一份字幕、镜头表和封面配置可交给不同助手复用。换文稿或重选人物帧会改变结果。

## 本地运行

已验证环境为 Windows、Python 3.12、Node.js 24、FFmpeg/ffprobe 9，认可版封面使用系统微软雅黑。安装 Python 3.11 以上、Node.js 22.12 以上及 npm、带 libx264 的 FFmpeg 和 ffprobe，将它们放入 PATH。首次调用官方模板需联网核验随包工具并检查依赖。认可版首次运行会使用 npm 安装封面依赖，也可预先执行 `npm ci --prefix cover`。Windows 若出现 WinError 206，可在当前终端为本次运行选择较短的可写 LOCALAPPDATA 路径。

在仓库根目录执行命令，给每次导出选择新的输出目录。用自己的内容时，将 `examples/story.json` 复制为本期镜头表。`throughCaption` 是每个镜头包含的最后一条字幕序号，从 1 开始。`duration` 是本次保留的原视频开头时长，取 30 fps 的整帧数。motion-kit 路线支持 5 至 600 秒。镜头表支持 `title` 分栏标题、`keyword` 关键词和 `quote` 引语。

### 认可版（默认）

按 `examples/cover.json` 填写两行短标题、观点和真人选帧时间。`crop` 是源画面的像素裁切框，可省略以使用居中裁切。

```sh
python run.py --template "我的612.motion" --source "口播.mp4" --srt "字幕.srt" --story "本期镜头.json" --cover-brief "本期封面.json" --music "指定配乐.m4a" --out "认可版"
```

`--music` 读入原曲并制作音床，`--music-start` 指定这份文件中的起播位置。`--bed "音床.wav"` 使用已经调好、从零秒对齐的音床。只有选用随包原创教学配乐时才传 `--demo-music`。样片的本地曲目 202B94 从文件零秒起播，旧工程中的 29.16 秒是完整母带上的位置。

### 原作者模板直出

沿用同一份视频、字幕和镜头表，保留 612 渲染器给出的首帧和音轨。无需准备封面配置和配乐。

```sh
python run.py --mode native --template "我的612.motion" --source "口播.mp4" --srt "字幕.srt" --story "本期镜头.json" --out "作者直出"
```

两种模式都交付 `video.mp4`、`captions.srt` 和 `verification.json`。认可版还会生成 `cover/cover-9x16.jpg` 与 `cover/cover-3x4.jpg`。工作目录 `work/` 可能包含私人实例资料，只留在本机。[来源和音乐权限](references/rights.md)

## 安装自测和原样片复验

以下自测会生成可重用的动态图案和测试音，使用真正的 612 原模板导出。这里选用原创教学配乐来测试认可版的混音。

```sh
python examples/make_fixture.py "测试素材.mp4"
python run.py --mode native --template "我的612.motion" --source "测试素材.mp4" --srt examples/check.srt --story examples/check-story.json --out "自测直出"
python run.py --template "我的612.motion" --source "测试素材.mp4" --srt examples/check.srt --story examples/check-story.json --cover-brief examples/check-cover.json --demo-music --out "自测认可版"
```

已持有原样片素材时，`--original` 载入固定的 7 句字幕、3 个镜头与 11.33 秒时间轴。它可与任一输出模式组合。

```sh
python run.py --mode native --original --template "我的612.motion" --source "20261106.mp4" --out "原样片直出"
python run.py --original --template "我的612.motion" --source "20261106.mp4" --music "202B94.m4a" --out "原样片认可版"
```

从模板新建实例可能产生轻微画面像素差异。要对认可版做逐字节复验，可将最后一条命令的 `--template "我的612.motion"` 替换为 `--native-render "已确认的612原生输出.mp4" --verify-original`，并使用相同素材、字体和编码环境。[查看两种模式的核验基准](references/verification.md)


