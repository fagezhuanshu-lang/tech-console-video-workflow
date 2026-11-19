"""Render a portrait video using a verified MotionGit personal template."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import native
from poster import render_poster
from presets import RELEASE_HASHES, STYLES, example


def render_motion(entry, package, instance, logs, cache, timeline, video, voice, language):
    timeline = timeline.get("timeline", timeline)
    prefix = [*entry, "run", str(package), "--instance", str(instance), "--cache", str(cache)]
    def stage(action, *args, log_name=None):
        command = [*prefix, action, *map(str, args), "--language", language]
        return native.private_run(command, logs, log_name or action)
    try:
        doctor = native.read(stage("doctor", "--workflow", "motion-kit"))
        native.require(doctor.get("status") == "dependencies-verified", "Dependencies are missing")
    except (ValueError, RuntimeError):
        stage("setup", "--workflow", "motion-kit")
        doctor = native.read(stage("doctor", "--workflow", "motion-kit", log_name="doctor-after-setup"))
        native.require(doctor.get("status") == "dependencies-verified", "Motion-kit setup incomplete")
    inputs = instance / "inputs"
    media = inputs / "media"
    media.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(video, media / "presenter.mp4")
    shutil.copyfile(voice, media / "voice.wav")
    params = instance / "params.json"
    native.save(params, {"workflow": "motion-kit", "timeline": timeline})
    plan, project = instance / "plan", instance / "project"
    stage("plan", params, "--inputs", inputs, "--out", plan)
    native.review_plan(plan, timeline, video)
    stage("prepare", "@vault", "--inputs", "@vault", "--plan", plan, "--out", project)
    stage("preview", project, "--times", native.preview_times(timeline))
    native.review_preview(project, timeline)
    target = instance / "film.mp4"
    stage("render", project, "--out", target)
    report = native.read(project / "render.json")
    native.require(native.digest(target) == report["outputSha256"], "Rendered MP4 checksum mismatch")
    return target


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", required=True, choices=STYLES)
    for key in ("template", "video", "voice", "timeline", "captions", "out", "cache", "init-timeline"):
        parser.add_argument("--" + key, type=Path)
    parser.add_argument("--language", choices=("zh","en"), default="zh")
    parser.add_argument("--allow-voice-trim", action="store_true",
                        help="Allow the timeline to use only the beginning of a longer voice file")
    for tool in ("node", "ffmpeg", "ffprobe"):
        parser.add_argument("--" + tool, default=tool)
    return parser.parse_args()


def run(args):
    if args.init_timeline:
        native.require(not args.init_timeline.exists(), "Choose a new timeline filename")
        native.save(args.init_timeline, example(args.style))
        return
    for name in ("template", "video", "voice", "timeline"):
        value = getattr(args, name)
        native.require(value and value.is_file(), f"Supply an existing --{name} file")
    native.require(args.out, "Supply a new output directory with --out")
    settings = STYLES[args.style]
    params = native.read(args.timeline)
    timeline = params.get("timeline", params)
    native.require(timeline.get("layout") == "portrait" and timeline.get("duration", 0) > 0,
                   "Expected a portrait timeline with a positive duration")
    native.require(timeline.get("segments") and timeline.get("narrationMap"), "Missing shots or narrationMap")
    if args.captions:
        timeline["captions"] = native.read(args.captions)
    native.require(timeline.get("captions"), "Supply timed captions")
    native.require(timeline["presenter"]["src"] == "media/presenter.mp4" and timeline["voiceover"] == "media/voice.wav"
                   and not timeline.get("music"), "Use the reviewed presenter and voice slots, with no additional music")
    timeline["language"] = args.language
    tools = {}
    for name in ("node", "ffmpeg", "ffprobe"):
        resolved = shutil.which(getattr(args, name))
        native.require(resolved, f"Missing executable: {name}")
        tools[name] = str(Path(resolved).resolve())
    os.environ["PATH"] = os.pathsep.join([*(str(Path(p).parent) for p in tools.values()),os.environ.get("PATH","")])
    package, video, voice = (p.resolve() for p in (args.template, args.video, args.voice))
    voice_info = json.loads(subprocess.check_output([tools["ffprobe"], "-v","error","-select_streams","a:0",
                            "-show_entries","stream=codec_type:format=duration","-of","json",str(voice)]))
    native.require(voice_info.get("streams"), "Voice input has no audio stream")
    voice_seconds = float(voice_info["format"]["duration"])
    native.require(args.allow_voice_trim or voice_seconds <= timeline["duration"] + 0.05,
                   "Timeline ends before the voice file. Extend the timing or explicitly use --allow-voice-trim.")
    out = native.make_private_dir(args.out)
    work = out / "work"
    work.mkdir()
    cache = native.configure_environment(args.cache or work / "cache")
    logs = work / "private-logs"
    entry = [tools["node"], str(native.verify_helper(package, work))]
    verified = native.read(native.private_run([*entry, "start", str(package), "--summary"],logs,"start"))
    native.require(verified.get("verified") is True, "MotionGit signature check failed")
    instance = work / "instance"
    created = native.read(native.private_run([*entry, "new", str(package), str(instance)],logs,"new"))
    expected = settings["slug"] + "@" + settings["version"]
    native.require(created.get("template") == expected and created.get("templateId") == settings["id"],
                   f"Use template {settings['id']}, version {settings['version']}")
    native.require(created.get("releaseArchiveSha256") == RELEASE_HASHES[args.style],
                   "The signed release differs from the reviewed version")
    native.require(Path(created["instanceDirectory"]).resolve() == instance, "Unexpected instance path")
    render = render_poster if args.style == "poster" else render_motion
    result = render(entry, package, instance, logs, cache, timeline, video, voice, args.language)
    data = json.loads(subprocess.check_output([tools["ffprobe"], "-v","error","-of","json","-show_entries",
               "stream=codec_type,width,height,avg_frame_rate,nb_frames,duration", str(result)]))
    picture = next(s for s in data["streams"] if s["codec_type"] == "video")
    native.require((picture["width"],picture["height"],picture["avg_frame_rate"]) == (1080,1920,"60/1")
                   and abs(int(picture["nb_frames"])-timeline["duration"]*60) <= 1,
                   "Unexpected output dimensions, frame rate or duration")
    native.require(any(s["codec_type"] == "audio" for s in data["streams"]), "Missing output audio")
    subprocess.run([tools["ffmpeg"], "-nostdin", "-v","error","-xerror","-i",str(result),"-f","null","-"],check=True)
    checksum = native.digest(result)
    native.save(out/"verification.json",dict(template=expected,template_id=settings["id"],workflow=settings["workflow"],
                sha256=checksum,streams=data["streams"],fully_decoded=True))
    os.replace(result,out/"video.mp4")
    print(out/"video.mp4")


if __name__ == "__main__":
    try:
        run(arguments())
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit(f"Render failed: {exc}")
