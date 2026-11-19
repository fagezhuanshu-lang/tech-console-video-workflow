"""Run the portrait 612 workflow from source media to verified delivery."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from story import build
from scripts.finish import decoded_hashes

ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "examples" / "reference-params.json"
ORIGINAL_VIDEO = "ec5172a177d0c250c4e066232fc84894904992feac6f926d6a23fed5d59b38bf"
ORIGINAL_MP4 = "56c9dc3abaf9bdf7897ff0c97f6718fdc034495a8c84a747bc59639774909ae4"

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def file_hash(filename):
    with filename.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=("approved", "native"), default="approved",
                   help="Approved cover and music mix (default), or the verified native template output")
    p.add_argument("--source",required=True,type=Path)
    native_input=p.add_mutually_exclusive_group(required=True)
    native_input.add_argument("--template",type=Path,help="Your own signed MotionGit #612 package")
    native_input.add_argument("--native-render",type=Path,help="Resume from the approved 612 native render of this same episode")
    p.add_argument("--out",required=True,type=Path,help="A new personal work directory")
    group=p.add_mutually_exclusive_group()
    group.add_argument("--music",type=Path,help="Music source you may use")
    group.add_argument("--bed",type=Path,help="A fully prepared audio bed, aligned at zero")
    group.add_argument("--demo-music",action="store_true",help="Generate the included original composition")
    plan=p.add_mutually_exclusive_group(required=True)
    plan.add_argument("--original",action="store_true",help="Use the approved episode plan with the identical original source")
    plan.add_argument("--story",type=Path,help="A scene list for this recording")
    plan.add_argument("--params",type=Path,help="An authored motion-kit plan")
    p.add_argument("--srt",type=Path,help="Proofread subtitles matching --story")
    p.add_argument("--cover-brief",type=Path,help="Cover wording and source portrait crop for this episode")
    p.add_argument("--music-start",type=float)
    p.add_argument("--cache",type=Path,help="Optional location of the official helper runtime cache")
    p.add_argument("--verify-original",action="store_true",help="Fail unless final file exactly matches the approved MP4")
    args=p.parse_args()
    approved = args.mode == "approved"
    if not approved:
        if not args.template:
            p.error("Native mode requires --template to render the official 612 package")
        if args.music or args.bed or args.demo_music or args.music_start is not None or args.cover_brief or args.verify_original:
            p.error("Native mode delivers the direct template output. Cover, music and --verify-original options apply to approved mode.")
    elif not (args.music or args.bed or args.demo_music):
        p.error("Choose --music, --bed or --demo-music")
    for key in ("source","template","native_render","story","params","srt","cover_brief","music","bed"):
        value=getattr(args,key)
        if value and not value.is_file(): p.error("Missing file: "+str(value))
    if args.original and file_hash(args.source)!=ORIGINAL_VIDEO:
        p.error("Different source. Use --story with --srt, or --params, for your own video.")
    if args.original and args.native_render and file_hash(args.native_render)!="08b44ceac7ec147a66cc45e8309d98f113d58e5f2cd87a324919550991126e42":
        p.error("--original with --native-render requires the approved 612 native export.")
    if args.verify_original and (not args.original or args.demo_music):
        p.error("--verify-original needs --original with the matching music source or prepared bed.")
    if approved and not args.original and not args.cover_brief: p.error("Supply --cover-brief for a new episode")
    if args.story and not args.srt: p.error("--story requires --srt")
    if args.srt and not args.story: p.error("--srt is used with --story")
    if args.music_start and not args.music: p.error("--music-start applies only to --music")
    for name in ("ffmpeg","ffprobe","node"):
        if not shutil.which(name): p.error("Missing executable on PATH: "+name)
    brief=args.cover_brief or ROOT/"examples/cover.json"
    if args.story: params=build(args.srt,args.story)
    else: params=json.loads((args.params or REFERENCE).read_text(encoding="utf-8-sig"))
    duration=float(params["timeline"]["duration"])
    if not math.isfinite(duration) or duration<=0: p.error("Plan requires a positive duration")
    if args.native_render:
        probe=run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=nb_frames",
                   "-of","default=noprint_wrappers=1:nokey=1",args.native_render],stdout=subprocess.PIPE,text=True)
        if abs(int(probe.stdout.strip())-duration*60)>1:
            p.error("The approved native render duration does not match this episode plan")
    if approved and not (ROOT/"cover/node_modules/sharp").is_dir():
        npm=shutil.which("npm.cmd" if os.name=="nt" else "npm")
        if not npm: p.error("Install Node.js with npm, then run npm ci --prefix cover")
        run([npm,"ci","--prefix",ROOT/"cover","--no-fund","--no-audit"])
    work=args.out.resolve()
    if work.exists(): p.error("Choose a new output directory. Previous results are preserved.")
    work.mkdir(parents=True)
    private=work/"work"
    private.mkdir()
    params_file=private/"params.json"
    params_file.write_text(json.dumps(params,ensure_ascii=False,indent=2),encoding="utf-8")
    media=private/"media"
    music=args.music
    if args.demo_music:
        music=private/"demo-music.wav"
        run([sys.executable,ROOT/"examples/make_music.py",music,"--seconds",str(max(8,math.ceil(duration)+2))])
    if approved:
        media_options=["--bed",args.bed] if args.bed else ["--music",music,"--music-start",args.music_start or 0]
    else:
        media_options=["--presenter-only"]
    run([sys.executable,ROOT/"media.py","--video",args.source,"--out",media,"--duration",duration,*media_options])
    if approved:
        run(["node",ROOT/"cover/render.mjs",args.source,brief,work/"cover"])
    native=private/"native"
    cache=["--cache",args.cache] if args.cache else []
    if args.template:
        result=run([sys.executable,ROOT/"scripts/native.py","--package",args.template,"--params",params_file,
                    "--presenter",media/"presenter.mp4","--voice",media/"voice.wav","--work",native,*cache],
                   stdout=subprocess.PIPE,text=True)
        receipt=json.loads(result.stdout)
    picture=args.native_render or native/"native.mp4"
    final=work/"video.mp4"
    native_sha=receipt["sha256"] if args.template else file_hash(picture)
    if approved:
        verify=["--expected-sha256",ORIGINAL_MP4] if args.verify_original else []
        result=run([sys.executable,ROOT/"scripts/finish.py","--native",picture,"--cover",work/"cover/cover-9x16.png",
                    "--music-bed",media/"music-bed.wav","--output",final,*verify],
                   stdout=subprocess.PIPE,text=True)
        report=json.loads(result.stdout)
    else:
        pending=private/"native-delivery.tmp.mp4"
        shutil.copyfile(picture,pending)
        delivery_sha=file_hash(pending)
        if delivery_sha!=native_sha:
            raise ValueError("Native delivery differs from the official render receipt")
        hashes=decoded_hashes(pending,"ffmpeg").splitlines()
        frames=receipt["frames"]
        report={"frames":frames,"fps":"60","duration":frames/60,"decode":"ok",
                "sha256":delivery_sha,"decoded_stream_hashes":hashes}
        pending.replace(final)
    report.update(mode=args.mode, native_source="official-render" if args.template else "supplied-export",
                  native_sha256=native_sha)
    if args.srt: shutil.copyfile(args.srt,work/"captions.srt")
    elif args.original: shutil.copyfile(ROOT/"examples/reference.srt",work/"captions.srt")
    else:
        def stamp(t):
            ms=round(1000*t)
            return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
        lines=params["timeline"]["captions"]
        (work/"captions.srt").write_text("\n\n".join(
            f"{i}\n{stamp(line['s'])} --> {stamp(line['e'])}\n{line['text']}" for i,line in enumerate(lines,1))+"\n",encoding="utf-8")
    (work/"verification.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(final)

if __name__=="__main__":
    try: main()
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as exc:
        sys.exit("Workflow failed: "+str(exc))

