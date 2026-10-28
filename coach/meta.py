"""Thin client for the Meta Model API, with retries and a hard spend cap.

Meta's billing has no hard cap (its Spend Limit only sends an email), so every paid
call goes through `Ledger.charge`, which refuses to start a call once the cap is spent (#20).
Access was flaky during the event (`model_not_found` on about half of calls), so every
call retries on that and on 429/5xx with backoff (#3).
"""

from __future__ import annotations

import base64
import contextvars
import io
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests

BASE_URL = os.environ.get("META_BASE_URL", "https://api.meta.ai/v1")
SPARK = "muse-spark-1.3"
SPARK_OPEN = "meta-models/muse-spark-open"  # Meta's open-weights Muse Spark, hosted by Baseten
BASETEN_URL = os.environ.get("BASETEN_BASE_URL", "https://inference.baseten.co/v1")
SAM = "sam-3.1"
IMAGE = "muse-image-1.0"

# List prices, Standard mode (dev.meta.ai/docs/pricing-rate-limits, read 2026-10-28).
PRICE_IN_PER_M = 1.25
PRICE_CACHED_IN_PER_M = 0.15
PRICE_OUT_PER_M = 4.25  # reasoning tokens are billed as output
PRICE_SAM_IMAGE = 0.0025
PRICE_IMAGE_GEN = 0.01

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


class SpendCapReached(RuntimeError):
    pass


class MetaAPIError(RuntimeError):
    pass


class Ledger:
    """Running total of estimated spend, persisted so the cap survives restarts."""

    def __init__(self, path: Path, cap_usd: float):
        self.path = path
        self.cap = cap_usd
        self.lock = threading.Lock()
        self.total = 0.0
        if path.exists():
            try:
                self.total = float(json.loads(path.read_text()).get("total_usd", 0.0))
            except (ValueError, OSError):
                self.total = 0.0

    def check(self, expected: float = 0.0) -> None:
        with self.lock:
            if self.total + expected > self.cap:
                raise SpendCapReached(
                    f"spend cap ${self.cap:.2f} reached (spent ${self.total:.4f})"
                )

    def charge(self, usd: float) -> None:
        meter = METER.get()
        if meter is not None:
            meter.add(usd)
        with self.lock:
            self.total += usd
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"total_usd": round(self.total, 6), "cap_usd": self.cap}))


class Meter:
    """Spend of one run, even when several runs share the ledger at once."""

    def __init__(self) -> None:
        self.usd = 0.0
        self.lock = threading.Lock()

    def add(self, usd: float) -> None:
        with self.lock:
            self.usd += usd


METER: contextvars.ContextVar[Meter | None] = contextvars.ContextVar("meter", default=None)


class Pool(ThreadPoolExecutor):
    """A thread pool whose tasks keep the caller's context, so their spend lands on its Meter."""

    def submit(self, fn, /, *args, **kwargs):
        ctx = contextvars.copy_context()
        return super().submit(ctx.run, fn, *args, **kwargs)


LEDGER = Ledger(
    Path(os.environ.get("SPEND_LEDGER", ROOT / "out" / "spend.json")),
    float(os.environ.get("SPEND_CAP_USD", "60")),
)


@dataclass
class CallStats:
    model: str
    seconds: float
    usd: float
    attempts: int
    tokens_in: int = 0
    tokens_out: int = 0


def _key() -> str:
    key = os.environ.get("META_MODEL_API_KEY") or os.environ.get("MODEL_API_KEY")
    if not key:
        raise MetaAPIError("META_MODEL_API_KEY is not set (put it in .env)")
    return key


def open_weights_available() -> bool:
    """True when a Baseten key is configured, so Muse Spark Open can be called."""
    return bool(os.environ.get("BASETEN_API_KEY"))


def _retryable(status: int, body: str) -> bool:
    return status in (408, 409, 429, 500, 502, 503, 504) or (
        status == 404 and "model_not_found" in body
    )


def post(path: str, payload: dict, *, stream: bool = False, attempts: int = 14,
         timeout: float = 180.0, base_url: str | None = None,
         key: str | None = None) -> tuple[requests.Response, int]:
    headers = {"Authorization": f"Bearer {key or _key()}", "Content-Type": "application/json"}
    if stream:
        headers["Accept"] = "text/event-stream"
    delay = 1.0
    last = ""
    for i in range(1, attempts + 1):
        try:
            r = requests.post(f"{base_url or BASE_URL}{path}", headers=headers, json=payload,
                              stream=stream, timeout=timeout)
        except requests.RequestException as e:
            last = f"network: {e}"
        else:
            if r.status_code == 200:
                return r, i
            body = r.text[:500]
            last = f"HTTP {r.status_code}: {body}"
            if not _retryable(r.status_code, body):
                raise MetaAPIError(last)
        time.sleep(delay)
        delay = min(delay * 1.7, 10.0)
    raise MetaAPIError(f"gave up after {attempts} attempts: {last}")


def image_data_url(img) -> str:
    """PIL image or path or bytes -> base64 data URL (PNG)."""
    from PIL import Image

    if isinstance(img, (str, Path)):
        img = Image.open(img)
    elif isinstance(img, bytes):
        img = Image.open(io.BytesIO(img))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def chat(messages: list[dict], *, schema: dict | None = None, schema_name: str = "out",
         effort: str = "low", max_tokens: int = 8000, model: str = SPARK) -> tuple[object, CallStats]:
    """Muse Spark over Chat Completions. Returns parsed JSON when `schema` is given, else text."""
    LEDGER.check(0.01)
    payload: dict = {
        "model": model,
        "messages": messages,
        "reasoning_effort": effort,
        "max_completion_tokens": max_tokens,
    }
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        }
    t0 = time.time()
    r, n = post("/chat/completions", payload)
    data = r.json()
    usage = data.get("usage") or {}
    tin = int(usage.get("prompt_tokens") or 0)
    cached = int((usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
    tout = int(usage.get("completion_tokens") or 0)
    usd = ((tin - cached) * PRICE_IN_PER_M + cached * PRICE_CACHED_IN_PER_M
           + tout * PRICE_OUT_PER_M) / 1e6
    LEDGER.charge(usd)
    stats = CallStats(model, time.time() - t0, usd, n, tin, tout)
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if schema is None:
        return content, stats
    if not content:
        raise MetaAPIError("empty structured reply (raise max_tokens or lower effort)")
    return json.loads(content), stats


# Baseten bills Muse Spark Open from its own credits, not Meta's, so it has its own ledger.
# Prices are estimates for the cap only (override with BASETEN_PRICE_IN / BASETEN_PRICE_OUT).
OPEN_PRICE_IN_PER_M = float(os.environ.get("BASETEN_PRICE_IN", "0.60"))
OPEN_PRICE_OUT_PER_M = float(os.environ.get("BASETEN_PRICE_OUT", "2.40"))
OPEN_LEDGER = Ledger(ROOT / "out" / "spend-baseten.json", float(os.environ.get("BASETEN_CAP_USD", "60")))


def _json_from_text(text: str):
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):]
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        raise MetaAPIError(f"no JSON in reply: {text[:120]!r}")
    return json.loads(t[start:end + 1])


def open_chat(messages: list[dict], *, schema: dict | None = None, schema_name: str = "out",
              effort: str = "low", max_tokens: int = 8000) -> tuple[object, CallStats]:
    """Muse Spark Open (open weights) on Baseten, OpenAI-compatible Chat Completions.

    Asks for structured output; if the provider rejects the schema, asks for plain JSON instead."""
    key = os.environ.get("BASETEN_API_KEY")
    if not key:
        raise MetaAPIError("BASETEN_API_KEY is not set (put it in .env)")
    OPEN_LEDGER.check(0.01)
    payload: dict = {"model": SPARK_OPEN, "messages": messages, "max_tokens": max_tokens,
                     "reasoning_effort": effort}
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": schema, "strict": True},
        }
    t0 = time.time()
    try:
        r, n = post("/chat/completions", payload, base_url=BASETEN_URL, key=key, attempts=6)
    except MetaAPIError as e:
        if schema is None or "HTTP 4" not in str(e):
            raise
        payload.pop("response_format", None)
        payload.pop("reasoning_effort", None)
        payload["messages"] = messages + [{"role": "user", "content":
                                           "Reply with only a JSON object matching this schema: "
                                           + json.dumps(schema)}]
        r, n = post("/chat/completions", payload, base_url=BASETEN_URL, key=key, attempts=6)
    data = r.json()
    usage = data.get("usage") or {}
    tin = int(usage.get("prompt_tokens") or 0)
    tout = int(usage.get("completion_tokens") or 0)
    usd = (tin * OPEN_PRICE_IN_PER_M + tout * OPEN_PRICE_OUT_PER_M) / 1e6
    OPEN_LEDGER.charge(usd)
    stats = CallStats(SPARK_OPEN, time.time() - t0, usd, n, tin, tout)
    content = (data["choices"][0]["message"].get("content") or "").strip()
    if schema is None:
        return content, stats
    return _json_from_text(content), stats


def user_msg(text: str, *images) -> dict:
    parts: list[dict] = [{"type": "text", "text": text}]
    for im in images:
        parts.append({"type": "image_url", "image_url": {"url": image_data_url(im)}})
    return {"role": "user", "content": parts}


def segment(image, prompt: str, *, confidence: bool = True) -> tuple[str, CallStats]:
    """SAM 3.1 over the Responses API (streamed). Returns the raw special-token text."""
    LEDGER.check(PRICE_SAM_IMAGE)
    payload = {
        "model": SAM,
        "input": [{
            "type": "message",
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": image_data_url(image)},
            ],
        }],
        "metadata": {"mask_encoding": "one_bit", **({"include_confidence": "true"} if confidence else {})},
        "stream": True,
    }
    t0 = time.time()
    r, n = post("/responses", payload, stream=True)
    out = []
    for raw in r.iter_lines(decode_unicode=False):
        if not raw:
            continue
        line = raw.decode("utf-8", errors="replace")
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break
        ev = json.loads(data)
        if ev.get("type") == "response.output_text.delta":
            out.append(ev.get("delta") or "")
        elif ev.get("type") in ("response.failed", "error"):
            raise MetaAPIError(f"SAM stream error: {json.dumps(ev)[:300]}")
    LEDGER.charge(PRICE_SAM_IMAGE)
    return "".join(out), CallStats(SAM, time.time() - t0, PRICE_SAM_IMAGE, n)


def generate_image(prompt: str, *, size: str = "1024x1024") -> tuple[bytes, CallStats]:
    """Muse Image single-shot generation. Returns image bytes."""
    LEDGER.check(PRICE_IMAGE_GEN)
    t0 = time.time()
    r, n = post("/images/generations",
                {"model": IMAGE, "prompt": prompt, "n": 1, "size": size}, timeout=300)
    b64 = r.json()["data"][0]["b64_json"]
    LEDGER.charge(PRICE_IMAGE_GEN)
    return base64.b64decode(b64), CallStats(IMAGE, time.time() - t0, PRICE_IMAGE_GEN, n)
