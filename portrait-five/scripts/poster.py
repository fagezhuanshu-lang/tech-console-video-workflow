"""Render the reviewed 624 layout using the author's poster-kit workflow."""
import json
import shutil
import sys
from pathlib import Path

from native import digest, preview_times, private_run, read, require, save


def render_poster(entry, package, instance, logs, cache, timeline, video, voice, language):
    instance = Path(instance).resolve()
    timeline = timeline.get("timeline", timeline)
    media = instance / "media"
    media.mkdir(exist_ok=True)
    shutil.copyfile(video, media / "presenter.mp4")
    shutil.copyfile(voice, media / "voice.wav")
    parameters = instance / "timeline.json"
    save(parameters, timeline)
    prefix = [*entry, "run", str(package), "--instance", str(instance)]
    if cache:
        prefix += ["--cache", str(cache)]

    def stage(action, *args):
        command = [*prefix, action, "--workflow", "poster-kit", *map(str, args), "--language", language]
        return read(private_run(command, logs, action))

    ready = stage("setup")
    require(ready.get("workflow") == "poster-kit" and ready.get("dependenciesReady") is True,
            "Poster dependencies are not ready")
    plan = instance / "poster-plan"
    preview = instance / "poster-preview"
    stage("plan", "--timeline", parameters, "--out", plan)
    plan_receipt = plan / "host-plan.json"
    receipt = read(plan_receipt)
    bound = set(receipt["inputFiles"].values())
    require(receipt["workflow"] == "poster-kit" and {digest(video), digest(voice)} <= bound,
            "The poster plan did not bind the supplied video and voice")
    receipt["reviewed"] = True
    save(plan_receipt, receipt)

    linked = ("--timeline", "@vault", "--plan", plan)
    stage("prepare", *linked, "--out", instance / "poster-project")
    stage("preview", *linked, "--out", preview, "--times", preview_times(timeline))
    review_file = preview / "preview-review.json"
    review = read(review_file)
    require(review["parametersSha256"] == receipt["parametersSha256"] and
            review["inputFiles"] == receipt["inputFiles"], "Preview does not match the plan")
    require(any(name.endswith(".png") for name in review["files"]), "Poster produced no preview images")
    for name, expected in review["files"].items():
        path = (preview / name).resolve()
        require(path.is_relative_to(preview) and digest(path) == expected, "Invalid preview file")
    geometry = read(preview / "geometry.json")
    if geometry.get("violations"):
        print(f"Check text margins in the poster preview: {preview / 'geometry.json'}", file=sys.stderr)
    review["reviewed"] = True
    save(review_file, review)

    target = instance / "poster.mp4"
    report = stage("render", *linked, "--preview-review", preview, "--out", target)
    export = report["exportVerification"]
    require(export["verifiedCopy"] and export["sha256"] == digest(target), "Invalid poster export hash")
    require(report["audioIntegrity"]["encodedMix"]["passed"], "Encoded poster audio failed its check")
    return target
