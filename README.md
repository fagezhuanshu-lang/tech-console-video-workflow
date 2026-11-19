# 科技控制台 · 竖屏口播

用 adunext 的 MotionGit **612 号原模板**剪一条 1080×1920、60 fps 的中文口播。这个版本固定了原版的三种镜头、青色深蓝人物封面、动作音效、人声和配乐混音。会同时导出 9:16 和 3:4 封面、字幕及核验报告。

**第一次使用请先领取模板。** 用自己的 MotionGit 账号登录，下载 **2.7.18-alpha.14**，把 `.motion` 放在自己的电脑上。官网为每个账号签发个人包。GitHub 提供工作流、原版预设和封面源码。[免费领取固定版本](https://motiongit.com/adunext/template-04-dark-console-portrait/download/2.7.18-alpha.14) · [官方模板介绍与预览](https://motiongit.com/adunext/template-04-dark-console-portrait)

## 交给剪辑助手

下载整份仓库，将个人模板、口播视频和校对好的字幕一起交给能运行本地程序的助手。可以直接发下面这段话。

> 读取这个仓库的 SKILL.md。用 612 号原模板剪我的视频，按我的字幕做三种科技控制台镜头，保留原声和动作音效，做深蓝人物封面。我指定音乐时用我的音源，否则用包内的原创教学配乐。请实际导出视频，检查声音、画面和两张封面后交付。

WorkBuddy 或其他助手需要能访问素材和运行本地命令。剪辑、封面和混音运行同一套脚本。模型根据新文稿选取的标题、人物帧和切点会影响观感；要让不同助手得到同一剪法，就共享同一份字幕、镜头表和封面配置。

## 本地使用

本次原样验收环境为 Windows、Python 3.12、Node.js 24、FFmpeg/ffprobe 9，封面使用系统微软雅黑。安装 Node.js 22.12 以上及 npm、Python 3.11 以上、带 libx264 的 FFmpeg 和 ffprobe，使它们进入 PATH。首次运行需要联网核验官方工具并准备组件。所有命令均在仓库根目录执行，路径含空格时保留引号。

```sh
npm ci --prefix cover
```

个人包的首次启动会核对官方签名和版本。缺少运行组件时，脚本调用官方 setup，再运行 doctor 检查。Windows 若出现 WinError 206，可在当前终端为本次运行选择较短的可写 LOCALAPPDATA 路径。此设置只影响当前终端。

**用自己的内容。** 把 `examples/story.json` 和 `examples/cover.json` 复制到本期目录。镜头表按字幕序号分组，`throughCaption` 是该镜头包含的最后一条字幕序号，从 1 开始。`duration` 是本次剪辑从原视频开头保留的秒数。本次 motion-kit 路线支持 5 至 600 秒，本流程人物素材按 30 fps 准备，时长取整帧（如 11 秒或 340/30 秒），最终模板输出 60 fps。三种镜头使用 `title`、`keyword`、`quote`。封面写两行短标题、观点及原片选帧时间，`crop` 是源画面像素坐标中的人物裁切框，可省略改为居中裁切。先预览确认。换新视频时需换成该视频的字幕、文案和选帧。

```sh
python run.py --template "我的612.motion" --source "口播.mp4" --srt "字幕.srt" --story "本期镜头.json" --cover-brief "本期封面.json" --music "已授权配乐.m4a" --out "本期成片"
```

`--music` 读入原曲并制作音床，`--music-start` 可设置这份文件中的起播位置。也可以把它换成 `--bed "已调好.wav"` 直接使用已经对齐的音床，或 `--demo-music` 现场生成随包的原创电子配乐。样片所选的本地曲目 202B94 从文件零秒起播；29.16 秒是上一个工程记录的完整母带定位，不能再给这个已选文件重复加偏移。

**检查安装。** 已经领取 612 的学员可以用下面两条命令自测。测试素材是动态图案与节拍声，普通电脑也可以重新生成。自测会调用真正的 612 模板、制作原版排版的双尺寸封面、加上原创教学配乐，并导出完整测试视频。

```sh
python examples/make_fixture.py "测试素材.mp4"
python run.py --template "我的612.motion" --source "测试素材.mp4" --srt examples/check.srt --story examples/check-story.json --cover-brief examples/check-cover.json --demo-music --out "安装自测"
```

**复验原样片。** 有相同原片和有权使用的同一音源时，以下命令按固定的 7 句字幕、3 个镜头及封面选帧制作 11.33 秒试片。也可用原音床替代原曲。实测同一台电脑从原模板新建实例，也会产生少量画面像素差异。需要逐字节交付原文件时，将下方的 `--template "我的612.motion"` 替换为 `--native-render "已确认的612原生输出.mp4" --verify-original`，并使用相同的源素材、字体和编码环境。核验记录见 [原版比对](references/verification.md)。

```sh
python run.py --original --template "我的612.motion" --source "20261106.mp4" --music "202B94.m4a" --out "原版复验"
```

在新的输出目录取 `video.mp4`、`captions.srt`、`cover/cover-9x16.jpg`、`cover/cover-3x4.jpg` 和 `verification.json`。调试用的 `work/` 可能包含私人实例资料，只留在自己电脑上。原曲、本人人像和个人账号的模板文件均由使用者本地提供。[来源和音乐权限](references/rights.md)

