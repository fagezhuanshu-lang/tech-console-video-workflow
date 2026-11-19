"""Create a moving calibration video and original pulse track for a fresh install test."""
import argparse
from pathlib import Path
import subprocess

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    if a.output.exists(): p.error("Choose a new output file")
    a.output.parent.mkdir(parents=True,exist_ok=True)
    # Moving test bars and a quiet pulsed tone deliberately distinguish these from a real speaker.
    subprocess.run(["ffmpeg","-nostdin","-v","error","-f","lavfi","-i","testsrc2=size=1080x1920:rate=30",
        "-f","lavfi","-i","aevalsrc=0.055*sin(2*PI*220*t)*(0.5+0.5*cos(2*PI*2*t)):s=48000",
        "-t","11.333333333","-c:v","libx264","-preset","veryfast","-crf","27","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","128k","-movflags","+faststart",str(a.output)],check=True)
