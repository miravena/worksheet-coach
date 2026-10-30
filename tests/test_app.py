"""Guards on the web app: token, upload limits, file serving, rate limit (#9, #20)."""

import io
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app as webapp


@pytest.fixture(autouse=True)
def stub_pipeline(monkeypatch):
    from coach import pipeline

    def fake_run(img, on_step=None, practice=True):
        on_step({"t": 0.1, "model": "code", "action": "photo received"})
        return {"score": {"correct": 1, "total": 1}, "steps": [], "verdicts": []}

    monkeypatch.setattr(pipeline, "run", fake_run)
    monkeypatch.setattr(webapp.meta.LEDGER, "total", 0.0)
    webapp.IP_RUNS.clear()
    monkeypatch.delenv("DEMO_TOKEN", raising=False)
    monkeypatch.delenv("REPLAY", raising=False)


def png_bytes(size=(40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "PNG")
    return buf.getvalue()


client = TestClient(webapp.app)


def test_run_streams_step_then_done():
    r = client.post("/api/run", files={"file": ("a.png", png_bytes(), "image/png")})
    assert r.status_code == 200
    jid = r.json()["job"]
    body = client.get(f"/api/jobs/{jid}/events").text
    assert "event: step" in body and "event: done" in body
    assert client.get(f"/api/jobs/{jid}/image").headers["content-type"] == "image/jpeg"


def test_rejects_non_image_and_oversize():
    assert client.post("/api/run", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 400
    big = b"0" * (webapp.MAX_UPLOAD + 10)
    assert client.post("/api/run", files={"file": ("a.png", big, "image/png")}).status_code == 413


def test_demo_token(monkeypatch):
    monkeypatch.setenv("DEMO_TOKEN", "s3cret")
    f = {"file": ("a.png", png_bytes(), "image/png")}
    assert client.post("/api/run", files=f).status_code == 401
    assert client.post("/api/run?token=s3cret", files=f).status_code == 200


def test_per_ip_limit(monkeypatch):
    monkeypatch.setenv("RUNS_PER_IP_PER_HOUR", "2")
    codes = [client.post("/api/run", files={"file": ("a.png", png_bytes(), "image/png")}).status_code
             for _ in range(3)]
    time.sleep(0.3)
    assert codes == [200, 200, 429]


def test_spend_cap_gives_503(monkeypatch):
    monkeypatch.setattr(webapp.meta.LEDGER, "total", webapp.meta.LEDGER.cap)
    r = client.post("/api/run", files={"file": ("a.png", png_bytes(), "image/png")})
    assert r.status_code == 503


def test_files_only_under_practice():
    assert client.get("/files/spend.json").status_code == 404
    assert client.get("/files/practice/../spend.json").status_code == 404
    assert client.get("/files/practice/nope.pdf").status_code == 404


def test_without_a_key_samples_replay_from_the_committed_runs(monkeypatch):
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setattr(webapp, "CACHE_DIR", webapp.ROOT / "no-such-cache")
    r = client.post("/api/run?sample=ws13")
    assert r.status_code == 200 and r.json()["replay"] is True
    body = client.get(f"/api/jobs/{r.json()['job']}/events").text
    assert "event: done" in body
    pdf = next(webapp.REPLAY_DIR.glob("practice-*.pdf")).name
    assert client.get(f"/files/practice/{pdf}").status_code == 200
    assert client.get("/files/practice/../ws13.json").status_code == 404
