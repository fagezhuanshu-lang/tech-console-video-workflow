"""Public style metadata and authored examples; contains no vendor renderer or media."""
import copy

# Hashes of the signed vendor *release*, shared by all authorized recipients.
RELEASE_HASHES = {
    "modern": "b3c24153f4c9870d331387334d9c6aa66d5cef657c3f5427019aaeaf13be2d33",
    "paper": "a6af2710baea9ad75329244701a7c50df27e48e9609d58d3776289fbf721abd0",
    "dark": "83a122209eff060bb97509bcae644563916fc9a27ead4b8d574a337c99dad2f4",
    "character": "dcf8803257cb842e3ddecd3326dc6757da421f65bcc1582ea817c99b5b396ee4",
    "poster": "7b75cc1078425eef924b53845b504d3b95e9d470c944dd3ce55f1054e194ef30",
}

STYLES = {
    "modern": {"id": 606, "slug": "template-01-integrated-portrait", "version": "2.7.18-alpha.15", "name": "现代图文", "workflow": "motion-kit", "profiles": ["light", "dark"]},
    "paper": {"id": 608, "slug": "template-02-expanded-portrait", "version": "2.7.18-alpha.15", "name": "纸面透视", "workflow": "motion-kit", "profiles": ["paper", "ink", "paper"]},
    "dark": {"id": 610, "slug": "template-03-native-portrait", "version": "2.7.18-alpha.15", "name": "深色立体", "workflow": "motion-kit", "profiles": ["dark", "blue", "dark"]},
    "character": {"id": 614, "slug": "template-05-native-portrait", "version": "2.7.18-alpha.15", "name": "鲜色角色", "workflow": "motion-kit", "profiles": ["sticker-orange", "sticker-blue", "sticker-purple"]},
    "poster": {"id": 624, "slug": "vibrant-poster-portrait", "version": "2.7.18-alpha.8", "name": "活力海报", "workflow": "poster-kit", "profiles": []},
}


def example(style):
    """An editable 12-second example. Replace text AND timing for actual narration."""
    settings = STYLES[style]
    captions = [{"s": i * 2, "e": i * 2 + 1.8, "text": text} for i, text in enumerate([
        "今天分享一个方法", "先把目标写清楚", "再把任务拆小", "一次只做一步", "只想不做容易拖延", "先做一步就有进展",
    ])]
    if style == "modern":
        scenes = [
            ("definition", "dictionary", 0, 8, {"kicker": "一个方法", "term": "目标拆解", "definition": "先明确目标，再拆小任务", "example": "一次只做一步"}, [0, 1, 2, 3], ["kicker", "term", "definition", "example"]),
            ("compare", "panels", 8, 12, {"left": {"label": "只想不做", "big": "容易拖延"}, "right": {"label": "先做一步", "big": "开始进展"}, "winner": "none"}, [4, 5], ["left", "right"]),
        ]
    elif style == "paper":
        scenes = [
            ("quote", "card", 0, 4, {"who": "方法提示", "text": "先把目标写清楚"}, [0, 1], ["who", "text"]),
            ("tip", "card", 4, 8, {"kind": "info", "title": "拆小任务", "text": "一次只做一步"}, [2, 3], ["title", "text"]),
            ("qa", "flip", 8, 12, {"question": "总在拖延怎么办？", "answer": "先完成一个小步骤"}, [4, 5], ["question", "answer"]),
        ]
    else:
        opening = ("title", "slam" if style == "poster" else "split", 0, 4, {"kicker": "一个方法", "line1": "目标拆解", "line2": "先把目标写清楚"}, [0, 1], ["kicker", "line2"])
        middle = ("keyword", "slam" if style == "poster" else "focus", 4, 8, {"kicker": "把任务拆小", "word": "一次一步"}, [2, 3], ["kicker", "word"])
        last = ("compare", "panels", 8, 12, {"left": {"label": "只想不做", "big": "容易拖延"}, "right": {"label": "先做一步", "big": "开始进展"}, "winner": "none"}, [4, 5], ["left", "right"])
        if style == "character":
            middle = ("kinetic", "wave", 4, 8, {"lines": ["把任务拆小", "一次只做一步"]}, [2, 3], ["lines[0]", "lines[1]"])
            last = ("chat", "thread", 8, 12, {"title": "如何开始", "messages": [{"who": "left", "name": "提问", "text": "总在拖延怎么办？"}, {"who": "right", "name": "回答", "text": "先完成一个小步骤"}]}, [4, 5], ["messages[0]", "messages[1]"])
        elif style == "poster":
            last = ("quote", "card", 8, 12, {"text": "先做一步\n就有进展"}, [4, 5], ["text", "text"])
        scenes = [opening, middle, last]
    segments, narration = [], []
    for i, (control, variant, a, b, props, indices, targets) in enumerate(scenes):
        segment = {"control": control, "variant": variant, "t0": a, "t1": b, "props": props}
        if style != "poster":
            segment.update(presenter="small" if i == 1 and style != "modern" else "card", transition="wipe" if i == 1 else "cut", styleProfile=settings["profiles"][i])
        segments.append(segment)
        narration.append({"shot": i, "start": a, "end": b, "spokenText": "，".join(captions[j]["text"] for j in indices), "purpose": "real-comparison" if control == "compare" else "neutral-emphasis", "timingSource": "provided-captions", "captionBinding": "continuous", "captionIndices": indices, "beats": [{"at": captions[j]["s"], "until": captions[j]["e"], "spokenText": captions[j]["text"], "timing": "sentence", "target": target} for j, target in zip(indices, targets)]})
    timeline = {"layout": "portrait", "duration": 12, "presenter": {"src": "media/presenter.mp4", "audio": "mute", "framing": "auto"}, "voiceover": "media/voice.wav", "subtitles": "", "music": "", "captions": captions, "segments": segments, "narrationMap": narration, "ending": "cut", "hud": False, "captionAlignment": "frame-center", "narrationLayout": "balanced", "narrationVisualMode": "follow-speech", "language": "zh", "header": {"shortTitle": "把目标拆小", "source": {"kind": "assistant-summary", "field": "timeline.captions"}}}
    if style == "poster":
        timeline["showCaptions"] = True
        return timeline
    timeline.update(aspect="9:16", sourceStart=0, styleProfile=settings["profiles"][0], captionLayout="balanced-lines/1", narrationComposition="readable/1")
    return {"workflow": "motion-kit", "timeline": copy.deepcopy(timeline)}
