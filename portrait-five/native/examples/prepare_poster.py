"""Prepare media for the two-scene 624 native example using the supplied 11.33 s clip."""
import argparse
import shutil
import subprocess
from pathlib import Path

from make_grain import make_grain


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path, help="Reviewed 11.33-second speaker clip with original audio")
    parser.add_argument("directory", type=Path, help="New input directory")
    args = parser.parse_args()
    duration = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                     "-of","default=noprint_wrappers=1:nokey=1",str(args.clip)]))
    if abs(duration - 680 / 60) > 0.05:
        parser.error("This timing is for the 11.33-second example. Author a new timeline for a different duration.")
    args.directory.mkdir(parents=True, exist_ok=False)
    # The first scene has its own video slot. The full talk gets a quiet 1.47 s closing beat.
    shutil.copyfile(args.clip, args.directory / "presenter.mp4")
    make_grain(args.directory / "grain.png")
    subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(args.clip),
                    "-vf","fps=60,tpad=stop_mode=clone:stop_duration=1.5","-af","apad=pad_dur=1.5",
                    "-t","12.8","-c:v","libx264","-preset","fast","-crf","16","-c:a","aac","-b:a","256k",
                    str(args.directory / "talk-with-outro.mp4")],check=True)


if __name__ == "__main__":
    main()
