"""FastAPI server: serves the web UI and the analysis API."""

from __future__ import annotations

import asyncio
import base64
import hmac
import json
import os
import time
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import recognizer, tts
from .feedback import analyze, phrase_pronunciation
from .lexicon import tokenize
from .phones import tokens_to_heard
from .acoustics import Acoustics
from .segment import word_spans
from .sentences import PRACTICE

STATIC = Path(__file__).resolve().parent.parent / "static"
# Every recording and what the recognizers heard is kept here (locally) so mistakes can be
# investigated and turned into test cases. Set ACCENT_SAVE_DIR="" to turn this off.
SAVE_DIR = os.environ.get("ACCENT_SAVE_DIR", str(STATIC.parent / "recordings"))

# When the app is reachable from the internet, ACCENT_PASSWORD puts every page and API call
# behind the browser's built-in login box (HTTP Basic auth; any user name works). Unset: open.
PASSWORD = os.environ.get("ACCENT_PASSWORD", "")

app = FastAPI(title="Leviosa: American Accent Coach")


@app.middleware("http")
async def require_password(request: Request, call_next):
    if PASSWORD:
        supplied = ""
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("basic "):
            try:
                supplied = base64.b64decode(auth[6:]).decode("utf-8").partition(":")[2]
            except (ValueError, UnicodeDecodeError):
                supplied = ""
        if not hmac.compare_digest(supplied.encode(), PASSWORD.encode()):
            return Response("Password required.", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Leviosa", charset="UTF-8"'})
    return await call_next(request)


@app.middleware("http")
async def revalidate_ui(request: Request, call_next):
    # Make browsers check for a newer page, script and stylesheet on every load (a cheap
    # "not modified" reply when nothing changed), so an update shows up without a hard refresh.
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def warm_models() -> None:
    # Load the models in the background so the first analysis isn't slow.
    def load():
        recognizer.phoneme_recognizer()
        recognizer.detail_recognizer()
        speaker()
        recognizer.transcriber()

    threading.Thread(target=load, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    loaded = recognizer._models
    return {"phoneme_model": "phoneme" in loaded and "detail" in loaded, "whisper_model": "whisper" in loaded,
            "voice": "tts" in loaded}


@app.get("/api/sentences")
def sentences():
    return PRACTICE


@app.get("/api/pronounce")
def pronounce(text: str):
    if not tokenize(text):
        raise HTTPException(400, "Enter at least one word.")
    return phrase_pronunciation(text)


def speaker() -> tts.Speaker:
    return recognizer._get("tts", tts.Speaker)


@app.get("/api/speak")
async def speak(text: str):
    """A natural American voice reading `text`, as a WAV file."""
    text = text.strip()
    if not text or len(text) > 1000:
        raise HTTPException(400, "Text must be 1-1000 characters.")
    data = await asyncio.to_thread(lambda: speaker().wav(text))
    return Response(data, media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})


def recognize(audio):
    """Run both phoneme recognizers. Returns (primary heard, detail heard, detail log probs)."""
    heard = tokens_to_heard(recognizer.phoneme_recognizer().recognize(audio))
    detail_tokens, detail_log_probs = recognizer.detail_recognizer().recognize(audio, with_log_probs=True)
    return heard, tokens_to_heard(detail_tokens), detail_log_probs


def score(audio, text: str, heard, detail, detail_log_probs) -> tuple[dict, list[dict]]:
    """Score a recording against `text`. Returns (result, acoustic measurements as rows)."""
    detail_rec = recognizer.detail_recognizer()
    acoustics = Acoustics(audio, recognizer.SAMPLE_RATE, detail_log_probs, detail_rec.vocab,
                          detail_rec.blank, detail_rec.frame_sec)
    measurements: list[dict] = []

    def measure(chosen, words):
        m = acoustics.measure(chosen, words)
        measurements.extend(_flatten(m, chosen, words))
        return m

    return analyze(text, heard, detail_heard=detail, measure=measure), measurements


def _run_analysis(data: bytes, target: str) -> dict:
    audio, _ = recognizer.load_audio(data)
    if len(audio) < recognizer.SAMPLE_RATE * 0.3:
        raise ValueError("The recording is too short or silent. Try again a little closer to the microphone.")

    # Run the PyTorch models before Whisper: loading ctranslate2 (Whisper) before torch can
    # deadlock their thread pools on macOS.
    heard, detail, detail_log_probs = recognize(audio)
    transcript = recognizer.transcriber().transcribe(audio)

    mode = "target" if target.strip() else "free"
    text = target if mode == "target" else transcript
    if not tokenize(text):
        raise ValueError("I couldn't understand any words. Please speak a full sentence clearly.")

    result, measurements = score(audio, text, heard, detail, detail_log_probs)
    _save(data, target, transcript, heard, detail, result, measurements)
    result["mode"] = mode
    result["transcript"] = transcript
    # Where each word is, for "play your version". Times are on the analyzed (trimmed) audio,
    # which is sent back so the UI plays clips on exactly the same timeline.
    detail_rec = recognizer.detail_recognizer()
    spans = word_spans(
        detail_log_probs, detail_rec.vocab, detail_rec.blank, detail_rec.frame_sec,
        [w["arpabet"].split() if w.get("known") else None for w in result["words"]],
        len(audio) / recognizer.SAMPLE_RATE,
    )
    for w, span in zip(result["words"], spans):
        w["start"], w["end"] = span if span else (None, None)
    result["audio_wav"] = recognizer.to_wav_base64(audio)

    if mode == "target":
        said = {w.lower() for w in tokenize(transcript)}
        for w in result["words"]:
            w["understood"] = w["word"].lower() in said
    return result


def _save(data: bytes, target: str, transcript: str, heard, detail, result: dict,
          measurements: list[dict]) -> None:
    if not SAVE_DIR:
        return
    folder = Path(SAVE_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    stem = time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"
    (folder / f"{stem}.audio").write_bytes(data)
    record = {
        "target": target, "transcript": transcript,
        "primary_heard": " ".join(h.ipa for h in heard),
        "detail_heard": " ".join(h.ipa for h in detail),
        "measurements": measurements,
        "result": {k: v for k, v in result.items() if k != "audio_wav"},
    }
    (folder / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")


def _flatten(m: dict[str, dict[int, float]], chosen: list[tuple[int, str]], words: list[str]) -> list[dict]:
    """Acoustic measurements as rows: {word, word_index, phone, kind, value}."""
    rows = []
    for kind, by_index in m.items():
        for i, value in sorted(by_index.items()):
            wi, phone = chosen[i]
            rows.append({"word": words[wi], "word_index": wi, "phone": phone, "kind": kind, "value": value})
    return rows


@app.post("/api/analyze")
async def analyze_audio(audio: UploadFile = File(...), target: str = Form("")):
    data = await audio.read()
    if not data:
        raise HTTPException(400, "Empty recording.")
    try:
        return await asyncio.to_thread(_run_analysis, data, target)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


def run() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
