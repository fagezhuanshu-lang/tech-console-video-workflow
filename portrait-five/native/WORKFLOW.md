# 原生制作步骤

本文件面向执行助手。先按每款 `guide.json`、`NATIVE-INPUTS.md`、`params.schema.json`、`capacity-matrix.json`、`adapter/parameter-map.json` 绑定真实素材，保留完整口播和实际字幕时间。不要把组件 `timeline` 参数交给原生入口。

原生参数由助手按所选动作组编排，放到工程的 `instance/params.json`，素材放 `instance/inputs/`。下面沿用 README 的工程路径；其他模板替换工程路径即可。官方入口默认使用原生路线，故不附加 `--workflow motion-kit` 或 `poster-kit`。

```powershell
python native/run.py --work "E:/Projects/dark-001" run check-params "E:/Projects/dark-001/instance/params.json" --inputs "E:/Projects/dark-001/instance/inputs" --language zh
python native/run.py --work "E:/Projects/dark-001" run plan "E:/Projects/dark-001/instance/params.json" --inputs "E:/Projects/dark-001/instance/inputs" --out "E:/Projects/dark-001/instance/plan" --language zh
```

检查计划中的内容依据、完整动作组、时间和素材裁切。确实通过后才按官方合同设置计划 `review.json` 的 `reviewed=true`。

```powershell
python native/run.py --work "E:/Projects/dark-001" run prepare @vault --inputs @vault --plan "E:/Projects/dark-001/instance/plan" --out "E:/Projects/dark-001/instance/project" --language zh
python native/run.py --work "E:/Projects/dark-001" run preview "E:/Projects/dark-001/instance/project" --times 0.5,2,4 --language zh
```

预览时间需根据实际镜头补充各转场和动作中段。查看生成帧，核对人物、文字、构图与声音；真实检查通过后才按合同设置预览 `preview.json` 的 `reviewed=true`。

```powershell
python native/run.py --work "E:/Projects/dark-001" run render "E:/Projects/dark-001/instance/project" --out "E:/Projects/dark-001/instance/video.mp4" --language zh
```

导出后再核对 1080×1920、60fps、帧数、原声完整性、全片解码、动作中段和声音同步。只有最终文件通过才记录原生出片成功。保留旧输出；修订使用新的 plan/project/output 路径。发布内容仅包含本人有权公开的成片与经过脱敏的制作记录，不上传 work 或个人 `.motion`。
