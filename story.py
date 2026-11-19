"""Build template 612's scene parameters from proofread SRT and a short scene list."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
TIMECODE = re.compile(r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})")

def seconds(text):
    m=TIMECODE.fullmatch(text.strip())
    if not m:
        raise ValueError("Invalid subtitle time: "+text)
    h,m,s,ms=map(int,m.groups())
    if m>=60 or s>=60:
        raise ValueError("Subtitle minutes and seconds must be below 60")
    return h*3600+m*60+s+ms/1000

def captions(file, duration):
    result=[]
    for block in re.split(r"\n\s*\n", file.read_text(encoding="utf-8-sig").strip()):
        index,timing,*lines=block.splitlines()
        a,b=map(seconds,timing.split("-->"))
        text=" ".join(line.strip() for line in lines).strip()
        if not index.strip().isdigit() or not text or not 0<=a<b<=duration+.001 or (result and a<result[-1]["e"]):
            raise ValueError("Invalid, overlapping, or out-of-range subtitle near "+index)
        result.append({"s":a,"e":min(b,duration),"text":text})
    if not result:
        raise ValueError("Empty SRT")
    return result

STYLES={
    "title":("split","card","cut",("kicker","line1","line2")),
    "keyword":("focus","small","wipe",("kicker","word")),
    "quote":("reveal","card","cut",("text",))
}

def build(srt,story):
    source=json.loads(story.read_text(encoding="utf-8-sig"))
    duration=float(source["duration"])
    lines=captions(srt,duration)
    plan=json.loads((ROOT/"examples/reference-params.json").read_text(encoding="utf-8-sig"))
    timeline=plan["timeline"]
    segments,anchors=[],[]
    start=0
    for shot,item in enumerate(source["scenes"]):
        end=item["throughCaption"]
        if not isinstance(end,int) or not start<end<=len(lines):
            raise ValueError("throughCaption must advance through the numbered captions")
        kind=item["control"]
        variant,presenter,transition,keys=STYLES[kind]
        props=item["props"]
        if set(props)!=set(keys) or any(not isinstance(v,str) or not v.strip() for v in props.values()):
            raise ValueError(f"{kind} expects these nonempty text fields: {keys}")
        t0=0 if start==0 else lines[start]["s"]
        t1=duration if end==len(lines) else lines[end]["s"]
        segments.append(dict(control=kind,variant=variant,t0=t0,t1=t1,props=props,presenter=presenter,
                             transition=transition,styleProfile="console"))
        bindings=item.get("targets")
        if bindings is not None and (len(bindings)!=end-start or any(v not in keys for v in bindings)):
            raise ValueError("targets must name one valid text field per subtitle")
        beats=[]
        for local,line in enumerate(lines[start:end]):
            target=bindings[local] if bindings else keys[min(local,len(keys)-1)]
            beats.append(dict(at=line["s"],until=line["e"],spokenText=line["text"],timing="sentence",target=target))
        anchors.append(dict(shot=shot,start=t0,end=t1,spokenText="，".join(x["text"] for x in lines[start:end]),
                            purpose="neutral-emphasis",timingSource="provided-captions",captionBinding="continuous",
                            captionIndices=list(range(start,end)),beats=beats))
        start=end
    if start!=len(lines):
        raise ValueError("Scenes must include every caption")
    title=source["header"]
    if not isinstance(title,str) or not title.strip():
        raise ValueError("Set the title in header")
    timeline.update(duration=duration,captions=lines,segments=segments,narrationMap=anchors)
    timeline["header"]["shortTitle"]=title
    return plan

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("srt","story","output"):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    try:
        value=build(a.srt,a.story)
        with a.output.open("x",encoding="utf-8") as f:
            json.dump(value,f,ensure_ascii=False,indent=2)
    except (ValueError,KeyError,OSError) as exc:
        p.exit(1,str(exc)+"\n")

