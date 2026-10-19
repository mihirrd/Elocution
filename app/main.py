"""FastAPI server: serves the web UI and the analysis API."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import recognizer
from .feedback import analyze, phrase_pronunciation
from .lexicon import tokenize
from .phones import tokens_to_heard
from .sentences import PRACTICE

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="American Accent Coach")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.on_event("startup")
def warm_models() -> None:
    # Load the models in the background so the first analysis isn't slow.
    def load():
        recognizer.phoneme_recognizer()
        recognizer.transcriber()

    threading.Thread(target=load, daemon=True).start()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    return {"phoneme_model": "phoneme" in recognizer._models, "whisper_model": "whisper" in recognizer._models}


@app.get("/api/sentences")
def sentences():
    return PRACTICE


@app.get("/api/pronounce")
def pronounce(text: str):
    if not tokenize(text):
        raise HTTPException(400, "Enter at least one word.")
    return phrase_pronunciation(text)


def _run_analysis(data: bytes, target: str) -> dict:
    audio, offset = recognizer.load_audio(data)
    if len(audio) < recognizer.SAMPLE_RATE * 0.3:
        raise ValueError("The recording is too short or silent. Try again a little closer to the microphone.")

    transcript = recognizer.transcriber().transcribe(audio)
    tokens = recognizer.phoneme_recognizer().recognize(audio)
    heard = tokens_to_heard(tokens)

    mode = "target" if target.strip() else "free"
    text = target if mode == "target" else transcript
    if not tokenize(text):
        raise ValueError("I couldn't understand any words. Please speak a full sentence clearly.")

    result = analyze(text, heard)
    result["mode"] = mode
    result["transcript"] = transcript
    result["audio_offset"] = offset

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
