"""Build an editable film timed to the generated narration, with alignment self-checks."""
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "composition"
SCENES = PROJECT / "compositions"
SCENES.mkdir(exist_ok=True)
scenes = json.loads((ROOT / "narration.json").read_text(encoding="utf-8"))
speech = json.loads((ROOT / "speech-metadata.json").read_text(encoding="utf-8"))
words = [w for w in speech["word_timestamps"] if not w["word"].startswith("<")]
expected = " ".join(s["text"] for s in scenes).split()
normalize = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
assert len(words) == len(expected), "Narration and script word counts differ"
assert all(normalize(a) == normalize(b["word"]) for a, b in zip(expected, words)), "Narration and script alignment differs"
offset = 0.30
cursor = 0
for index, scene in enumerate(scenes):
    count = len(scene["text"].split())
    scene["start"] = 0 if index == 0 else round(offset + (words[cursor - 1]["end"] + words[cursor]["start"]) / 2, 3)
    scene["speech_start"] = round(offset + words[cursor]["start"], 3)
    scene["speech_end"] = round(offset + words[cursor + count - 1]["end"], 3)
    cursor += count
total = round(speech["duration"] + offset + 2.0, 3)
for i, scene in enumerate(scenes):
    scene["duration"] = round((scenes[i + 1]["start"] if i + 1 < len(scenes) else total) - scene["start"], 3)
    assert scene["start"] <= scene["speech_start"] < scene["speech_end"] <= scene["start"] + scene["duration"] + .001
assert abs(sum(s["duration"] for s in scenes) - total) < .01
(ROOT / "scene-timing.json").write_text(json.dumps({"duration": total, "scenes": scenes}, indent=2), encoding="utf-8")

css = """
@font-face{font-family:Manrope;src:url('assets/fonts/manrope.woff2');font-weight:100 900}
@font-face{font-family:'DM Sans';src:url('assets/fonts/dm-sans.woff2');font-weight:100 900}
*{box-sizing:border-box}#root{position:absolute;inset:0;overflow:hidden;background:#f6f8fb;color:#18263a;font-family:'DM Sans'}
.chapter{position:absolute;left:192px;top:110px;font-size:28px;font-weight:700;color:#116c4b;letter-spacing:1px}
h1,p{margin:0}h1{font:800 64px/1.12 Manrope;letter-spacing:-2px}
.title{position:absolute;left:192px;top:166px;width:1536px}.detail{position:absolute;left:192px;top:260px;width:1536px;font-size:32px;line-height:1.35;color:#42546c}
.stage{position:absolute;left:192px;top:350px;width:1536px;height:580px;background:white;border:2px solid #d9e1eb;border-radius:20px;overflow:hidden}
.bar{height:48px;background:#e7ebf1;color:#42546c;display:flex;align-items:center;gap:10px;padding:0 24px;font-size:28px}.bar i{width:10px;height:10px;background:#718096;border-radius:50%}.bar span{margin-left:24px}
.surface{position:absolute;left:26px;right:26px;top:64px;bottom:20px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.surface img{max-width:100%;max-height:100%;object-fit:contain;display:block}
.foot{position:absolute;left:192px;bottom:94px;font-size:28px;line-height:1.3;color:#52637a}
.cue{position:absolute;right:36px;bottom:28px;background:#ddf5eb;color:#116c4b;border:2px solid #16865e;border-radius:12px;font-size:30px;font-weight:700;padding:15px 24px}
.dark{background:#101b2d!important;color:#f6f8fb!important}.dark .chapter{color:#90e2bc}.dark .detail,.dark .foot{color:#b7c8d9}.dark h1{color:#f6f8fb}.accent{color:#90e2bc}
.narrow .title{top:240px;width:760px;font-size:80px;line-height:1.16}.narrow .detail{top:540px;width:730px;font-size:34px;line-height:1.5}.narrow .stage{left:1128px;top:146px;width:570px;height:770px}.narrow .surface{inset:20px}.narrow .bar{display:none}
.wide .stage{height:596px}.wide .surface{top:62px;bottom:18px}
.notice-scene .stage{height:570px;background:#fff}.notice-scene .surface{align-items:flex-start;top:240px}.notice-scene .surface img{width:100%;max-height:160px}.notice-scene .summary{position:absolute;left:40px;right:40px;top:108px;font:800 44px/1.2 Manrope;color:#18263a}.notice-scene .cue{bottom:44px}
"""
cue_copy = {"signin":"Sign in to your workspace", "register":"Patient registration", "schedule":"30-minute consultations", "blocks":"14:00–15:00 unavailable", "discover":"Dr. Meera · London", "slots":"15:30 Kolkata = 10:00 London", "book":"Appointment confirmed", "calendar":"10:00–10:30 London", "conflict":"One confirmed booking", "reschedule":"Original booking stays safe", "moved":"New time: 16:30 Kolkata", "cancel":"Slot released after cancellation", "history":"Every change is recorded"}

for scene in scenes:
    ident = scene["id"]
    title, detail, chapter = [html.escape(scene[k]) for k in ("title", "detail", "chapter")]
    dur = scene["duration"]
    standard = f'<div class="chapter">{chapter}</div><h1 class="title" data-var-text="{ident}-title">{title}</h1><p class="detail">{detail}</p>'
    foot = '<div class="foot">Actual SlotZero interface · isolated fictional-data demonstration</div>'
    root_class = "wide"
    animation = "tl.fromTo('.stage',{opacity:0,y:30},{opacity:1,y:0,duration:.45,ease:'power3.out'},.06);"

    if ident == "problem":
        root_class = "dark"
        content = '''<div class="chapter">A scheduling problem worth solving</div>
<h1 data-hold="true" style="position:absolute;left:192px;top:250px;width:780px;font-size:100px">Two patients.<br>One slot.<br><span class="accent" id="answer">One confirmed.</span></h1>
<div id="requests" style="position:absolute;left:1070px;top:270px;width:650px;font-size:34px;line-height:1.5"><div style="padding:26px;border-bottom:2px solid #405268">Asha · Kolkata <strong style="float:right">15:30</strong></div><div style="padding:26px">Sam · New York <strong style="float:right">05:00</strong></div></div>
<div id="result" style="position:absolute;left:1070px;top:575px;width:650px;padding:30px;border-radius:18px;background:#ddf5eb;color:#116c4b;font-size:36px;font-weight:700">Asha: appointment confirmed<br><span style="font-size:30px;font-weight:400">Sam: please choose another time</span></div>
<div class="foot">SlotZero · conflict-checked doctor appointment scheduling</div>'''
        animation = "tl.fromTo('#requests',{opacity:0,x:40},{opacity:1,x:0,duration:.45,ease:'power3.out'},.2).fromTo('#answer',{opacity:0},{opacity:1,duration:.3},4.3).fromTo('#result',{opacity:0,y:22},{opacity:1,y:0,duration:.4,ease:'power3.out'},5.2);"
    elif ident == "zones":
        root_class = "dark"
        content = standard + '''<div style="position:absolute;left:192px;top:386px;width:1536px;border-top:2px solid #405268;border-bottom:2px solid #405268;padding:30px 0"><div class="zone-row" style="display:flex;align-items:center;justify-content:space-between;height:122px"><span style="font-size:40px">London</span><strong style="font:800 76px Manrope">10:00</strong><span style="font-size:32px;width:350px;text-align:right">Europe/London</span></div><div class="zone-row" style="display:flex;align-items:center;justify-content:space-between;height:122px;color:#90e2bc"><span style="font-size:40px">Kolkata</span><strong style="font:800 76px Manrope">15:30</strong><span style="font-size:32px;width:350px;text-align:right">Asia/Kolkata</span></div><div class="zone-row" style="display:flex;align-items:center;justify-content:space-between;height:122px"><span style="font-size:40px">New York</span><strong style="font:800 76px Manrope">05:00</strong><span style="font-size:32px;width:350px;text-align:right">America/New_York</span></div></div><div class="foot">One UTC instant · local displays account for the selected time zone</div>'''
        animation = "tl.fromTo('.zone-row',{opacity:.25,x:25},{opacity:1,x:0,duration:.4,stagger:2.4,ease:'power2.out'},.2);"
    elif ident == "close":
        root_class = "dark"
        content = '''<div class="chapter">Explore the working prototype</div><h1 style="position:absolute;left:192px;top:240px;font-size:140px">slotzero<span class="accent">.</span></h1><div style="position:absolute;left:192px;top:430px;font:800 76px Manrope">Appointments, in sync.</div><div id="cta" style="position:absolute;left:192px;top:620px;color:#90e2bc;font-size:46px">slot-zero-pied.vercel.app/login</div><div id="scope" style="position:absolute;left:192px;top:750px;width:1536px;color:#b7c8d9;font-size:32px;line-height:1.5">Doctor availability → patient booking → safe appointment changes<br>Fictional-data prototype · reminders and payments are not included</div><div class="foot">Music: Sascha Ende · ende.app · CC BY 4.0</div>'''
        animation = "tl.fromTo('#cta',{opacity:0,x:24},{opacity:1,x:0,duration:.45,ease:'power3.out'},Math.min(3,D*.2)).fromTo('#scope',{opacity:0},{opacity:1,duration:.4},Math.min(9,D*.6));"
    else:
        if ident in ("signin", "register"):
            root_class = "dark narrow"
        screen = scene["screen"]
        notice = ident in ("conflict", "cancel")
        if notice:
            root_class += " notice-scene"
        summary = '<div class="summary">' + ("Sam's request for the same slot" if ident == "conflict" else "Asha cancels her eligible appointment") + '</div>' if notice else ""
        cue = html.escape(cue_copy[ident])
        badge = f'<div class="cue" data-hold="true">{cue}</div>' if notice else ""
        content = standard + f'<div class="stage" data-hold="true"><div class="bar"><i></i><i></i><i></i><span>SlotZero · {chapter}</span></div>{summary}<div class="surface"><img src="assets/{screen}.png" alt="Actual SlotZero {html.escape(screen)} screen"></div>{badge}</div>' + foot
        if notice:
            animation += "tl.fromTo('.cue',{opacity:0,y:12},{opacity:1,y:0,duration:.25,ease:'power2.out'},Math.min(4.2,D*.48));"
    if ident in ("zones", "close"):
        content = content.replace('<h1 ', '<h1 data-hold="true" ', 1)
    document = f'''<template><style>{css}</style><div id="root" data-composition-id="{ident}" data-width="1920" data-height="1080"><div class="{root_class}" style="position:absolute;inset:0">{content}</div></div><script>const D={dur};const tl=gsap.timeline({{paused:true}});{animation}window.__timelines=window.__timelines||{{}};window.__timelines['{ident}']=tl;</script></template>'''
    (SCENES / f"{ident}.html").write_text(document, encoding="utf-8")

hosts = "".join(f'<div id="scene-{s["id"]}" class="clip" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" data-start="{s["start"]}" data-duration="{s["duration"]}" data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080"></div>' for s in scenes)
audio = f'<audio id="voiceover" class="clip" src="assets/narration.mp3" data-start="{offset}" data-duration="{speech["duration"]}" data-volume="0.65" data-track-index="10"></audio>'
audio += f'<audio id="music" class="clip" src="assets/music-bed.mp3" data-start="0" data-duration="{total}" data-volume="0.075" data-fade-in="1" data-fade-out="3" data-track-index="11"></audio>'
index = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><script src="assets/gsap.min.js"></script><style>*{{box-sizing:border-box}}html,body{{margin:0;width:1920px;height:1080px;overflow:hidden;background:#101b2d}}.clip{{position:absolute;inset:0}}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="1920" data-height="1080" data-fps="30">{hosts}{audio}</div><script>window.__timelines=window.__timelines||{{}};window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>'''
(PROJECT / "index.html").write_text(index, encoding="utf-8")
(PROJECT / "meta.json").write_text(json.dumps({"id":"slotzero-narrated-workflow","name":"SlotZero narrated workflow"},indent=2),encoding="utf-8")
(PROJECT / "hyperframes.json").write_text(json.dumps({"paths":{"blocks":"compositions","components":"compositions/components","assets":"assets"},"media":{"autoProxy":True}},indent=2),encoding="utf-8")
print(f"Built {len(scenes)} scenes, {total:.3f}s. All {len(words)} words aligned exactly to the authored script.")
