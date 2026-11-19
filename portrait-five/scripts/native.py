"""Verify a personal MotionGit package and call its published rendering tools.

This module contains workflow glue, not the vendor's protected template.
Derived from the public tech-console-video-workflow v1.1.0 helper.
"""
import argparse
import csv
import hashlib
import json
import os
import re
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


def read(path, which="first"):
    """Read JSON data or the first/last complete top-level JSON in a CLI log."""
    data = Path(path).read_text(encoding="utf-8-sig")
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        pass
    decoder, found, consumed = json.JSONDecoder(), [], 0
    for match in re.finditer(r"(?m)^[ \t]*[\[{]", data):
        offset = match.end() - 1
        if offset < consumed:
            continue
        try:
            value, length = decoder.raw_decode(data[offset:])
        except json.JSONDecodeError:
            continue
        found.append(value)
        consumed = offset + length
    require(found, f"No complete JSON result in {path}")
    require(which in ("first", "last"), "which must be first or last")
    return found[0 if which == "first" else -1]


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def digest(path):
    with Path(path).open("rb") as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def make_private_dir(path):
    """Create a new private directory; never change permissions of an existing one."""
    path = Path(path).resolve()
    require(not path.exists(), f"Choose a new private work directory: {path}")
    path.mkdir(mode=0o700, parents=True)
    if os.name == "nt":
        result = subprocess.check_output(["whoami", "/user", "/fo", "csv", "/nh"], text=True)
        sid = next(csv.reader(result.splitlines()))[1]
        require(re.fullmatch(r"S-1-[0-9-]+", sid), "Cannot identify current Windows user")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"],
                       check=True, stdout=subprocess.DEVNULL)
    return path


def configure_environment(cache):
    """Keep subprocess caches below the chosen path, without changing OS settings."""
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for name in ("tmp", "ms-playwright", "local"):
        (cache / name).mkdir(exist_ok=True)
    os.environ.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    for key in ("TEMP", "TMP", "TMPDIR"):
        os.environ.setdefault(key, str(cache / "tmp"))
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(cache / "ms-playwright"))
    if os.name == "nt":
        os.environ.setdefault("LOCALAPPDATA", str(cache / "local"))
    return cache


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def verify_helper(package, folder):
    package, folder = Path(package), Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
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
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    require(re.fullmatch(r"[A-Za-z0-9_.-]+", name), "Invalid log name")
    logfile = folder / (name + ".log")
    print("MotionGit: " + name, file=sys.stderr, flush=True)
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    temp = folder.parent / "tmp"
    temp.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temp.resolve()), TMP=str(temp.resolve()), TMPDIR=str(temp.resolve()))
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
    plan = Path(plan)
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
    project = Path(project).resolve()
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
                require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II",header[16:24]) == (1080, 1920),
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



