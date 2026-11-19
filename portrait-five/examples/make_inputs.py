"""Make short, generated video and sound inputs for the five installation checks."""
import argparse
import shutil
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--seconds", type=float, default=680 / 60)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 600:
        parser.error("--seconds must be between 1 and 600")
    if not shutil.which(args.ffmpeg):
        parser.error("FFmpeg is required. Set --ffmpeg or add it to PATH.")
    args.directory.mkdir(parents=True, exist_ok=True)
    targets = [args.directory / name for name in ("presenter.mp4", "voice.wav")]
    if any(target.exists() for target in targets):
        parser.error("Choose an empty output directory")
    prefix = [args.ffmpeg, "-nostdin", "-n", "-v", "error", "-f", "lavfi", "-i"]
    subprocess.run(prefix + ["testsrc2=size=720x1280:rate=30", "-t", str(args.seconds),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                   "-pix_fmt", "yuv420p", str(targets[0])], check=True)
    subprocess.run(prefix + ["aevalsrc=0.05*sin(2*PI*220*t)*(0.6+0.4*cos(2*PI*t)):s=48000",
                   "-t", str(args.seconds), "-ac", "2", "-c:a", "pcm_s16le",
                   str(targets[1])], check=True)


if __name__ == "__main__":
    main()
