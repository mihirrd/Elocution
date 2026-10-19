"""Natural American voice for "Listen" (Kokoro-82M, Apache-2.0, runs locally).

Kokoro is given phonemes rather than text, built from the same American pronunciations the
coach scores against (CMUdict + the flap rule), so the voice says exactly what it teaches."""

from __future__ import annotations

import io
import os
import re
import threading
import wave
from collections import OrderedDict
from types import SimpleNamespace

import numpy as np

from .lexicon import american_surface, base, is_vowel, lookup, number_to_words, stress

MODEL_REPO = "hexgrad/Kokoro-82M"
VOICE = os.environ.get("ACCENT_VOICE", "af_heart")  # American English voices start with "a"
SAMPLE_RATE = 24_000
SPEEDS = {"normal": 0.95, "slow": 0.7}
MAX_PHONEMES = 500  # Kokoro's limit is 510 per chunk

# ARPAbet -> Kokoro's (misaki) American phoneme alphabet.
ARPA_TO_KOKORO = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "W", "AY": "I", "EH": "ɛ", "ER": "ɜɹ",
    "EY": "A", "IH": "ɪ", "IY": "i", "OW": "O", "OY": "Y", "UH": "ʊ", "UW": "u",
    "B": "b", "CH": "ʧ", "D": "d", "DH": "ð", "DX": "ɾ", "F": "f", "G": "ɡ", "HH": "h",
    "JH": "ʤ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ",
    "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w", "Y": "j", "Z": "z",
    "ZH": "ʒ",
}

# Said without stress in running speech.
FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for", "by", "with",
    "from", "as", "is", "are", "was", "were", "be", "it", "its", "i", "you", "he", "she", "we",
    "they", "me", "him", "her", "us", "them", "my", "your", "his", "our", "their", "that",
    "than", "can", "could", "would", "should", "will", "do", "does", "have", "has", "had",
}


def word_to_kokoro(phones: list[str], stressed: bool = True) -> str:
    """'water' W AO1 DX ER0 -> 'wˈɔɾəɹ'."""
    out = []
    for i, p in enumerate(phones):
        b, st = base(p), stress(p)
        if b == "AH" and st == 0:
            # Syllabic L at the end of a word: little -> lˈɪɾᵊl
            sym = "ᵊ" if i == len(phones) - 2 and base(phones[-1]) == "L" else "ə"
        elif b == "ER" and st == 0:
            sym = "əɹ"
        else:
            sym = ARPA_TO_KOKORO[b]
        final_y = b == "IY" and i == len(phones) - 1  # thirty: θˈɜɹɾi, no stress on -y
        if stressed and is_vowel(p) and st in (1, 2) and not final_y:
            sym = ("ˈ" if st == 1 else "ˌ") + sym
        out.append(sym)
    return "".join(out)


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*|\d+|[.,!?;:—…]")

_fallback = None


def _espeak(word: str) -> str:
    """Pronounce a word missing from the dictionary with espeak (bundled with misaki)."""
    global _fallback
    if _fallback is None:
        from misaki.espeak import EspeakFallback

        _fallback = EspeakFallback(british=False)
    ps, _ = _fallback(SimpleNamespace(text=word))
    return ps or ""


def text_to_kokoro(text: str) -> str:
    parts: list[str] = []
    for tok in _TOKEN_RE.findall(text):
        if tok in ".,!?;:—…":
            if parts:
                parts[-1] += tok
            continue
        words = number_to_words(int(tok)).split() if tok.isdigit() else [tok.replace("’", "'")]
        for w in words:
            phones = lookup(w)
            if phones:
                multi = sum(is_vowel(p) for p in phones) > 1
                parts.append(word_to_kokoro(american_surface(phones), multi or w.lower() not in FUNCTION_WORDS))
            else:
                parts.append(_espeak(w))
    return " ".join(p for p in parts if p)


def _chunks(ps: str) -> list[str]:
    """Split a long phoneme string at punctuation (then spaces) to stay under Kokoro's limit."""
    if len(ps) <= MAX_PHONEMES:
        return [ps]
    out, cur = [], ""
    for piece in re.split(r"(?<=[.,!?;:—…]) ", ps):
        while len(piece) > MAX_PHONEMES:
            cut = piece.rfind(" ", 0, MAX_PHONEMES)
            cut = cut if cut > 0 else MAX_PHONEMES
            out.append(piece[:cut]); piece = piece[cut:].lstrip()
        if cur and len(cur) + 1 + len(piece) > MAX_PHONEMES:
            out.append(cur); cur = piece
        else:
            cur = f"{cur} {piece}".strip()
    if cur:
        out.append(cur)
    return out


class Speaker:
    def __init__(self, voice: str = VOICE):
        import torch
        from huggingface_hub import hf_hub_download
        from kokoro.model import KModel

        self.torch = torch
        self.model = KModel(repo_id=MODEL_REPO).eval()
        self.voice = torch.load(hf_hub_download(MODEL_REPO, f"voices/{voice}.pt"), weights_only=True)
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, str], bytes] = OrderedDict()

    def wav(self, text: str, speed: str = "normal") -> bytes:
        """Speak `text` and return a WAV file. Results are cached (most recent 200)."""
        key = (text.strip(), speed)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            pieces = []
            for ps in _chunks(text_to_kokoro(text)):
                if not ps:
                    continue
                ref_s = self.voice[min(len(ps), len(self.voice)) - 1]
                with self.torch.inference_mode():
                    audio = self.model(ps, ref_s, SPEEDS[speed])
                pieces.append(audio.float().cpu().numpy())
                pieces.append(np.zeros(int(0.12 * SAMPLE_RATE), dtype=np.float32))
            data = _encode(np.concatenate(pieces) if pieces else np.zeros(1, dtype=np.float32))
            self._cache[key] = data
            if len(self._cache) > 200:
                self._cache.popitem(last=False)
            return data


def _encode(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()
