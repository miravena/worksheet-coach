"""Web app for the worksheet coach (#9, #16): upload a photo, watch the agent work live over
Server-Sent Events, then read the diagnosis and practice problems.

Run:  uvicorn app:app --port 8000      (or: python app.py)

Environment (all optional):
  RUNS_PER_IP_PER_HOUR  per-IP run limit, default 5            (#20)
  MAX_CONCURRENT_RUNS   global concurrent pipeline runs, default 2
  RUN_COST_ESTIMATE     USD assumed per run for the spend-cap check, default 0.30
  DEMO_TOKEN            if set, /api/run needs it as ?token= or the X-Demo-Token header
  REPLAY=1              replay out/cache/<sample>.json for sample runs instead of calling the API
  TRUST_PROXY=1         take the client IP from X-Forwarded-For (only behind a proxy you control)
"""

from __future__ import annotations

import asyncio
import hmac
import io
import json
import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

from coach import meta

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
PRACTICE_DIR = OUT / "practice"
CACHE_DIR = OUT / "cache"
SAMPLES_DIR = ROOT / "tests" / "worksheets"
WEB_DIR = ROOT / "web"

MAX_UPLOAD = 8 * 1024 * 1024
MAX_SIDE = 2200
JOB_TTL = 3600
MAX_JOBS = 60

try:  # phone photos are often HEIC; only works when the optional package is installed
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:
    pass

app = FastAPI(title="worksheet-coach", docs_url=None, redoc_url=None)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Job:
    def __init__(self, image_jpeg: bytes):
        self.id = uuid.uuid4().hex[:12]
        self.created = time.time()
        self.image = image_jpeg
        self.events: list[dict] = []  # {"event": "step"|"done"|"error", "data": {...}}
        self.finished = False
        self.lock = threading.Lock()

    def emit(self, event: str, data: dict) -> None:
        with self.lock:
            self.events.append({"event": event, "data": data})
            if event in ("done", "error"):
                self.finished = True


JOBS: dict[str, Job] = {}
JOBS_LOCK = threading.Lock()
IP_RUNS: dict[str, list[float]] = {}
ACTIVE = 0
ACTIVE_LOCK = threading.Lock()


def _client_ip(request: Request) -> str:
    if os.environ.get("TRUST_PROXY") == "1":
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_token(request: Request) -> None:
    want = os.environ.get("DEMO_TOKEN", "")
    if not want:
        return
    got = request.query_params.get("token") or request.headers.get("x-demo-token") or ""
    if not hmac.compare_digest(got.encode(), want.encode()):
        raise HTTPException(401, "This demo needs an access code. Ask the person who shared the link.")


def _check_ip_budget(ip: str) -> None:
    limit = _env_int("RUNS_PER_IP_PER_HOUR", 5)
    now = time.time()
    with JOBS_LOCK:
        recent = [t for t in IP_RUNS.get(ip, []) if now - t < 3600]
        if len(recent) >= limit:
            IP_RUNS[ip] = recent
            raise HTTPException(
                429, f"Limit reached: {limit} worksheets per hour from one connection. Try again later.")
        recent.append(now)
        IP_RUNS[ip] = recent


def _prune_jobs() -> None:
    now = time.time()
    with JOBS_LOCK:
        for jid in [j for j, job in JOBS.items() if now - job.created > JOB_TTL]:
            del JOBS[jid]
        while len(JOBS) > MAX_JOBS:
            del JOBS[min(JOBS, key=lambda j: JOBS[j].created)]


def _prepare_image(raw: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(400, "That file is not an image I can read. Try a JPEG or PNG photo.")
    img = ImageOps.exif_transpose(img).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        s = MAX_SIDE / max(w, h)
        img = img.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return img


def _jpeg(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _sample_path(name: str) -> Path:
    """A sample sheet: its phone-photo version when one exists (closer to real use), else the page."""
    if not name.isalnum():
        raise HTTPException(404, "Unknown sample.")
    photo = SAMPLES_DIR / f"{name}_photo.jpg"
    if photo.is_file():
        return photo
    p = SAMPLES_DIR / f"{name}.png"
    if not p.is_file():
        raise HTTPException(404, "Unknown sample.")
    return p


# The samples offered on the page: a spread of topics, layouts and adult use cases.
DEMO_SAMPLES = [s for s in os.environ.get(
    "DEMO_SAMPLES", "ws01,ws13,ws12,ws16,ws28,ws22,ws05,ws08").split(",") if s]


def _run_live(job: Job, img: Image.Image, sample: str | None) -> None:
    global ACTIVE
    try:
        from coach import pipeline

        def on_step(s: dict) -> None:
            job.emit("step", s)

        result = pipeline.run(img, on_step=on_step, practice=True)
        if sample:
            try:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                (CACHE_DIR / f"{sample}.json").write_text(json.dumps(result))
            except OSError:
                pass
        job.emit("done", result)
    except meta.SpendCapReached:
        job.emit("error", {"message": "The demo's spend cap has been reached, so it is paused."})
    except Exception as e:  # surface a calm message; the detail stays short
        job.emit("error", {"message": f"The run failed: {str(e)[:300]}"})
    finally:
        with ACTIVE_LOCK:
            ACTIVE -= 1


def _run_replay(job: Job, sample: str) -> None:
    try:
        cached = json.loads((CACHE_DIR / f"{sample}.json").read_text())
        prev = 0.0
        for s in cached.get("steps", []):
            t = float(s.get("t", prev) or prev)
            time.sleep(min(0.9, max(0.15, (t - prev) * 0.25)))
            prev = t
            job.emit("step", s)
        job.emit("done", cached)
    except Exception as e:
        job.emit("error", {"message": f"Replay failed: {str(e)[:200]}"})


@app.get("/api/config")
def config() -> dict:
    return {"token_required": bool(os.environ.get("DEMO_TOKEN")),
            "max_upload_mb": MAX_UPLOAD // (1024 * 1024)}


@app.get("/api/samples")
def samples() -> list[dict]:
    out = []
    for p in [SAMPLES_DIR / f"{n}.png" for n in DEMO_SAMPLES if (SAMPLES_DIR / f"{n}.png").is_file()]:
        title = p.stem
        meta_file = p.with_suffix(".json")
        if meta_file.exists():
            try:
                title = json.loads(meta_file.read_text()).get("title", title)
            except (ValueError, OSError):
                pass
        out.append({"id": p.stem, "title": title,
                    "cached": (CACHE_DIR / f"{p.stem}.json").exists()})
    return out


@app.get("/api/samples/{name}/image")
def sample_image(name: str) -> FileResponse:
    p = _sample_path(name)
    return FileResponse(p, media_type="image/jpeg" if p.suffix == ".jpg" else "image/png")


@app.post("/api/run")
async def run(request: Request, sample: str | None = None, file: UploadFile | None = File(None)):
    global ACTIVE
    _check_token(request)
    _prune_jobs()

    replay = bool(sample) and os.environ.get("REPLAY") == "1" and (CACHE_DIR / f"{sample}.json").exists()

    if sample:
        img = _prepare_image(_sample_path(sample).read_bytes())
    else:
        if file is None:
            raise HTTPException(400, "Attach a photo of the worksheet.")
        raw = await file.read(MAX_UPLOAD + 1)
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, f"That photo is larger than {MAX_UPLOAD // (1024 * 1024)} MB.")
        img = _prepare_image(raw)

    job = Job(_jpeg(img))

    if replay:  # no API calls, so no per-IP, concurrency or spend checks
        with JOBS_LOCK:
            JOBS[job.id] = job
        threading.Thread(target=_run_replay, args=(job, sample), daemon=True).start()
        return {"job": job.id, "replay": True}

    try:
        meta.LEDGER.check(float(os.environ.get("RUN_COST_ESTIMATE", "0.30")))
    except meta.SpendCapReached:
        return JSONResponse(
            {"detail": "The demo has reached its spending limit and is paused. "
                       "Please come back later, or watch the recorded walkthrough."},
            status_code=503)

    _check_ip_budget(_client_ip(request))
    with ACTIVE_LOCK:
        if ACTIVE >= _env_int("MAX_CONCURRENT_RUNS", 2):
            raise HTTPException(503, "The coach is busy with other worksheets. Try again in a minute.")
        ACTIVE += 1
    with JOBS_LOCK:
        JOBS[job.id] = job
    threading.Thread(target=_run_live, args=(job, img, sample), daemon=True).start()
    return {"job": job.id, "replay": False}


def _job(job_id: str) -> Job:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(404, "Unknown or expired job.")
    return job


@app.get("/api/jobs/{job_id}/image")
def job_image(job_id: str) -> Response:
    return Response(_job(job_id).image, media_type="image/jpeg",
                    headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str, request: Request) -> StreamingResponse:
    job = _job(job_id)

    async def stream():
        i = 0
        idle = 0.0
        while True:
            with job.lock:
                batch = job.events[i:]
                finished = job.finished
            for ev in batch:
                i += 1
                yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"
                idle = 0.0
            if finished and not batch:
                return
            if await request.is_disconnected():
                return
            await asyncio.sleep(0.2)
            idle += 0.2
            if idle >= 15:
                idle = 0.0
                yield ": keepalive\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/files/{path:path}")
def files(path: str) -> FileResponse:
    """Only files the pipeline wrote under out/practice/."""
    root = PRACTICE_DIR.resolve()
    target = (OUT / path).resolve()
    rel = path.split("/", 1)
    if rel[0] != "practice" or root not in target.parents or not target.is_file():
        raise HTTPException(404, "Not found.")
    return FileResponse(target)


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=_env_int("PORT", 8000))
