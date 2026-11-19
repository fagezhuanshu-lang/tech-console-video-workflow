"""Run the owner's verified MotionGit 612 package in a fresh private workspace."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

HELPER_SHA = "77dfe906b8cb6b2c766c89fcd7d4e2f2de049542d6fbd5b7b3465c16b9b2d1c6"
HELPER_SIZE = 898025
RELEASE_SHA = "11ad7d00aa8d9f62001de441a07d044cfc935b977a0a0c88bc1c98b423f75745"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    with path.open("rb") as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_helper(package, folder):
    opener = urllib.request.build_opener(NoRedirect())
    for host in ("https://motiongit.cn", "https://motiongit.com", "https://adudir.com/motiongit"):
        url = host + "/assets/motion-runtimes/1.0.0-rc.59.json"
        try:
            with opener.open(url, timeout=12) as response:
                require(response.geturl() == url, "Unexpected official metadata destination")
                meta = json.loads(response.read(16384))
            break
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
    else:
        raise ValueError("Official MotionGit helper metadata is unreachable. Retry with network access.")
    require(meta.get("sha256") == HELPER_SHA and meta.get("bytes") == HELPER_SIZE, "Official helper version mismatch")
    helper = folder / "motion.mjs"
    with zipfile.ZipFile(package) as archive:
        member = archive.getinfo("assistant/motion.mjs")
        require(member.file_size == HELPER_SIZE, "Package helper size mismatch")
        code = archive.read(member)
    require(hashlib.sha256(code).hexdigest() == HELPER_SHA, "Package helper checksum mismatch")
    helper.write_bytes(code)
    return helper


def private_run(command, folder, name):
    # The vendor's metadata/logs can identify the local account. Keep them outside the repository.
    logfile = folder / (name + ".log")
    print("MotionGit: " + name, file=sys.stderr, flush=True)
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    node_path = shutil.which(str(command[0]))
    tool_dirs = [str(Path(sys.executable).parent)]
    if node_path:
        tool_dirs.append(str(Path(node_path).parent))
    env["PATH"] = os.pathsep.join([*tool_dirs, env.get("PATH", "")])
    with logfile.open("wb") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        raise RuntimeError(f"MotionGit {name} failed; inspect the private log {logfile}")
    return logfile


def review_plan(plan, timeline, presenter):
    report = read(plan / "report.json")
    require(report.get("ready") and report.get("workflow") == "motion-kit", "Plan is not ready")
    require(report.get("layout") == "portrait" and abs(report["duration"] - timeline["duration"]) < 1/60,
            "Plan changed layout or duration")
    require(report.get("captionRows") == timeline["captions"], "Plan changed the submitted captions")
    alignment = report.get("narrationAlignment", {})
    require(alignment.get("timingCoverageVerified") and alignment.get("visualCoverage", {}).get("allSentencesMapped"),
            "Incomplete timed speech or shot coverage")
    require(any(b.get("role") == "presenter" and b.get("sha256") == digest(presenter)
                for b in report.get("mediaBindings", [])), "Presenter binding changed")
    require(not report.get("notes"), "Official plan includes unresolved notes")
    require(not report.get("narrationChoices", {}).get("composition", {}).get("missingChoices"), "Unresolved shot choices")
    receipt = read(plan / "review.json")
    receipt["reviewed"] = True
    save(plan / "review.json", receipt)


def preview_times(timeline):
    end = timeline["duration"] - 1/60
    times = {0, max(0, end)}
    for shot in timeline["segments"]:
        a, b = shot["t0"], shot["t1"]
        times.update([min(b-1/60,a+.15), min(b-1/60,a+.6), (a+b)/2, max(a,b-.15)])
    for cap in timeline["captions"]:
        times.add((cap["s"] + cap["e"]) / 2)
    return ",".join(str(t) for t in sorted({round(max(0, min(t, end)), 3) for t in times}))

def review_preview(project, timeline):
    receipt = read(project / "preview.json")
    details = receipt["renderer"]
    require(not details.get("layoutDiagnostics") and receipt.get("stills"), "Missing stills or layout issues")
    for group in ("projectHashes", "stills"):
        for relative, expected in receipt[group].items():
            asset = (project / relative).resolve()
            require(asset.is_relative_to(project) and digest(asset) == expected, "Preview asset hash mismatch")
            if group == "stills":
                with asset.open("rb") as f:
                    header = f.read(24)
                require(header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II",header[16:24]) == (1080, 1920),
                        "Incorrect preview size")
    seen = set()
    for sample in details["captionSamples"]:
        displayed = {item["text"] for item in sample.get("items", [])}
        expected = {c["text"] for c in timeline["captions"] if c["s"]+.1 <= sample["time"] <= c["e"]-.1}
        require(expected <= displayed, "Timed subtitle changed")
        for item in sample.get("items", []):
            require(0 <= item["left"] < item["right"] <= 1080 and 0 <= item["top"] < item["bottom"] <= 1920
                    and not item.get("publishSafeArea", {}).get("hits"), "Caption crosses the canvas or safe area")
        seen.update(displayed)
    require({c["text"] for c in timeline["captions"]} <= seen, "An authored subtitle was not previewed")
    require(any(g.get("role") == "presenter" and g.get("width",0)>0 and g.get("height",0)>0
                for g in details.get("mediaGeometry", [])), "Presenter is missing in preview")
    receipt["reviewed"] = True
    save(project / "preview.json", receipt)


def render(args):
    package, work = args.package.resolve(), args.work.resolve()
    params = read(args.params)
    timeline = params["timeline"]
    require(params["workflow"] == "motion-kit" and timeline.get("layout") == "portrait", "Expected motion-kit portrait plan")
    require(timeline["presenter"]["src"] == "media/presenter.mp4" and timeline["voiceover"] == "media/voice.wav"
            and not timeline.get("music"), "Expected canonical media slots and an external music bed")
    require(timeline.get("captions") and timeline.get("segments") and timeline.get("narrationMap"), "Missing caption or visual plan")
    require(all(p.is_file() for p in (package, args.presenter, args.voice)), "Missing personal package or source media")
    require(not work.exists() or (work.is_dir() and not any(work.iterdir())), "Choose a fresh empty private work folder")
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    logs = work / "private-logs"
    logs.mkdir(mode=0o700)
    version = subprocess.check_output([args.node, "--version"], encoding="utf8")
    require(int(version.strip().lstrip("v").split(".")[0]) >= 22, "Install Node.js 22 or later")
    entry = [args.node, str(verify_helper(package, work))]
    start = read(private_run(entry + ["start", str(package), "--summary"], logs, "start"))
    require(start.get("verified") is True, "Package signature not verified")
    requested_instance = work / "instance"
    created = read(private_run(entry + ["new", str(package), str(requested_instance)], logs, "new"))
    require(created.get("templateId") == 612 and created.get("releaseArchiveSha256") == RELEASE_SHA
            and created.get("template") == "template-04-dark-console-portrait@2.7.18-alpha.14", "Signed edition differs")
    instance = Path(created["instanceDirectory"]).resolve()
    require(instance == requested_instance, "Helper selected a different private workspace")
    prefix = entry + ["run", str(package), "--instance", str(instance)]
    suffix = ["--language", "zh"] + (["--cache", str(args.cache.resolve())] if args.cache else [])
    def stage(name, *words):
        return private_run(prefix + [str(word) for word in words] + suffix, logs, name)
    try:
        doctor = read(stage("doctor", "doctor", "--workflow", "motion-kit"))
        require(doctor.get("status") == "dependencies-verified", "Missing dependencies")
    except (ValueError, RuntimeError):
        stage("setup", "setup", "--workflow", "motion-kit")
        doctor = read(stage("doctor-after-setup", "doctor", "--workflow", "motion-kit"))
        require(doctor.get("status") == "dependencies-verified", "Official dependency setup incomplete")

    inputs, plan, project = (instance / name for name in ("inputs", "plan", "project"))
    media = inputs / "media"
    media.mkdir(parents=True)
    shutil.copyfile(args.presenter, media / "presenter.mp4")
    shutil.copyfile(args.voice, media / "voice.wav")
    shutil.copyfile(args.params, instance / "params.json")
    stage("plan", "plan", instance / "params.json", "--inputs", inputs, "--out", plan)
    review_plan(plan, timeline, args.presenter)
    stage("prepare", "prepare", "@vault", "--inputs", "@vault", "--plan", plan, "--out", project)
    stage("preview", "preview", project, "--times", preview_times(timeline))
    review_preview(project, timeline)
    rendered = instance / "native.mp4"
    stage("render", "render", project, "--out", rendered)
    result = read(project / "render.json")
    checksum = digest(rendered)
    require(result.get("outputSha256") == checksum, "Final native render SHA-256 differs")
    encoder = result["renderer"]["encoded"]
    require((encoder["width"], encoder["height"], encoder["fps"], encoder["audio"]) == (1080,1920,60,True)
            and abs(encoder["frames"] - timeline["duration"] * 60) <= 1, "Native output geometry or duration differs")
    target = work / "native.mp4"
    os.replace(rendered, target)
    print(json.dumps({"native":str(target),"sha256":checksum,"frames":encoder["frames"],
                      "verified_template":612,"version":"2.7.18-alpha.14","technical_preview_review":True,
                      "artistic_review":False}, ensure_ascii=True))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("package", "params", "presenter", "voice", "work"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--node", default="node")
    ap.add_argument("--cache", type=Path, help="Existing or new private MotionGit dependency cache")
    try:
        render(ap.parse_args())
    except (ValueError, KeyError, OSError, RuntimeError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        ap.exit(1, f"Native build failed: {exc}\n")
