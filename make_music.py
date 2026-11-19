"""Write an original, sample-free electronic accompaniment; no network access."""
import argparse
import array
import math
from pathlib import Path
import sys
import wave

RATE = 24000
BEAT = 60 / 96
TAU = 2 * math.pi

def pitch(note):
    return 440 * 2 ** ((note-69)/12)

def render(target, seconds):
    target = Path(target)
    if not 1 <= seconds <= 3600:
        raise ValueError("Choose a duration between 1 and 3600 seconds")
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Original four-bar voicing and eight-note pattern, generated without recordings.
    chords = ((50,57,60,65), (53,57,60,67), (48,55,60,64), (55,59,62,69))
    order = (1,3,2,1,3,2,0,2)
    phases = [pitch(n) * TAU for n in range(128)]
    with wave.open(str(target), "wb") as out:
        out.setparams((1,2,RATE,0,"NONE","not compressed"))
        for second in range(math.ceil(seconds)):
            block = array.array("h")
            for index in range(second*RATE, min((second+1)*RATE, round(seconds*RATE))):
                t = index / RATE
                beat = t / BEAT
                chord = chords[int(beat/4)%4]
                step = int(beat*2)
                age = (beat*2-step)*BEAT/2
                note = chord[order[step%8]] + 12
                # Soft pluck; the fundamental and a quiet partial share the same envelope.
                env = min(1,age/.012)*math.exp(-age*12)
                pluck=(math.sin(phases[note]*age)+.14*math.sin(2*phases[note]*age))*env*.105
                bar = (beat%4)*BEAT
                swell = min(1,bar/.10,(4*BEAT-bar)/.18)
                pad = swell*sum(math.sin(phases[n]*t) for n in chord[1:])*.020
                bass = math.sin(phases[chord[0]-12]*t)*swell*.055
                pulse_age = (beat%2)*BEAT
                pulse = math.sin(TAU*(48*pulse_age+1.8*(1-math.exp(-20*pulse_age))))*math.exp(-pulse_age*16)*.095
                fade = max(0,min(1,t/.18,(seconds-t)/.25))
                block.append(round((pluck+pad+bass+pulse)*fade*32767))
            if sys.byteorder == "big":
                block.byteswap()
            out.writeframes(block.tobytes())

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--seconds",type=float,default=48)
    args=parser.parse_args()
    render(args.output,args.seconds)

