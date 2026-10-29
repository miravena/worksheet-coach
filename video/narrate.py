"""Render the voiceover with Kokoro TTS, one WAV per shot, plus timings for captions (#15).

Each line in shots.json is [spoken text, caption text]; an empty caption means "same as spoken".
Spoken text spells things the way the voice should say them ("G.E.D.", "three point one").

    KOKORO_DIR=/path/to/model-files python video/narrate.py out/video
Needs kokoro-onnx, soundfile, numpy and the Kokoro v1.0 model files (kokoro-v1.0.onnx,
voices-v1.0.bin). On ARM Linux, point ESPEAK_LIB / ESPEAK_DATA at the system espeak-ng.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

VOICE, SPEED, GAP, SHOT_TAIL = "af_heart", 0.95, 0.35, 0.6

lib = os.environ.get("ESPEAK_LIB", "/usr/lib/aarch64-linux-gnu/libespeak-ng.so.1")
data = os.environ.get("ESPEAK_DATA", "/usr/lib/aarch64-linux-gnu/espeak-ng-data")
import phonemizer.backend.espeak.api as espeak_api  # noqa: E402

_init = espeak_api.EspeakAPI.__init__
espeak_api.EspeakAPI.__init__ = lambda self, l, d: _init(self, l, data)  # the wheel's data path is wrong
from kokoro_onnx import EspeakConfig, Kokoro  # noqa: E402


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    kdir = Path(os.environ["KOKORO_DIR"])
    k = Kokoro(str(kdir / "kokoro-v1.0.onnx"), str(kdir / "voices-v1.0.bin"),
               espeak_config=EspeakConfig(lib, data))
    shots = json.loads((Path(__file__).parent / "shots.json").read_text())
    timing = []
    for shot in shots:
        parts, t, caps = [], 0.0, []
        for spoken, caption in shot["lines"]:
            audio, rate = k.create(spoken, voice=VOICE, speed=SPEED, lang="en-us")
            dur = len(audio) / rate
            caps.append({"start": round(t, 2), "end": round(t + dur, 2), "text": caption or spoken})
            parts += [audio, np.zeros(int(rate * GAP), dtype=audio.dtype)]
            t += dur + GAP
        parts.append(np.zeros(int(rate * SHOT_TAIL), dtype=parts[0].dtype))
        t += SHOT_TAIL
        sf.write(out / f"{shot['id']}.wav", np.concatenate(parts), rate)
        timing.append({"id": shot["id"], "seconds": round(t, 2), "captions": caps})
        print(f"{shot['id']:<9} {t:5.1f}s")
    (out / "narration.json").write_text(json.dumps(timing, indent=1))
    print(f"total {sum(s['seconds'] for s in timing):.1f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
