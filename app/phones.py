"""Map the recognizer's (multilingual, espeak-style) IPA tokens onto American English phones,
and score how close a heard sound is to an expected one."""

from __future__ import annotations

from dataclasses import dataclass

from .lexicon import base, stress

# espeak token -> sequence of ARPAbet base phones.
TOKEN_TO_ARPA: dict[str, list[str]] = {
    "p": ["P"], "b": ["B"], "t": ["T"], "d": ["D"], "k": ["K"], "ɡ": ["G"], "g": ["G"],
    "f": ["F"], "v": ["V"], "θ": ["TH"], "ð": ["DH"], "s": ["S"], "z": ["Z"], "ʃ": ["SH"],
    "ʒ": ["ZH"], "h": ["HH"], "tʃ": ["CH"], "dʒ": ["JH"], "m": ["M"], "n": ["N"], "ŋ": ["NG"],
    "l": ["L"], "ɫ": ["L"], "ɹ": ["R"], "w": ["W"], "j": ["Y"], "ɾ": ["DX"], "ʔ": ["Q"],
    "i": ["IY"], "iː": ["IY"], "ɪ": ["IH"], "ᵻ": ["IH"], "ɛ": ["EH"], "æ": ["AE"],
    "ɑ": ["AA"], "ɑː": ["AA"], "ɔ": ["AO"], "ɔː": ["AO"], "ʊ": ["UH"], "u": ["UW"], "uː": ["UW"],
    "ʌ": ["AH"], "ə": ["AH"], "ɐ": ["AH"], "ɚ": ["ER"], "ɜ": ["ER"], "ɜː": ["ER"],
    "eɪ": ["EY"], "aɪ": ["AY"], "aʊ": ["AW"], "oʊ": ["OW"], "ɔɪ": ["OY"], "oɪ": ["OY"],
    "əl": ["AH", "L"], "l̩": ["AH", "L"], "n̩": ["AH", "N"], "ts": ["T", "S"],
    "ɑːɹ": ["AA", "R"], "ɔːɹ": ["AO", "R"], "oːɹ": ["AO", "R"], "ɛɹ": ["EH", "R"],
    "ɪɹ": ["IH", "R"], "ʊɹ": ["UH", "R"], "aɪɚ": ["AY", "ER"], "aɪə": ["AY", "AH"],
    "iə": ["IY", "AH"], "ju": ["Y", "UW"],
}

# Non-American sounds the recognizer can hear, with the English phone(s) they stand in for
# and how far off they are (0 = perfect, 1 = clearly wrong). These are accent markers.
FOREIGN_NEAREST: dict[str, dict[str, float]] = {
    "r": {"R": 0.55, "DX": 0.2},        # trilled / tapped R
    "ʁ": {"R": 0.6}, "ʀ": {"R": 0.6}, "ɽ": {"R": 0.5, "D": 0.5}, "ɻ": {"R": 0.3},
    "ʈ": {"T": 0.45}, "ɖ": {"D": 0.45}, "ɳ": {"N": 0.3}, "ɭ": {"L": 0.3},
    "t̪": {"T": 0.4, "TH": 0.6}, "d̪": {"D": 0.4, "DH": 0.6}, "s̪": {"S": 0.2},
    "ʋ": {"V": 0.5, "W": 0.5}, "β": {"V": 0.5, "B": 0.5},
    "x": {"HH": 0.55, "K": 0.6}, "χ": {"HH": 0.6}, "ç": {"HH": 0.5, "SH": 0.6}, "ħ": {"HH": 0.4},
    "ɣ": {"G": 0.5}, "ɸ": {"F": 0.4}, "ɕ": {"SH": 0.4}, "ʑ": {"ZH": 0.4}, "tɕ": {"CH": 0.4},
    "dʑ": {"JH": 0.4}, "ɲ": {"N": 0.5}, "ʎ": {"L": 0.5}, "c": {"K": 0.4}, "ɟ": {"G": 0.4},
    "kʰ": {"K": 0.0}, "pʰ": {"P": 0.0}, "tʰ": {"T": 0.0},
    "e": {"EY": 0.35, "EH": 0.4}, "eː": {"EY": 0.35, "EH": 0.4}, "e̞": {"EY": 0.4, "EH": 0.3},
    "o": {"OW": 0.35, "AO": 0.4}, "oː": {"OW": 0.35, "AO": 0.4}, "o̞": {"OW": 0.4},
    "a": {"AA": 0.3, "AE": 0.45, "AH": 0.45}, "aː": {"AA": 0.25}, "ä": {"AA": 0.3, "AH": 0.45},
    "ɒ": {"AA": 0.3, "AO": 0.3}, "əʊ": {"OW": 0.3}, "eə": {"EH": 0.4}, "ɛː": {"EH": 0.3},
    "y": {"UW": 0.6, "IY": 0.6}, "yː": {"UW": 0.6}, "ø": {"ER": 0.6, "UH": 0.6},
    "œ": {"ER": 0.6, "AH": 0.6}, "ɨ": {"IH": 0.4, "AH": 0.4}, "ʉ": {"UW": 0.4},
    "ɯ": {"UW": 0.5, "UH": 0.5}, "ɵ": {"UH": 0.5, "AH": 0.5}, "ɪː": {"IH": 0.3}, "ʊː": {"UH": 0.3},
    "æː": {"AE": 0.1}, "ɑ̃": {"AA": 0.5}, "ɔ̃": {"AO": 0.5}, "ɛ̃": {"EH": 0.5}, "õ": {"OW": 0.5},
    "ĩ": {"IY": 0.5}, "ũ": {"UW": 0.5}, "ã": {"AA": 0.5},
}

# Plain names for non-English sounds (accent markers).
FOREIGN_NAMES = {
    "r": "rolled r", "ʁ": "throat r", "ʀ": "throat r", "ɽ": "flapped r", "ɻ": "curled r",
    "ʈ": "curled-back t", "ɖ": "curled-back d", "ɳ": "curled-back n", "ɭ": "curled-back l",
    "t̪": "t on the teeth", "d̪": "d on the teeth", "ʋ": "sound between v and w", "β": "soft b",
    "x": "scratchy h", "χ": "scratchy h", "ç": "hissing h", "ɣ": "soft g", "ɸ": "soft f",
    "ɲ": "ny", "ʎ": "ly", "e": "flat e (no glide)", "eː": "flat e (no glide)",
    "o": "flat o (no glide)", "oː": "flat o (no glide)", "ɒ": "British o", "əʊ": "British o",
    "a": "open a", "aː": "long open a", "y": "French u", "ø": "French eu", "œ": "French eu",
}


def unit_name(unit: str, reduced: bool = False) -> tuple[str, str | None]:
    """Simple (name, example word) for a heard unit."""
    from .lexicon import sound_name

    if unit.startswith("~"):
        ipa = unit[1:]
        return (FOREIGN_NAMES.get(ipa, "non-English sound"), None)
    return sound_name(unit + ("0" if reduced and unit in {"AH", "ER"} else ""))


def heard_respelling(heard: list["Heard"]) -> str:
    """Respell what was heard in the same plain-English style as the correct pronunciation."""
    from .lexicon import to_respelling

    units = []
    for h in heard:
        if h.foreign:
            near = FOREIGN_NEAREST.get(h.ipa)
            options = {k: v for k, v in (near or {}).items() if k != "DX"} or near
            if options:
                units.append(min(options, key=options.get))
        elif h.unit != "Q":
            units.append(h.unit)
    return to_respelling(units, caps=False) if units else ""


VOICING_PAIRS = {
    frozenset(p) for p in [("P", "B"), ("T", "D"), ("K", "G"), ("F", "V"), ("TH", "DH"),
                           ("S", "Z"), ("SH", "ZH"), ("CH", "JH")]
}
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
REDUCED = {"AH", "IH", "UH", "ER"}  # acceptable realizations of an unstressed (reduced) vowel


@dataclass
class Heard:
    """One sound unit the recognizer heard."""
    unit: str        # ARPAbet base, "DX", "Q", or "~<ipa>" for a non-English sound
    ipa: str         # what the model actually emitted (for display)
    start: float     # seconds
    end: float

    @property
    def foreign(self) -> bool:
        return self.unit.startswith("~")


def tokens_to_heard(tokens: list[tuple[str, float, float]]) -> list[Heard]:
    """Convert (token, start, end) triples from the recognizer into Heard units."""
    out: list[Heard] = []
    for tok, s, e in tokens:
        arpa = TOKEN_TO_ARPA.get(tok)
        if arpa:
            step = (e - s) / len(arpa)
            for i, a in enumerate(arpa):
                out.append(Heard(a, tok if len(arpa) == 1 else _piece_ipa(a), s + i * step, s + (i + 1) * step))
        elif tok.strip() and tok not in {"<pad>", "<s>", "</s>", "<unk>", "??"}:
            out.append(Heard("~" + tok, tok, s, e))
    return out


def _piece_ipa(arpa: str) -> str:
    from .lexicon import ARPA_TO_IPA
    return ARPA_TO_IPA.get(arpa, arpa)


def is_vowel_unit(unit: str) -> bool:
    if unit.startswith("~"):
        near = FOREIGN_NEAREST.get(unit[1:], {})
        return any(k in VOWELS for k in near)
    return unit in VOWELS


def substitution_cost(expected: str, heard: str, next_expected: str | None = None, flap_ok: bool = False) -> float:
    """Cost of hearing `heard` (a Heard.unit) where `expected` (ARPAbet with stress) was due.

    0 means correct (including accepted American variants), ~0.3-0.5 is an accent-level
    deviation, and >=0.6 is a real mispronunciation.
    """
    exp = base(expected)
    st = stress(expected)

    if heard == exp:
        return 0.0
    if heard.startswith("~"):
        near = FOREIGN_NEAREST.get(heard[1:])
        if near and exp in near:
            return near[exp]
        return 1.0 if is_vowel_unit(heard) == (exp in VOWELS) else 1.8

    # Accepted American variants.
    if heard == "DX" and exp in {"T", "D"}:
        return 0.0
    if flap_ok and exp == "T" and heard == "D":
        return 0.0  # flap T between vowels, often heard as a D ("sit in" -> si-din)
    if heard == "Q" and exp == "T":
        return 0.1  # glottal T ("button", "that one")
    if {exp, heard} == {"AA", "AO"}:
        return 0.1  # cot-caught merger is normal in much of the US
    if st == 0 and exp in VOWELS and heard in REDUCED | {"IY"}:
        return 0.1  # unstressed vowels reduce
    if exp == "IY" and st == 0 and heard == "IH":
        return 0.1
    if exp in {"ER"} and heard == "R":
        return 0.2

    exp_v, heard_v = exp in VOWELS, heard in VOWELS
    if exp_v != heard_v:
        return 1.8  # vowel <-> consonant: never treat as a substitution
    if frozenset((exp, heard)) in VOICING_PAIRS:
        if exp == "Z" and heard == "S" and next_expected is None:
            return 0.3  # final Z devoicing is mild
        return 0.65
    if exp_v:
        return 0.8
    return 0.9


def rhotic_pair_cost(expected: str, first: str, second: str) -> float | None:
    """Cost of an expected r-colored vowel (ER) heard as vowel + R ("ə ɹ", "ɜ ɹ").

    The recognizer often splits /ɚ/ in two; that is still a correct American R."""
    if base(expected) != "ER" or second != "R":
        return None
    if first in {"ER", "AH"}:
        return 0.0
    if first in {"EH", "UH", "IH"}:
        return 0.3
    return None


def deletion_cost(expected: str, prev_expected: str | None = None, next_expected: str | None = None,
                  word_final: bool = False) -> float:
    if word_final and next_expected and (
        base(next_expected) == base(expected) or frozenset((base(expected), base(next_expected))) in VOICING_PAIRS
    ):
        return 0.1  # "please sit", "this seat": same consonant across words merges into one
    if base(expected) == "DH" and prev_expected and base(prev_expected) in {"T", "D", "N", "Z", "S", "L"}:
        return 0.4  # "visited the", "in the": DH assimilates in connected speech
    if base(expected) in {"HH"} or (stress(expected) == 0 and base(expected) == "AH"):
        return 0.7
    return 1.0


def insertion_cost(heard: str) -> float:
    if heard in {"Q"}:
        return 0.1
    if heard in {"HH", "Y", "W"}:
        return 0.6
    return 0.8
