# Demo video build

Makes the 3-minute submission video from a live run of the app (#15). Output goes to
`out/video/` (not committed).

```sh
python3 -m uvicorn app:app --port 8011            # live: the run in the video is real
REPLAY=1 python3 -m uvicorn app:app --port 8012   # replay: for the second-sample card
KOKORO_DIR=<kokoro model files> python video/narrate.py out/video
python video/record.py http://localhost:8011 ws13 out/video
python video/cards.py http://localhost:8012 out/video
python video/assemble.py out/video                # -> out/video/worksheet-coach.mp4
```

`shots.json` holds each shot's narration as `[spoken, caption]` pairs: the spoken text spells
words the way the voice should say them ("G.E.D."), the caption is what appears on screen.
The picture is cut to the voice: footage longer than its line is sped up (and labelled so on
screen), shorter footage holds a frame.

Tools (video only, not app dependencies): [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)
voice model (Apache-2.0) via [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx) (MIT),
[Playwright](https://github.com/microsoft/playwright-python) (Apache-2.0),
[FFmpeg](https://ffmpeg.org) with libx264 and libass (GPL, run as a separate program, not
bundled), Poppler `pdftoppm` (GPL, same).
