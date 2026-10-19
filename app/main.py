"""FastAPI server: serves the web UI and the analysis API."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import recognizer, tts
from .feedback import analyze, phrase_pronunciation
from .lexicon import tokenize
from .phones import tokens_to_heard
from .segment import word_spans
from .sentences import PRACTICE

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="American Accent Coach")
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
async def speak(text: str, slow: bool = False):
    """A natural American voice reading `text`, as a WAV file."""
    text = text.strip()
    if not text or len(text) > 1000:
        raise HTTPException(400, "Text must be 1-1000 characters.")
    data = await asyncio.to_thread(lambda: speaker().wav(text, "slow" if slow else "normal"))
    return Response(data, media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})


def _run_analysis(data: bytes, target: str) -> dict:
    audio, _ = recognizer.load_audio(data)
    if len(audio) < recognizer.SAMPLE_RATE * 0.3:
        raise ValueError("The recording is too short or silent. Try again a little closer to the microphone.")

    # Run the PyTorch models before Whisper: loading ctranslate2 (Whisper) before torch can
    # deadlock their thread pools on macOS.
    heard = tokens_to_heard(recognizer.phoneme_recognizer().recognize(audio))
    detail_rec = recognizer.detail_recognizer()
    detail_tokens, detail_log_probs = detail_rec.recognize(audio, with_log_probs=True)
    detail = tokens_to_heard(detail_tokens)
    transcript = recognizer.transcriber().transcribe(audio)

    mode = "target" if target.strip() else "free"
    text = target if mode == "target" else transcript
    if not tokenize(text):
        raise ValueError("I couldn't understand any words. Please speak a full sentence clearly.")

    result = analyze(text, heard, detail_heard=detail)
    result["mode"] = mode
    result["transcript"] = transcript
    # Where each word is, for "play your version". Times are on the analyzed (trimmed) audio,
    # which is sent back so the UI plays clips on exactly the same timeline.
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
