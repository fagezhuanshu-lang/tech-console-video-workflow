"""Finish a MotionGit 612 native render with the approved cover and prepared music bed."""
import argparse
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path
import subprocess
import tempfile


def command(*args):
    return subprocess.check_output([str(arg) for arg in args], encoding="utf-8", errors="replace")


def sha256(path):
    with path.open("rb") as f:
        digest = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def streams(path, ffprobe):
    return json.loads(command(ffprobe, "-v", "error", "-show_streams", "-of", "json", path))["streams"]


def stream(items, kind):
    for item in items:
        if item["codec_type"] == kind:
            return item
    raise ValueError(f"Missing {kind} stream")


def decoded_hashes(path, ffmpeg):
    return command(ffmpeg, "-v", "error", "-xerror", "-i", path, "-map", "0:v:0", "-map", "0:a:0",
                   "-f", "streamhash", "-hash", "sha256", "-").strip()


def finish(args):
    target = args.output.resolve()
    if target.exists():
        raise FileExistsError(f"Output already exists: {target}")
    for asset in (args.native, args.cover, args.music_bed):
        if not asset.is_file():
            raise FileNotFoundError(asset)
    source = streams(args.native, args.ffprobe)
    pic = stream(source, "video")
    stream(source, "audio")
    fps = Fraction(pic["avg_frame_rate"])
    frames = int(pic["nb_frames"])
    length = float(frames / fps)
    size = (pic["width"], pic["height"])
    cover = stream(streams(args.cover, args.ffprobe), "video")
    if size != (1080, 1920) or fps != 60:
        raise ValueError(f"612 native delivery expects 1080x1920 at 60 fps, got {size} at {fps}")
    if (cover["width"], cover["height"]) != size:
        raise ValueError("Supply a 1080x1920 release cover")
    if length <= 0:
        raise ValueError("Video has no frames")
    bed = stream(streams(args.music_bed, args.ffprobe), "audio")
    if float(bed["duration"]) + 0.025 < length:
        raise ValueError("Music bed ends before the video; prepare it for the full timeline")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".mp4", dir=target.parent)
    os.close(fd)
    staging = Path(name)
    filters = [
        "[0:v]setsar=1[vbase]", "[1:v]format=rgba[cover]",
        "[vbase][cover]overlay=0:0:enable='eq(n,0)',format=yuv420p[v]",
        "[2:a:0]aresample=48000,loudnorm=I=-17:TP=-2:LRA=7,aresample=48000,apad[voice]",
        "[3:a:0]aresample=48000,apad[bed]",
        f"[voice][bed]amix=inputs=2:normalize=0,atrim=end={length:.8f},alimiter=limit=0.84:level=0:latency=1[a]"
    ]
    try:
        command(args.ffmpeg, "-v", "error", "-nostdin", "-y", "-i", args.native, "-i", args.cover,
                "-i", args.native, "-i", args.music_bed, "-filter_complex", ";".join(filters),
                "-map", "[v]", "-map", "[a]", "-t", f"{length:.8f}", "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-b:a", "256k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", staging)
        result = streams(staging, args.ffprobe)
        video, audio = stream(result, "video"), stream(result, "audio")
        if (video["width"], video["height"]) != size or int(video["nb_frames"]) != frames or Fraction(video["avg_frame_rate"]) != fps:
            raise ValueError("Final video geometry or timing changed")
        if (audio["codec_name"], audio["sample_rate"], audio["channels"]) != ("aac", "48000", 2) or abs(float(audio["duration"]) - length) > .05:
            raise ValueError("Final audio geometry or timing changed")
        hashes = decoded_hashes(staging, args.ffmpeg)
        digest = sha256(staging)
        report = {"frames": frames, "fps": str(fps), "duration": length, "decode": "ok", "sha256": digest,
                  "decoded_stream_hashes": hashes.splitlines()}
        if args.expected_sha256 and digest != args.expected_sha256.lower():
            raise ValueError(f"File SHA-256 differs: {digest}")
        if args.reference:
            same_file = digest == sha256(args.reference)
            original_video = stream(streams(args.reference, args.ffprobe), "video")
            if (original_video["width"], original_video["height"], int(original_video["nb_frames"]), Fraction(original_video["avg_frame_rate"])) != (*size, frames, fps):
                raise ValueError("Reference video geometry or timing differs")
            if not same_file and decoded_hashes(args.reference, args.ffmpeg) != hashes:
                raise ValueError("Reference differs at decoded video or audio sample level")
            report.update(reference_file_identical=same_file, reference_decoded_identical=True)
        # Publish only the verified result. An existing destination always wins a concurrent race.
        os.link(staging, target)
        print(json.dumps(report, ensure_ascii=True))
    finally:
        staging.unlink(missing_ok=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("native", "cover", "music-bed", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--ffprobe", default="ffprobe")
    ap.add_argument("--reference", type=Path, help="Require the same decoded audio, video and frame clock as this MP4")
    ap.add_argument("--expected-sha256", help="Require an exact match to this published whole-file SHA-256")
    try:
        finish(ap.parse_args())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        ap.exit(1, f"Finish failed: {exc}\n")

