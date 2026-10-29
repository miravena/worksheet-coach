"""Cut the screen recording and stills to the narration, burn in captions, mux (#15).

    python video/assemble.py out/video
Reads narration.json and the shot WAVs (narrate.py), screen.webm and marks.json (record.py),
the card PNGs (cards.py), and the practice PDF of the recorded run (from out/cache/<sample>.json).
Writes out/video/worksheet-coach.mp4. Needs ffmpeg with libx264, libass and pdftoppm.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS, W, H = 30, 1920, 1080
FONT = "DejaVu Sans"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def enc(out: Path) -> list[str]:
    return ["-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(out)]


def badge(text: str) -> str:
    return (f"drawtext=font='{FONT}':text='{text}':fontsize=30:fontcolor=white:box=1:"
            f"boxcolor=0x1f6f6b@0.92:boxborderw=14:x=w-tw-40:y=34")


def screen_clip(src: Path, a: float, b: float, dur: float, out: Path, label: str = "",
                hold: str = "end") -> None:
    """Play src[a:b] in exactly dur seconds: speed up if longer; if shorter, hold the first
    frame (hold="start") or the last one (hold="end")."""
    length = b - a
    speed = max(1.0, length / dur)
    pad = max(0.0, dur - length / speed)
    tpad = (f"tpad=start_mode=clone:start_duration={pad:.2f}" if hold == "start"
            else f"tpad=stop_mode=clone:stop_duration={dur:.2f}")
    vf = [f"setpts=(PTS-STARTPTS)/{speed:.4f}", f"fps={FPS}", tpad, f"scale={W}:{H}"]
    if label:
        vf.append(badge(label + (f" · sped up {speed:.1f}x" if speed > 1.05 else "")))
    run("ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.2f}", "-t", f"{length:.2f}", "-i", str(src),
        "-vf", ",".join(vf), "-t", f"{dur:.2f}", *enc(out))


def still_clip(img: Path, dur: float, out: Path, zoom: bool = False) -> None:
    n = int(dur * FPS) + 1
    if zoom:  # slow push-in
        vf = (f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=decrease,pad={W * 2}:{H * 2}:(ow-iw)/2:(oh-ih)/2:color=0x3b2f2a,"
              f"zoompan=z='1+0.18*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}")
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xf6f7f4"
    run("ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
        "-t", f"{dur:.2f}", *enc(out))


def marked_sheet(out: Path) -> Path:
    """The ws01 sheet with red-pen marks, placed using the agent's own boxes from a saved run."""
    from PIL import Image, ImageDraw

    run_ = json.loads((ROOT / "out/cache/ws01.json").read_text())
    img = Image.open(ROOT / "tests/worksheets/ws01.png").convert("RGB")
    sx, sy = img.width / run_["size"][0], img.height / run_["size"][1]
    d = ImageDraw.Draw(img)
    red = (200, 40, 40)
    for v in run_["verdicts"]:
        x1, y1, x2, y2 = v["box"]
        cx, cy, r = int((x2 + 40) * sx), int((y1 + y2) / 2 * sy), int(46 * sx)
        if v["is_correct"]:
            d.line([(cx - r, cy), (cx - r // 3, cy + r // 2), (cx + r, cy - r // 1.2)], fill=red, width=12)
        else:
            d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=red, width=12)
            d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=red, width=12)
    img.save(out)
    return out


def ass_time(t: float) -> str:
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main(d: Path) -> None:
    nar = {s["id"]: s for s in json.loads((d / "narration.json").read_text())}
    marks = json.loads((d / "marks.json").read_text())
    screen = d / "screen.webm"
    clips = d / "clips"
    clips.mkdir(exist_ok=True)
    pdf = ROOT / "out" / json.loads((ROOT / "out/cache/ws13.json").read_text())["practice"]["pdf_url"].split("/files/")[1]
    run("pdftoppm", "-r", "150", "-png", "-f", "2", "-l", "2", "-singlefile", str(pdf), str(d / "answer-key"))
    from PIL import Image  # the top of the key page, large enough to read

    key = Image.open(d / "answer-key.png")
    key.crop((0, 0, key.width, int(key.width * 0.62))).save(d / "answer-key.png")

    def line_end(shot: str, i: int) -> float:  # where line i of a shot finishes, plus its gap
        caps = nar[shot]["captions"]
        return caps[i + 1]["start"] if i + 1 < len(caps) else nar[shot]["seconds"]

    parts: list[Path] = []

    def add(name: str, make) -> None:
        out = clips / f"{len(parts):02d}-{name}.mp4"
        make(out)
        parts.append(out)

    sec = lambda s: nar[s]["seconds"]  # noqa: E731
    add("hook", lambda o: still_clip(marked_sheet(d / "ws01-marked.png"), sec("hook"), o, zoom=True))
    add("start", lambda o: screen_clip(screen, marks["start"] - 0.5, marks["live"] + 0.5, sec("start"), o,
                                       hold="start"))
    add("live", lambda o: screen_clip(screen, marks["live"] + 0.5, marks["results"] + 1.0, sec("live"), o, "LIVE RUN"))
    t1 = line_end("pattern", 0)  # line 1 on the pattern card, line 2 over the evidence cards
    add("pattern", lambda o: screen_clip(screen, marks["pattern"], marks["evidence"] - 1.5, t1, o, "LIVE RUN"))
    add("evidence", lambda o: screen_clip(screen, marks["evidence"] - 1.5, marks["practice"], sec("pattern") - t1, o,
                                          "LIVE RUN"))
    p2 = line_end("practice", 1)  # lines 1-2: practice list; line 3: answer key page; line 4: the sheet
    p3 = line_end("practice", 2)
    add("practice-list", lambda o: screen_clip(screen, marks["practice"], marks["practice"] + 4.5, p2, o, "LIVE RUN"))  # hold on the list
    add("answer-key", lambda o: still_clip(d / "answer-key.png", p3 - p2, o))
    add("sheet", lambda o: screen_clip(screen, marks["sheet"], marks["summary"], sec("practice") - p3, o, "LIVE RUN"))
    a2 = line_end("accuracy", 1)
    add("accuracy", lambda o: still_clip(d / "card-accuracy.png", a2, o))
    add("ws12", lambda o: still_clip(d / "card-ws12.png", sec("accuracy") - a2, o))
    add("summary", lambda o: screen_clip(screen, marks["summary"], marks["end"], sec("summary"), o, "LIVE RUN"))
    add("title", lambda o: still_clip(d / "card-title.png", sec("title"), o))

    (clips / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(clips / "list.txt"),
        "-c", "copy", str(d / "picture.mp4"))

    order = ["hook", "start", "live", "pattern", "practice", "accuracy", "summary", "title"]
    (d / "audio.txt").write_text("".join(f"file '{s}.wav'\n" for s in order))
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(d / "audio.txt"),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", str(d / "voice.wav"))

    events, t = [], 0.0
    for s in order:
        for c in nar[s]["captions"]:
            text = c["text"].replace("\n", " ")
            events.append(f"Dialogue: 0,{ass_time(t + c['start'])},{ass_time(t + c['end'] + 0.25)},Cap,,0,0,0,,{text}")
        t += nar[s]["seconds"]
    (d / "captions.ass").write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},46,&H00FFFFFF,&H00000000,&H64151515,0,0,0,0,100,100,0,0,3,14,0,2,200,200,46,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n")

    run("ffmpeg", "-loglevel", "error", "-y", "-i", str(d / "picture.mp4"), "-i", str(d / "voice.wav"),
        "-vf", f"ass={d / 'captions.ass'}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        str(d / "worksheet-coach.mp4"))
    print(f"wrote {d / 'worksheet-coach.mp4'} ({t:.1f}s)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
