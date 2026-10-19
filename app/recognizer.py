"""Speech models: a phoneme recognizer (what sounds you actually made) and Whisper
(which words an American listener would understand)."""

from __future__ import annotations

import json
import os
import subprocess
import threading

import numpy as np

SAMPLE_RATE = 16_000
PHONEME_MODEL = os.environ.get("ACCENT_PHONEME_MODEL", "facebook/wav2vec2-lv-60-espeak-cv-ft")
WHISPER_MODEL = os.environ.get("ACCENT_WHISPER_MODEL", "small.en")

_lock = threading.Lock()


def load_audio(data: bytes) -> tuple[np.ndarray, float]:
    """Decode any audio container (webm/ogg/wav/m4a...) to mono 16 kHz float32 via ffmpeg.

    Returns the silence-trimmed audio and the offset (seconds) of the trimmed start."""
    proc = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", "pipe:0",
         "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "pipe:1"],
        input=data, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise ValueError(f"Could not decode audio: {proc.stderr.decode(errors='ignore').strip()}")
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    return trim_silence(audio)


def trim_silence(audio: np.ndarray, threshold: float = 0.01, pad: float = 0.15) -> tuple[np.ndarray, float]:
    frame = int(0.02 * SAMPLE_RATE)
    n = len(audio) // frame
    if n == 0:
        return audio, 0.0
    rms = np.sqrt((audio[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    loud = np.nonzero(rms > max(threshold, rms.max() * 0.05))[0]
    if loud.size == 0:
        return audio, 0.0
    p = int(pad * SAMPLE_RATE)
    start = max(0, loud[0] * frame - p)
    return audio[start : min(len(audio), (loud[-1] + 1) * frame + p)], start / SAMPLE_RATE


def _device():
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class PhonemeRecognizer:
    def __init__(self, model_name: str = PHONEME_MODEL):
        import torch
        from huggingface_hub import hf_hub_download
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        self.torch = torch
        self.extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_name).eval()
        self.device = _device()
        try:
            self.model.to(self.device)
        except Exception:
            self.device = "cpu"
        vocab = json.load(open(hf_hub_download(model_name, "vocab.json"), encoding="utf-8"))
        self.id_to_token = {i: t for t, i in vocab.items()}
        self.blank = vocab.get("<pad>", 0)
        self.frame_sec = 0.02  # wav2vec2 emits one frame per 20 ms

    def recognize(self, audio: np.ndarray) -> list[tuple[str, float, float]]:
        """Return the sequence of (phoneme token, start sec, end sec) heard in the audio."""
        torch = self.torch
        inputs = self.extractor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
        with torch.inference_mode():
            logits = self.model(inputs.input_values.to(self.device)).logits[0].float().cpu()
        ids = logits.argmax(dim=-1).tolist()

        tokens: list[tuple[str, float, float]] = []
        prev = None
        for f, i in enumerate(ids):
            if i != prev and i != self.blank:
                tokens.append((self.id_to_token.get(i, ""), f * self.frame_sec, (f + 1) * self.frame_sec))
            elif i == prev and i != self.blank and tokens:
                tok, s, _ = tokens[-1]
                tokens[-1] = (tok, s, (f + 1) * self.frame_sec)
            prev = i
        return [t for t in tokens if t[0] not in {"<s>", "</s>", "<unk>", " ", "|"}]


class Transcriber:
    def __init__(self, model_name: str = WHISPER_MODEL):
        from faster_whisper import WhisperModel

        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self.model.transcribe(
            audio, language="en", beam_size=5, vad_filter=False, condition_on_previous_text=False
        )
        return " ".join(s.text.strip() for s in segments).strip()


_models: dict[str, object] = {}


def _get(name: str, factory):
    with _lock:
        if name not in _models:
            _models[name] = factory()
        return _models[name]


def phoneme_recognizer() -> PhonemeRecognizer:
    return _get("phoneme", PhonemeRecognizer)


def transcriber() -> Transcriber:
    return _get("whisper", Transcriber)
