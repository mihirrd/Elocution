"""Find where each word is in the recording, for playing back "your version" of a word.

The words' expected phones are force-aligned to the recognizer's frame-by-frame probabilities
(CTC Viterbi), so every word gets a position even if some of its sounds were dropped, and
stray sounds can't drag a boundary into the wrong word."""

from __future__ import annotations

import numpy as np

from .lexicon import base

# Recognizer tokens (espeak vocabulary) that can realize each American phone.
ALTERNATIVES = {
    "IY": ["i", "iː"], "IH": ["ɪ", "ᵻ", "i"], "EY": ["eɪ", "e", "eː"], "EH": ["ɛ", "e"],
    "AE": ["æ", "a"], "AA": ["ɑ", "ɑː", "ɑːɹ", "a", "aː"], "AO": ["ɔ", "ɔː", "ɔːɹ", "oːɹ", "ɑː"],
    "OW": ["oʊ", "o", "oː", "əʊ"], "UH": ["ʊ", "ʊɹ"], "UW": ["u", "uː", "ju"],
    "AH": ["ʌ", "ə", "ɐ", "əl"], "ER": ["ɚ", "ɜ", "ɜː", "ə"], "AY": ["aɪ", "aɪɚ", "aɪə"],
    "AW": ["aʊ"], "OY": ["ɔɪ", "oɪ"],
    "T": ["t", "ɾ", "ʔ", "ts"], "D": ["d", "ɾ"], "R": ["ɹ", "r", "ɚ"], "L": ["l", "əl", "ɫ"],
    "Y": ["j", "ju"], "G": ["ɡ"], "HH": ["h"], "CH": ["tʃ"], "JH": ["dʒ"], "NG": ["ŋ"],
}


def _token_ids(phone: str, vocab: dict[str, int]) -> list[int]:
    from .lexicon import ARPA_TO_IPA

    b = base(phone)
    cands = ALTERNATIVES.get(b, [ARPA_TO_IPA.get(b, "")])
    return [vocab[c] for c in cands if c in vocab]


def forced_align(log_probs: np.ndarray, targets: list[list[int]], blank: int) -> list[tuple[int, int]] | None:
    """CTC Viterbi alignment. `targets[k]` is the set of token ids allowed for the k-th phone.

    Returns the (first frame, last frame) each phone occupies, or None if it can't fit."""
    T, L = log_probs.shape[0], len(targets)
    if L == 0 or T < L:
        return None
    # Emission score per phone per frame: best of its allowed tokens.
    emit = np.stack([log_probs[:, ids].max(axis=1) for ids in targets], axis=1)  # T x L
    blank_lp = log_probs[:, blank]
    S = 2 * L + 1  # blank, phone0, blank, phone1, ..., blank
    NEG = -1e30
    score = np.full(S, NEG)
    back = np.zeros((T, S), dtype=np.int8)  # 0 = stay, 1 = from s-1, 2 = from s-2
    score[0] = blank_lp[0]
    score[1] = emit[0, 0]
    is_phone = np.arange(S) % 2 == 1
    phone_idx = np.arange(S) // 2
    # Skipping a blank is allowed between phones (even when consecutive phones share a token,
    # since they're separate phones).
    can_skip = is_phone & (np.arange(S) >= 2)
    for t in range(1, T):
        stay = score
        step1 = np.concatenate(([NEG], score[:-1]))
        step2 = np.where(can_skip, np.concatenate(([NEG, NEG], score[:-2])), NEG)
        stacked = np.stack([stay, step1, step2])
        choice = stacked.argmax(axis=0)
        best = stacked.max(axis=0)
        frame = np.where(is_phone, emit[t, np.minimum(phone_idx, L - 1)], blank_lp[t])
        score = best + frame
        back[t] = choice
    end = S - 1 if score[S - 1] >= score[S - 2] else S - 2
    if score[end] <= NEG / 2:
        return None
    spans: list[list[int]] = [[-1, -1] for _ in range(L)]
    s = end
    for t in range(T - 1, -1, -1):
        if s % 2 == 1:
            k = s // 2
            spans[k][0] = t
            if spans[k][1] < 0:
                spans[k][1] = t
        s -= int(back[t, s]) if t > 0 else 0
    return [tuple(sp) for sp in spans]


def word_spans(log_probs: np.ndarray, vocab: dict[str, int], blank: int, frame_sec: float,
               words_phones: list[list[str] | None], duration: float,
               max_pad: float = 0.15) -> list[tuple[float, float] | None]:
    """(start, end) seconds for each word, ready to cut a clip from the analyzed audio.

    Boundaries between neighboring words sit in the middle of the gap between them; at a pause,
    each side gets at most `max_pad` of silence."""
    targets, owner = [], []
    for wi, phones in enumerate(words_phones):
        for p in phones or []:
            ids = _token_ids(p, vocab)
            if ids:
                targets.append(ids)
                owner.append(wi)
    spans = forced_align(log_probs, targets, blank)
    if spans is None:
        return [None] * len(words_phones)

    raw: list[list[float] | None] = [None] * len(words_phones)
    for (f0, f1), wi in zip(spans, owner):
        s, e = f0 * frame_sec, (f1 + 1) * frame_sec
        if raw[wi] is None:
            raw[wi] = [s, e]
        else:
            raw[wi][0], raw[wi][1] = min(raw[wi][0], s), max(raw[wi][1], e)

    known = [i for i, r in enumerate(raw) if r]
    out: list[tuple[float, float] | None] = [None] * len(words_phones)
    for n, i in enumerate(known):
        s, e = raw[i]
        prev_end = raw[known[n - 1]][1] if n > 0 else None
        next_start = raw[known[n + 1]][0] if n + 1 < len(known) else None
        start = max((prev_end + s) / 2, s - max_pad) if prev_end is not None else max(0.0, s - max_pad)
        end = min((e + next_start) / 2, e + max_pad) if next_start is not None else min(duration, e + max_pad)
        out[i] = (round(start, 3), round(end, 3))
    return out
