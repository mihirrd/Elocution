"""Read the IPA used in the connected-speech reference ("[ˈwɑɾɚ]", "[ɡʊd̚ deɪ]", "[ən], [n̩]")
and turn it into what the app needs: Kokoro phonemes for the voice, ARPAbet for scoring.

One source for display, voice and scoring, so the three can't drift apart."""

from __future__ import annotations

import re

DIPHTHONGS = ("eɪ", "aɪ", "aʊ", "oʊ", "ɔɪ", "tʃ", "dʒ")
VOWELS = {"i", "ɪ", "eɪ", "ɛ", "æ", "ɑ", "ɔ", "oʊ", "ʊ", "u", "ʌ", "ə", "ɚ", "ɝ", "aɪ", "aʊ", "ɔɪ", "a", "o", "e"}
REDUCED = {"ə", "ɚ"}

TO_KOKORO = {"eɪ": "A", "aɪ": "I", "aʊ": "W", "oʊ": "O", "ɔɪ": "Y", "tʃ": "ʧ", "dʒ": "ʤ",
             "ɝ": "ɜɹ", "ɚ": "əɹ", "r": "ɹ", "g": "ɡ", "a": "ɑ", "o": "O", "e": "A"}
TO_ARPA = {
    "i": "IY", "ɪ": "IH", "eɪ": "EY", "ɛ": "EH", "æ": "AE", "ɑ": "AA", "ɔ": "AO", "oʊ": "OW", "ʊ": "UH",
    "u": "UW", "ʌ": "AH", "ə": "AH", "ɚ": "ER", "ɝ": "ER", "aɪ": "AY", "aʊ": "AW", "ɔɪ": "OY",
    "a": "AA", "o": "OW", "e": "EY",
    "p": "P", "b": "B", "t": "T", "d": "D", "k": "K", "ɡ": "G", "g": "G", "f": "F", "v": "V",
    "θ": "TH", "ð": "DH", "s": "S", "z": "Z", "ʃ": "SH", "ʒ": "ZH", "tʃ": "CH", "dʒ": "JH",
    "h": "HH", "m": "M", "n": "N", "ŋ": "NG", "l": "L", "ɹ": "R", "r": "R", "j": "Y", "w": "W",
    "ɾ": "DX", "ʔ": "T",  # a glottal stop is the T said as a catch; scoring accepts it (see casual)
}


def forms(text: str) -> list[str]:
    """Every bracketed form in a reference cell: "[ən], [n̩]" -> ["ən", "n̩"]. For "A → B" only
    the result counts. Optional parts in parentheses give two forms: "[kæn(ʔ)]" -> kæn, kænʔ."""
    if "→" in text:
        text = text.split("→")[-1]
    out = []
    for f in re.findall(r"\[([^\]]+)\]", text):
        if "(" in f:
            out += [re.sub(r"\(([^)]*)\)", "", f), re.sub(r"[()]", "", f)]
        else:
            out.append(f)
    return out


def tokens(ipa: str) -> list[str]:
    """Split IPA into sounds and marks: "ˈwɑɾɚ" -> ["ˈ", "w", "ɑ", "ɾ", "ɚ"]. Kept marks:
    ˈ ˌ (stress), "." (syllable), " " (word), ː (held), "̩" (syllabic, joined to its consonant)."""
    out: list[str] = []
    k = 0
    while k < len(ipa):
        two = ipa[k:k + 2]
        if two in DIPHTHONGS:
            out.append(two)
            k += 2
            continue
        c = ipa[k]
        k += 1
        if c == "̩" and out:
            out[-1] += c  # syllabic n / l
        elif c in "̚ʰ'’":
            continue  # unreleased / aspiration marks: not spoken differently by the voice or scorer
        elif c.strip() or c == " ":
            out.append(c)
    return out


def _words(ipa: str) -> list[list[str]]:
    words, cur = [], []
    for t in tokens(ipa):
        if t == " ":
            if cur:
                words.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        words.append(cur)
    return words


def to_kokoro(ipa: str) -> str:
    """Kokoro (misaki) phonemes: stress marks move from the syllable start to just before the
    vowel, diphthongs become misaki's letters, syllabic n / l become ᵊn / ᵊl."""
    parts = []
    for word in _words(ipa):
        out, pending = [], ""
        for t in word:
            if t in "ˈˌ":
                pending = t
            elif t == ".":
                continue
            elif t.endswith("̩"):
                out.append(pending + "ᵊ" + TO_KOKORO.get(t[0], t[0]))
                pending = ""
            elif t in VOWELS:
                out.append(pending + TO_KOKORO.get(t, t))
                pending = ""
            else:
                out.append(TO_KOKORO.get(t, t))
        parts.append("".join(out))
    return " ".join(parts)


def to_arpabet(ipa: str) -> list[str]:
    """ARPAbet with stress for scoring. A word written without stress marks has its full vowels
    stressed (content words like [nɛks deɪ]); ə / ɚ are always unstressed; a held sound (ː) is
    one sound; a syllabic n / l is the consonant alone."""
    out: list[str] = []
    for word in _words(ipa):
        marked = any(t in "ˈˌ" for t in word)
        pending = None
        for t in word:
            if t in "ˈˌ":
                pending = "1" if t == "ˈ" else "2"
            elif t in ".ː":
                continue
            elif t.endswith("̩"):
                out.append(TO_ARPA[t[0]])
            elif t in VOWELS:
                if t in REDUCED:
                    st = "0"
                else:
                    st = pending or ("0" if marked else "1")
                out.append(TO_ARPA[t] + st)
                pending = None
            elif t in TO_ARPA:
                out.append(TO_ARPA[t])
    return out
