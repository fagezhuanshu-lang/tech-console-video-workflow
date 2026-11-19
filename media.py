"""Prepare the portrait presenter, original voice and stereo music bed for the 612 workflow."""
import argparse
from array import array
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SR = 48000
VIDEO_SHA = "ec5172a177d0c250c4e066232fc84894904992feac6f926d6a23fed5d59b38bf"
MUSIC_SHA = "ceeea50bd12575d36c0c8f8cc9c4ededb7adac29d7e89a07fb4b29dc8846e32c"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def run(exe, *args):
    subprocess.run([exe, "-nostdin", "-v", "error", "-n", *args], check=True)


def probe(exe, path):
    return json.loads(subprocess.check_output([exe, "-v", "error", "-show_streams",
                                              "-of", "json", path]))["streams"]


def read_floats(exe, *args):
    data = array("f")
    data.frombytes(subprocess.check_output([exe, "-nostdin", "-v", "error", *args,
                                            "-vn", "-ar", str(SR), "-ac", "2", "-f", "f32le", "-"]))
    if sys.byteorder != "little":
        data.byteswap()
    return data


def gain_for(exe, path, seek, duration, target):
    command = [exe, "-nostdin", "-hide_banner", "-nostats", *seek, "-i", path, "-t", duration,
               "-vn", "-af", "aformat=sample_rates=48000:channel_layouts=stereo,ebur128", "-f", "null", "-"]
    output = subprocess.run(command, check=True, stderr=subprocess.PIPE).stderr.decode(errors="replace")
    results = re.findall(r"I:\s+(-?[0-9.]+) LUFS", output)
    if not results or float(results[-1]) <= -69.9:
        raise ValueError("Cannot normalize silent audio.")
    return 10 ** ((target - float(results[-1])) / 20)


def window_sums(values, size):
    """Centered running sums with the same reflected endpoints as scipy's uniform_filter1d."""
    half = size // 2
    if len(values) < size:
        raise ValueError("Audio is too short for speech detection.")
    padded = values[:half][::-1] + values + values[-(half-1):][::-1]
    total = sum(padded[:size])
    for i in range(len(values)):
        yield total
        if i + 1 < len(values):
            total += padded[i + size] - padded[i]


def raw_music(args, source, directory, seek, samples, duration, video_sha, music_sha):
    # The original trial's speech detector saw the next 145ms of the continuous recording.
    context = f"{float(duration) + .16:.6f}"
    mono = directory / "detector.wav"
    run(args.ffmpeg, *seek, "-i", args.video, "-t", context, "-map", "0:a:0", "-vn",
        "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", mono)
    excerpt = [] if args.music_start == 0 else ["-ss", str(args.music_start)]
    reference_voice = video_sha == VIDEO_SHA and not seek
    reference_music = music_sha == MUSIC_SHA and not excerpt
    voice_gain = 3.7735004366481095 if reference_voice else gain_for(args.ffmpeg, mono, [], duration, -16)
    music_gain = 0.8174517079808572 if reference_music else gain_for(args.ffmpeg, source, excerpt, duration, -22)
    voice = read_floats(args.ffmpeg, "-i", mono)[::2]
    power = array("d", ((v * voice_gain) ** 2 for v in voice))
    del voice
    speech = array("B", (int(value > 1920 * .007**2) for value in window_sums(power, 1920)))
    del power
    if len(speech) < samples:
        # A source/FFmpeg rounding difference of one sample is normal at the final frame.
        if len(speech) < samples - 2:
            raise ValueError("Narration does not cover the requested excerpt.")
        speech.extend([speech[-1]] * (samples-len(speech)))
    audio = read_floats(args.ffmpeg, *excerpt, "-i", source, "-t", duration)
    if len(audio) < 2 * samples:
        raise ValueError("Music is too short at the selected offset. Supply a longer track or reduce the offset.")
    # In the approved mix the global normalization turned down the premix by 1.010316584 dB.
    master_trim = 0.8901929915441916
    pcm = array("i")
    fade_count = min(samples, 57600)
    for i, activity in enumerate(window_sums(speech, 12000)):
        if i >= samples:
            break
        duck = 10 ** (-7 * min(2 * activity / 12000, 1) / 20)
        if i < fade_count:
            duck *= i/(fade_count-1)
        for channel in (0, 1):
            value = audio[2*i+channel] * music_gain * duck * master_trim
            # libsndfile's PCM24 quantizer first rounds to signed 32-bit, then discards 8 bits.
            pcm.append(max(-2147483648, min(2147483647, round(value*2147483648))) & -256)
    if sys.byteorder != "little":
        pcm.byteswap()
    raw = directory / "music.s32le"
    with raw.open("wb") as handle:
        pcm.tofile(handle)
    return ["-f", "s32le", "-ar", str(SR), "-ac", "2", "-i", raw]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--music", type=Path, help="Original licensed music file. The reference M4A starts at zero.")
    choice.add_argument("--bed", type=Path, help="Finished music bed, already ducked and faded. No further gain or fade.")
    parser.add_argument("--out", "--output", type=Path, required=True, help="New directory for the three inputs.")
    parser.add_argument("--start", type=float, default=0, help="Video start in seconds.")
    parser.add_argument("--duration", type=Fraction, default=Fraction(340, 30), help="Seconds; must align to 30 fps (e.g. 340/30).")
    parser.add_argument("--music-start", type=float, default=0, help="Offset into supplied music or finished bed.")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    args = parser.parse_args()
    if not all(math.isfinite(v) and v >= 0 for v in (args.start, args.music_start)):
        parser.error("Offsets must be finite and nonnegative.")
    exact = args.duration * 30
    frames = round(exact)
    # This workflow uses the motion-kit timeline.duration contract.
    if not 5 <= args.duration <= 600 or abs(float(exact)-frames) > 0.0001:
        parser.error("Use 5 to 600 seconds aligned to whole 30 fps frames.")
    samples = frames * 1600
    duration = f"{frames / 30:.6f}"
    music_file = args.music or args.bed
    if args.out.exists():
        parser.error("Output directory already exists; supply a new directory.")
    if not args.video.is_file() or not music_file.is_file():
        parser.error("The source video and music files must both exist.")
    streams = probe(args.ffprobe, args.video)
    video = next((s for s in streams if s["codec_type"] == "video"), None)
    if not video or not any(s["codec_type"] == "audio" for s in streams):
        parser.error("The source must include picture and original audio.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".612-media-", dir=args.out.parent) as temp:
        scratch = Path(temp)
        stage = scratch / "prepared"
        stage.mkdir()
        seek = [] if args.start == 0 else ["-ss", str(args.start)]
        video_sha, music_sha = digest(args.video), digest(music_file)
        filters = "fps=30,setsar=1"
        if (video["width"], video["height"]) != (1080, 1920) or video.get("sample_aspect_ratio", "1:1") not in ("1:1", "N/A"):
            filters = "fps=30,scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2:reset_sar=1,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
        presenter = stage / "presenter.mp4"
        voice = stage / "voice.wav"
        run(args.ffmpeg, *seek, "-i", args.video, "-map", "0:v:0", "-map", "0:a:0",
            "-t", duration, "-vf", filters, "-c:v", "libx264", "-preset", "veryfast", "-crf", "17",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart",
            presenter, "-map", "0:a:0", "-t", duration, "-vn", "-c:a", "pcm_s16le", "-ar", "48000", voice)
        if args.music:
            music_input = raw_music(args, music_file, scratch, seek, samples, duration, video_sha, music_sha)
            end = frames/30
            curve = f"atrim=end={duration},asetpts=PTS-STARTPTS,afade=t=out:st={end - .753333333333:.5f}:d=0.75333"
        else:
            excerpt = ["-ss", str(args.music_start)] if args.music_start else []
            music_input = [*excerpt, "-i", args.bed]
            curve = f"atrim=end={duration},asetpts=PTS-STARTPTS"
        bed = stage / "music-bed.wav"
        run(args.ffmpeg, *music_input, "-map", "0:a:0", "-af", curve, "-c:a", "pcm_s24le", "-ar", "48000", "-ac", "2", bed)
        picture = next(s for s in probe(args.ffprobe, presenter) if s["codec_type"] == "video")
        if int(picture.get("nb_frames", -1)) != frames:
            raise ValueError("Source picture does not cover the requested excerpt.")
        for wav in (bed, voice):
            actual = probe(args.ffprobe, wav)[0]
            tolerance = 2 if wav == voice else 0
            if abs(int(actual["duration_ts"])-samples) > tolerance:
                raise ValueError(f"{wav.name} is shorter than the requested time range.")
        stage.rename(args.out)
    print(json.dumps({"frames": frames, "duration": duration, "source_sha256": video_sha, "music_sha256": music_sha,
                      "inputs": ["presenter.mp4", "voice.wav", "music-bed.wav"]}))


if __name__ == "__main__":
    main()



