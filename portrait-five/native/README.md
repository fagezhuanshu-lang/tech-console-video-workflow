# 五款官方原生入口

从仓库根目录进入 `portrait-five`，或在安装器打印的技能目录执行下列命令。五款审核版使用各自的组件流程。要调用原作场景，请选择已验证的历史版本。每款已导出的动作、帧数与样片摘要见 [验证结果](VERIFICATION.json)，未通过的版本和动作列在 [已知问题](KNOWN-ISSUES.md)。

学员从 [模板清单](templates.json) 的官网地址自行领取本人 `.motion`。这里只分发调用代码和说明，不含个人模板、凭据、原作者保护核心或真人素材。官方 GitHub 的五个仓库目前提供文档与 Demo，未发现可直接运行的公开源码包。

新制作优先用 [pipeline.py 分阶段入口](PIPELINE.md)：同一命令处理素材、依赖、计划、预览、渲染和解码验收，支持断点继续。先生成并检查计划，随后检查预览再导出：

```powershell
python native/pipeline.py --style dark --package "E:/Templates/dark-14.motion" --video "E:/MyVideo/presenter.mp4" --captions "E:/MyVideo/captions.json" --params "E:/MyVideo/params.json" --inputs "E:/MyVideo/inputs" --output "E:/MyVideo/output/native.mp4" --work "E:/MyVideo/work/native-001" --stage plan
python native/pipeline.py --work "E:/MyVideo/work/native-001" --stage preview --approve-plan
python native/pipeline.py --work "E:/MyVideo/work/native-001" --stage render --approve-preview
```

审核参数由实际看过本期计划和预览的用户或已获授权助手设置；已有授权下助手可自行完成这些检查。Node/npm/FFmpeg 不在 PATH 时的选项，以及完整 7 条双语词时格式样例，见配套说明。

准备 Python 3.12+、Node.js 22+（带 npm），以及官方 doctor 指明的 FFmpeg、浏览器与 Python 依赖。原生色彩转换要求 FFmpeg 9+ 的相应 libswscale 能力；版本号满足仍须 doctor 验证。已有依赖可复用，按官方 setup 补缺项。

以深色立体为例；`--work` 必须是尚不存在的新目录。路径按自己的电脑修改。模板名可选 `modern`、`paper`、`dark`、`character`（兼容旧名 `characters`）、`poster`。

```powershell
python native/run.py --template dark --package "E:/Templates/my-dark.motion" --work "E:/Projects/dark-001" init
python native/run.py --work "E:/Projects/dark-001" read guide.json
python native/run.py --work "E:/Projects/dark-001" read NATIVE-INPUTS.md
python native/run.py --work "E:/Projects/dark-001" read params.schema.json
python native/run.py --work "E:/Projects/dark-001" read capacity-matrix.json
python native/run.py --work "E:/Projects/dark-001" read adapter/parameter-map.json
python native/run.py --work "E:/Projects/dark-001" run doctor --language zh
```

读取结果只存于命令显示的本机私有日志，供本人和助手检查，不原样打印或提交到仓库。init 校验官网公布的 helper 大小与 SHA256，再由官方工具验签并核对模板 ID、明确列出的版本锁和竖屏尺寸。前四款允许 .15/.14，海报允许 .8/.7；接受初始化不等于该版已出片，具体测试范围见 nativeVersions 和验证结果。实例记录并打印实际版本；不同版本使用新工程。

doctor 通过后，按 [执行步骤](WORKFLOW.md) 创建本期原生参数。若 doctor 指出缺依赖，可调用 `run setup --language zh` 后复验；路径校验拒绝时停止该阶段，不能以组件输出代替原生验收。此入口不会自动修改计划或预览的审核标记，也不会自动上传内容。
