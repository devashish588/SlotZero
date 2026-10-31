"""Verify the delivered MP4 and extract representative frames from that exact file."""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
FFMPEG = shutil.which("ffmpeg") or "C:/Users/hp/AppData/Local/Temp/slotzero-video-deps/bin/ffmpeg.exe"
FFPROBE = shutil.which("ffprobe") or str(Path(FFMPEG).with_name("ffprobe.exe"))
video = ROOT / "slotzero-workflow-voiceover.mp4"
expected = json.loads((ROOT / "scene-timing.json").read_text(encoding="utf-8"))["duration"]
assert video.exists() and video.stat().st_size > 100000
info = json.loads(subprocess.check_output([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)], text=True))
v = next(s for s in info["streams"] if s["codec_type"] == "video")
a = next(s for s in info["streams"] if s["codec_type"] == "audio")
assert (v["width"], v["height"], v["codec_name"], v["r_frame_rate"]) == (1920, 1080, "h264", "30/1")
assert a["codec_name"] == "aac"
assert abs(float(info["format"]["duration"]) - expected) < .12
assert int(v["nb_frames"]) == math.ceil(expected * 30)
decoded = subprocess.run([FFMPEG, "-hide_banner", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True, check=True)
assert not decoded.stderr.strip(), decoded.stderr
volume = subprocess.run([FFMPEG, "-hide_banner", "-i", str(video), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
(ROOT / "audio-check.log").write_text(volume, encoding="utf-8")
mean = float(re.search(r"mean_volume:\s*(-?[\d.]+) dB", volume)[1])
peak = float(re.search(r"max_volume:\s*(-?[\d.]+) dB", volume)[1])
assert mean > -40, "Audio is unexpectedly quiet"
assert peak <= -0.5, "Mix needs more headroom"
times = [7, 34, 66, 86, 108, 120, 139, 165]
sheet = Image.new("RGB", (1600, 4 * 470), "#e7ebf1")
draw = ImageDraw.Draw(sheet)
for index, second in enumerate(times):
    frame = ROOT / f"decoded-{second:03}.jpg"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(second), "-i", str(video), "-frames:v", "1", "-q:v", "2", str(frame)], check=True)
    with Image.open(frame) as image:
        image.thumbnail((800, 450))
        left, top = index % 2 * 800, index // 2 * 470
        sheet.paste(image, (left, top + 20))
        draw.text((left + 12, top + 3), f"{second}s — decoded final MP4", fill="#101b2d")
sheet.save(ROOT / "final-contact-sheet.jpg", quality=90)
shutil.copy2(ROOT / "decoded-066.jpg", ROOT / "poster.jpg")
result = {"passed": True, "duration": float(info["format"]["duration"]), "dimensions": [v["width"], v["height"]], "video_codec": v["codec_name"], "audio_codec": a["codec_name"], "frames": int(v["nb_frames"]), "fps": 30, "mean_db": mean, "peak_db": peak, "bytes": video.stat().st_size, "full_decode": "passed", "subjective_listening": "not performed", "frames_extracted_at_seconds": times}
(ROOT / "media-verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
(ROOT / "media-info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
