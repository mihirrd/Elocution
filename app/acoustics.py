"""Acoustic checks for accent features the phoneme recognizers can't hear reliably.

The recognizers' labels come from dictionaries, not from listening, so they call a
non-American R an "R" and an unaspirated T a "T". These features have well-known physical
signatures, measured here on each sound's position in the recording (found by forced alignment):

- R color: the American R pulls the third formant (F3) down sharply, to about 0.65-0.80 of the
  speaker's usual F3; a tapped, rolled, or flat R leaves it near 0.85-1.0. Comparing with the
  same speaker's vowels makes this work for any voice.
- Aspiration: an American P, T or K before a stressed vowel ("pin", "time", "attack") is
  released with a puff of air, so the voicing of the vowel starts 50-90 ms after the release
  (voice onset time, VOT). Unaspirated stops (Indian, Spanish, French...) start voicing within
  about 10-35 ms.
"""

from __future__ import annotations

import numpy as np

from .lexicon import base, is_vowel, stress
from .segment import _token_ids, forced_align

# F3 during R / ER as a fraction of the speaker's median vowel F3.
CLEAR_R = 0.80     # at or below: a clear American R
NO_R_COLOR = 0.84  # at or above: the American R quality is missing

# Voice onset time of P / T / K before a stressed vowel, in milliseconds.
# F2 during an L after a vowel ("feel", "milk", "all") as a fraction of the speaker's median
# vowel F2. The American "dark" L pulls the tongue back and F2 down; a clear L keeps it high.
# Set from CMU ARCTIC American vs Indian English speakers (see dark_l_positions).
DARK_L = 0.70   # at or below: an American dark L (American speakers: median 0.62, 75% below 0.68)
CLEAR_L = 0.80  # at or above: a clear L (Indian English: median 0.94, 75% above 0.80)

# V / W: how much more likely the detail recognizer finds the "wrong" lip sound than the right
# one at that position (log probability ratio, a goodness-of-pronunciation score). The
# recognizer's final label leans toward the dictionary, but its frame probabilities still hear
# the Indian ʋ (between V and W). At or above: flagged. Calibrated on CMU ARCTIC Americans
# (W median -6.4, 90% below -5.3; V median -6.6, 90% below -5.7) against L2-ARCTIC Hindi
# speakers annotated as saying V for W (median -0.6) or W for V (median -4.9).
GOP_COMPETITORS = {
    "W": (("w",), ("ʋ", "v", "β")),
    "V": (("v",), ("ʋ", "w", "β", "b", "bʰ")),
}
GOP_FLAG = {"W": -4.0, "V": -5.0}

# At or below: no puff of air. K is naturally aspirated longer than T, and T longer than P (in
# both accents), so each has its own threshold. Measured on CMU ARCTIC: American medians P 65,
# T 81, K 70 ms (25th percentiles 43 / 59 / 55); Indian English medians 23 / 23 / 37 ms.
UNASPIRATED = {"P": 30, "T": 35, "K": 40}

_VOWELS = {"AA", "AE", "AH", "AO", "EH", "IH", "IY", "UH", "UW", "EY", "AY", "OW", "AW", "OY"}
_STEP = 0.005
_WIDEN = 0.04  # the R color spreads into neighboring vowels; CTC spans are tight
_UNSTRESSED_WORDS = {"to"}  # usually reduced in connected speech, even by Americans


def aspiration_positions(words_phones: list[tuple[int, str]], stops: tuple[str, ...] = ("T",)) -> list[int]:
    """Indexes of the stops an American would aspirate: at the start of a word, or inside a word
    before a stressed vowel, and not after S ("stop" has no puff even in American English)."""
    out = []
    for i, (w, p) in enumerate(words_phones):
        if base(p) not in stops or i + 1 >= len(words_phones):
            continue
        nw, nxt = words_phones[i + 1]
        if nw != w or not is_vowel(nxt):
            continue  # word-final T, or T before a consonant
        word_initial = i == 0 or words_phones[i - 1][0] != w
        if not word_initial and (stress(nxt) != 1 or base(words_phones[i - 1][1]) == "S"):
            continue
        out.append(i)
    return out


def _ids(vocab: dict[str, int], tokens: tuple[str, ...]) -> list[int]:
    return [vocab[t] for t in tokens if t in vocab]


def dark_l_positions(words_phones: list[tuple[int, str]]) -> list[int]:
    """Indexes of the L's Americans make dark: after a vowel and not before a vowel in the same
    word ("feel", "milk", "all", "little"), as opposed to "light", "hello"."""
    out = []
    for i, (w, p) in enumerate(words_phones):
        if base(p) != "L" or i == 0 or words_phones[i - 1][0] != w:
            continue
        nxt = words_phones[i + 1] if i + 1 < len(words_phones) else None
        if nxt is not None and nxt[0] == w and is_vowel(nxt[1]):
            continue
        out.append(i)
    return out


class Acoustics:
    """Measurements on one recording. `measure(words_phones, words)` is what feedback.analyze
    calls with the utterance's expected phones."""

    def __init__(self, audio: np.ndarray, sample_rate: int, log_probs: np.ndarray, vocab: dict[str, int],
                 blank: int, frame_sec: float):
        import parselmouth

        self.audio, self.sr = audio, sample_rate
        self.log_probs, self.vocab, self.blank, self.frame_sec = log_probs, vocab, blank, frame_sec
        self.snd = parselmouth.Sound(audio.astype(np.float64), sample_rate)

    def measure(self, words_phones: list[tuple[int, str]], words: list[str]) -> dict[str, dict[int, float]]:
        """{"r_color": {phone index: F3 ratio}, "vot": {phone index: ms},
        "l_f2": {phone index: F2 ratio}, "vw_gop": {phone index: log ratio}}."""
        phones = [p for _, p in words_phones]
        targets = [_token_ids(p, self.vocab) for p in phones]
        keep = [i for i, t in enumerate(targets) if t]
        spans = forced_align(self.log_probs, [targets[i] for i in keep], self.blank) if keep else None
        if not spans:
            return {"r_color": {}, "vot": {}, "l_f2": {}, "vw_gop": {}}
        times = {i: (f0 * self.frame_sec, (f1 + 1) * self.frame_sec) for i, (f0, f1) in zip(keep, spans)}
        t_positions = [i for i in aspiration_positions(words_phones, stops=("P", "T", "K"))
                       if words[words_phones[i][0]].lower() not in _UNSTRESSED_WORDS]
        frames = dict(zip(keep, spans))
        return {"r_color": self._r_color(phones, times), "vot": self._vot(t_positions, times),
                "l_f2": self._l_f2(phones, dark_l_positions(words_phones), times),
                "vw_gop": self._gop(phones, frames)}

    def _gop(self, phones: list[str], frames: dict[int, tuple[int, int]]) -> dict[int, float]:
        """Competitor-vs-target log probability ratio for each V and W (see GOP_COMPETITORS)."""
        out = {}
        for i, (f0, f1) in frames.items():
            b = base(phones[i])
            if b not in GOP_COMPETITORS:
                continue
            target, rivals = (_ids(self.vocab, toks) for toks in GOP_COMPETITORS[b])
            if not target or not rivals:
                continue
            win = self.log_probs[max(0, f0 - 2): f1 + 3]
            out[i] = round(float(win[:, rivals].max() - win[:, target].max()), 2)
        return out

    def _formants(self):
        if not hasattr(self, "_fm"):
            self._fm = self.snd.to_formant_burg(time_step=_STEP, max_number_of_formants=5, maximum_formant=5000)
        return self._fm

    def _track(self, n: int, start: float, end: float) -> list[float]:
        """Formant `n` values between start and end, skipping frames where none was found."""
        fm = self._formants()
        vals = (fm.get_value_at_time(n, t) for t in np.arange(max(0.0, start), end, _STEP))
        return [v for v in vals if v == v]

    def _vowel_median(self, n: int, phones: list[str], times: dict[int, tuple[float, float]]) -> float | None:
        vals: list[float] = []
        for i, (s, e) in times.items():
            if base(phones[i]) in _VOWELS:
                vals += self._track(n, s, e)
        return float(np.median(vals)) if len(vals) >= 10 else None

    def _l_f2(self, phones: list[str], positions: list[int], times: dict[int, tuple[float, float]]) -> dict[int, float]:
        ref = self._vowel_median(2, phones, times) if positions else None
        if not ref:
            return {}
        out = {}
        for i in positions:
            if i in times:
                s, e = times[i]
                vals = self._track(2, s - 0.02, e + 0.03)
                if len(vals) >= 3:
                    out[i] = round(float(np.median(vals)) / ref, 3)
        return out

    def _r_color(self, phones: list[str], times: dict[int, tuple[float, float]]) -> dict[int, float]:
        def f3(start: float, end: float) -> list[float]:
            return self._track(3, start, end)

        vowel_f3: list[float] = []
        for i, (s, e) in times.items():
            if base(phones[i]) in _VOWELS:
                vowel_f3 += f3(s, e)
        if len(vowel_f3) < 10:
            return {}
        ref = float(np.median(vowel_f3))
        out = {}
        for i, (s, e) in times.items():
            if base(phones[i]) in {"R", "ER"}:
                vals = f3(s - _WIDEN, e + _WIDEN)
                if len(vals) >= 3:
                    # A low percentile, not the minimum: one bad formant frame shouldn't decide.
                    out[i] = round(float(np.percentile(vals, 10)) / ref, 3)
        return out

    def _vot(self, positions: list[int], times: dict[int, tuple[float, float]]) -> dict[int, float]:
        if not positions:
            return {}
        import parselmouth

        # The release is the sharpest rise in high-frequency energy; voicing starts where the
        # pitch tracker first finds a pitch after it.
        hiss = parselmouth.praat.call(self.snd, "Filter (pass Hann band)", 2500, 8000, 100)
        hiss_db = hiss.to_intensity(minimum_pitch=200, time_step=0.001)
        pitch = self.snd.to_pitch_ac(time_step=0.002, pitch_floor=70, pitch_ceiling=500)
        out = {}
        for i in positions:
            if i not in times:
                continue
            s, e = times[i][0] - 0.06, times[i][1] + 0.14
            ts = np.arange(max(s, 0.0), e, 0.001)
            if len(ts) < 20:
                continue
            db = np.array([hiss_db.get_value(t) for t in ts], dtype=float)
            if np.all(np.isnan(db)):
                continue
            db = np.nan_to_num(db, nan=float(np.nanmin(db)))
            rise = np.diff(db)[: max(1, int(len(ts) * 0.7))]
            release = ts[int(np.argmax(rise))]
            closure = [pitch.get_value_at_time(t) for t in np.arange(release - 0.025, release - 0.004, 0.002)]
            if closure and all(v == v for v in closure):
                continue  # voicing never stopped: no real closure found, so no reliable release
            voiced = next((t for t in np.arange(release + 0.003, e + 0.1, 0.002)
                           if pitch.get_value_at_time(t) == pitch.get_value_at_time(t)), None)
            if voiced is not None:
                out[i] = round((voiced - release) * 1000)
        return out
