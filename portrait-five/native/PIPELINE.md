# 一条入口，分阶段复跑

先从官网领取本人对应版本 `.motion`，准备带原声的视频、当前文稿的原生参数和实际字幕。`examples/captions-bilingual-words.json` 是已审核 11.33 秒口播的完整 7 条格式样例，含中文逐词时间、英文对应翻译，无人物素材、账户或路径信息。现代图文和纸面透视示例使用 `examples/modern-captions.json`，其中三句英文译文与这两款原生样片一致。两份字幕都只对应该段原声；新稿须用真实 ASR/对齐结果和核对后的翻译，不能挪用示例词时。

从源码运行时，先在仓库根目录执行 `cd portrait-five`；安装后也可在安装器打印的任一技能目录执行。五种公开风格名统一为 `modern/paper/dark/character/poster`，旧名 `characters` 兼容。先用助手按原生合同准备本期 `params.json`；示例参数里的文稿与时间只用于对应审核片，不是任意新稿的通用参数。

```powershell
python native/pipeline.py --style dark --package "E:/Templates/dark-14.motion" --video "E:/MyVideo/presenter.mp4" --captions "E:/MyVideo/captions.json" --params "E:/MyVideo/params.json" --inputs "E:/MyVideo/inputs" --output "E:/MyVideo/output/native.mp4" --work "E:/MyVideo/work/native-001" --runtime-root "E:/MotionGitRuntime" --stage plan
```

命令使用官方入口验签、准备依赖、检查原声和逐词双语字幕、生成计划，并要求 `ready=true`、全文时间覆盖和足够的成片时长。它只打印私有日志位置。`--inputs` 可省略；提供时先复制额外图片等素材，再按 params 的相对文件名绑定主视频和字幕。同名文件必须内容完全一致，否则停止，保留原文件。

实际检查计划的内容、动作和字幕后，由已获授权的助手或用户继续：

```powershell
python native/pipeline.py --work "E:/MyVideo/work/native-001" --stage preview --approve-plan
python native/pipeline.py --work "E:/MyVideo/work/native-001" --stage render --approve-preview
```

第二条只在真正查看生成预览后执行。两种 approve 参数记录真实审核结果，不会凭旧样片静默跳过新计划/预览。已有明确的制作授权和认可效果时，助手可完成这些检查后继续，无需再增加用户确认关卡。流程按阶段恢复；素材/参数已变时另建 work，保留旧工程。

Node、npm、FFmpeg、ffprobe 不在 PATH 时，首次命令可分别添加 `--node`、`--npm`、`--ffmpeg`、`--ffprobe` 的完整可执行文件路径。Node 必须带 npm。依赖放在指定 runtime-root，复跑继续复用；TEMP 位于本期 work。若仅漏配 npm，resume 允许补 `--npm` 路径。

导出会自动核对 1080×1920、60fps、计划帧数、音轨和完整解码，保存 MP4 与旁边的 `.verification.json`。这些技术检查之后，助手仍需检查最终编码画面和听感；不会把技术通过称作整套原作全部动作验收。

安装全部五个技能只需从仓库的 `portrait-five` 目录运行一次 `python scripts/install.py --dest "E:/YourCodexHome/skills"`，不传 `--style` 即安装全部。安装器会把 native、脚本和示例一起放入每个技能；每个已安装技能都可独立运行以上相对路径。本人模板、输入媒体及工作日志不打包。
