"""American English pronunciation dictionary (CMUdict) plus IPA / respelling helpers.

Phones are represented as ARPAbet strings with stress digits on vowels, e.g. "AH0", "T".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

import cmudict

VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}

# General American IPA for each ARPAbet phone.
ARPA_TO_IPA = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "aɪ", "EH": "ɛ",
    "ER": "ɝ", "EY": "eɪ", "IH": "ɪ", "IY": "i", "OW": "oʊ", "OY": "ɔɪ", "UH": "ʊ",
    "UW": "u", "B": "b", "CH": "tʃ", "D": "d", "DH": "ð", "F": "f", "G": "ɡ", "HH": "h",
    "JH": "dʒ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ", "P": "p", "R": "ɹ",
    "S": "s", "SH": "ʃ", "T": "t", "TH": "θ", "V": "v", "W": "w", "Y": "j", "Z": "z",
    "ZH": "ʒ",
    # Surface-only phones produced by American allophony rules / the recognizer.
    "DX": "ɾ", "Q": "ʔ",
}

# Plain-English respelling chunks ("say it like...").
RESPELL = {
    "AA": "ah", "AE": "a", "AH": "uh", "AO": "aw", "AW": "ow", "AY": "eye", "EH": "eh",
    "ER": "ur", "EY": "ay", "IH": "ih", "IY": "ee", "OW": "oh", "OY": "oy", "UH": "uu",
    "UW": "oo", "B": "b", "CH": "ch", "D": "d", "DH": "th", "F": "f", "G": "g", "HH": "h",
    "JH": "j", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ng", "P": "p", "R": "r",
    "S": "s", "SH": "sh", "T": "t", "TH": "th", "V": "v", "W": "w", "Y": "y", "Z": "z",
    "ZH": "zh", "DX": "d",
}

# Simple name + example word for every American sound, for learners who don't read IPA.
SOUND_NAMES = {
    "IY": ("ee", "see"), "IH": ("i", "sit"), "EY": ("ay", "day"), "EH": ("e", "bed"),
    "AE": ("a", "cat"), "AA": ("ah", "father"), "AO": ("aw", "law"), "OW": ("oh", "go"),
    "UH": ("short oo", "book"), "UW": ("oo", "food"), "AH": ("u", "cup"), "ER": ("ur", "bird"),
    "AY": ("eye", "my"), "AW": ("ow", "now"), "OY": ("oy", "boy"),
    "P": ("p", "pen"), "B": ("b", "boy"), "T": ("t", "top"), "D": ("d", "dog"), "K": ("k", "cat"),
    "G": ("g", "go"), "F": ("f", "fun"), "V": ("v", "very"), "TH": ("th", "think"),
    "DH": ("th", "this"), "S": ("s", "see"), "Z": ("z", "zoo"), "SH": ("sh", "she"),
    "ZH": ("zh", "vision"), "CH": ("ch", "chair"), "JH": ("j", "jump"), "HH": ("h", "hat"),
    "M": ("m", "man"), "N": ("n", "no"), "NG": ("ng", "sing"), "L": ("l", "love"),
    "R": ("r", "red"), "W": ("w", "we"), "Y": ("y", "yes"), "DX": ("quick d", "water"),
    "Q": ("throat stop", "uh-oh"),
}


def sound_name(phone: str) -> tuple[str, str | None]:
    """('th', 'think') for TH; the weak unstressed vowel is ('uh', 'about')."""
    b = base(phone)
    if b == "AH" and stress(phone) == 0:
        return ("uh", "about")
    if b == "ER" and stress(phone) == 0:
        return ("ur", "teacher")
    return SOUND_NAMES.get(b, (b.lower(), None))


# Consonant clusters allowed at the start of an English syllable (for syllabification).
LEGAL_ONSETS = {
    ("P", "L"), ("P", "R"), ("B", "L"), ("B", "R"), ("T", "R"), ("D", "R"), ("K", "L"),
    ("K", "R"), ("G", "L"), ("G", "R"), ("F", "L"), ("F", "R"), ("TH", "R"), ("SH", "R"),
    ("S", "P"), ("S", "T"), ("S", "K"), ("S", "M"), ("S", "N"), ("S", "L"), ("S", "W"),
    ("T", "W"), ("D", "W"), ("K", "W"), ("G", "W"), ("P", "Y"), ("B", "Y"), ("F", "Y"),
    ("K", "Y"), ("M", "Y"), ("HH", "Y"), ("V", "Y"),
    ("S", "P", "R"), ("S", "T", "R"), ("S", "K", "R"), ("S", "P", "L"), ("S", "K", "W"),
}


def base(phone: str) -> str:
    """Strip the stress digit: 'AH0' -> 'AH'."""
    return phone.rstrip("012")


def stress(phone: str) -> int | None:
    return int(phone[-1]) if phone[-1].isdigit() else None


def is_vowel(phone: str) -> bool:
    return base(phone) in VOWELS


def phone_ipa(phone: str) -> str:
    b = base(phone)
    if b == "AH" and stress(phone) == 0:
        return "ə"
    if b == "ER" and stress(phone) == 0:
        return "ɚ"
    return ARPA_TO_IPA.get(b, phone)


@lru_cache(maxsize=1)
def _dict() -> dict[str, list[list[str]]]:
    return cmudict.dict()


_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_to_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else " " + _ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return _ONES[n // 100] + " hundred" + ("" if rest == 0 else " " + number_to_words(rest))
    if n < 1_000_000:
        rest = n % 1000
        return number_to_words(n // 1000) + " thousand" + ("" if rest == 0 else " " + number_to_words(rest))
    return " ".join(_ONES[int(d)] for d in str(n))


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*|\d+")


def tokenize(text: str) -> list[str]:
    """Split text into words, spelling out numbers ('3 cats' -> ['three', 'cats'])."""
    words: list[str] = []
    for tok in _TOKEN_RE.findall(text):
        if tok.isdigit():
            words.extend(number_to_words(int(tok)).split())
        else:
            words.append(tok.replace("’", "'"))
    return words


def _lookup_raw(word: str) -> list[str] | None:
    entries = _dict().get(word.lower())
    return list(entries[0]) if entries else None


def _lookup_morph(word: str, depth: int = 0) -> list[str] | None:
    """Fallback for words missing from CMUdict: strip a common suffix and rebuild."""
    w = word.lower()
    if depth > 2:
        return None
    suffixes = [
        ("'s", ["Z"]), ("s", ["Z"]), ("es", ["IH0", "Z"]), ("ed", ["D"]), ("ing", ["IH0", "NG"]),
        ("ly", ["L", "IY0"]), ("er", ["ER0"]), ("ers", ["ER0", "Z"]), ("ness", ["N", "AH0", "S"]),
    ]
    for suf, extra in suffixes:
        if w.endswith(suf) and len(w) > len(suf) + 2:
            root = w[: -len(suf)]
            candidates = [root, root + "e"] + ([root[:-1] + "y"] if root.endswith("i") else [])
            stem = next((p for c in candidates if (p := _lookup_raw(c))), None)
            if stem is None:
                stem = next((p for c in candidates if (p := _lookup_morph(c, depth + 1))), None)
            if stem:
                if suf in ("s", "'s") and base(stem[-1]) in {"P", "T", "K", "F", "TH"}:
                    extra = ["S"]
                if suf == "ed" and base(stem[-1]) in {"T", "D"}:
                    extra = ["IH0", "D"]
                elif suf == "ed" and base(stem[-1]) in {"P", "K", "F", "S", "SH", "CH", "TH"}:
                    extra = ["T"]
                return stem + extra
    return None


def lookup(word: str) -> list[str] | None:
    return _lookup_raw(word) or _lookup_morph(word)


def all_pronunciations(word: str) -> list[list[str]]:
    return [list(p) for p in _dict().get(word.lower(), [])]


def american_surface(phones: list[str]) -> list[str]:
    """Apply the American flap rule: T/D between a vowel (or R) and an unstressed vowel -> DX.

    'water' W AO1 T ER0 -> W AO1 DX ER0 ("WAH-der"); 'better', 'city', 'ladder' likewise.
    """
    out = list(phones)
    for i in range(1, len(out) - 1):
        if base(out[i]) in {"T", "D"}:
            prev, nxt = out[i - 1], out[i + 1]
            prev_ok = is_vowel(prev) or base(prev) == "R"
            if prev_ok and is_vowel(nxt) and stress(nxt) == 0:
                out[i] = "DX"
    return out


def syllabify(phones: list[str]) -> list[list[str]]:
    """Split a phone list into syllables using the maximal-onset principle."""
    nuclei = [i for i, p in enumerate(phones) if is_vowel(p)]
    if not nuclei:
        return [phones]
    bounds = [0]
    for a, b in zip(nuclei, nuclei[1:]):
        cons = [base(p) for p in phones[a + 1 : b]]
        split = b  # default: all consonants to the left (zero onset)
        for k in range(len(cons) + 1):
            onset = tuple(cons[k:])
            if len(onset) <= 1 or onset in LEGAL_ONSETS:
                split = a + 1 + k
                break
        bounds.append(split)
    bounds.append(len(phones))
    return [phones[s:e] for s, e in zip(bounds, bounds[1:]) if e > s]


def to_ipa(phones: list[str], mark_stress: bool = True) -> str:
    parts = []
    syls = syllabify(phones)
    for syl in syls:
        s = "".join(phone_ipa(p) for p in syl)
        st = next((stress(p) for p in syl if is_vowel(p)), None)
        if mark_stress and len(syls) > 1 and st == 1:
            s = "ˈ" + s
        elif mark_stress and len(syls) > 1 and st == 2:
            s = "ˌ" + s
        parts.append(s)
    return "".join(parts)


# Short vowels are spelled plainly in a closed syllable ("sit", "bed", "cup") and with an h
# when the syllable is open ("sih", "eh").
SHORT_CLOSED = {"IH": "i", "EH": "e", "AE": "a", "AH": "u", "UH": "uu"}
SHORT_SPELLED = {"IH", "EH", "AE", "UH"}


def to_respelling(phones: list[str], caps: bool = True) -> str:
    """Plain-English 'say it like' spelling: about -> uh-BOWT, think -> think, water -> WAW-dur."""
    syls = [list(s) for s in syllabify(phones)]
    # Move one consonant back after a stressed short vowel so it reads naturally: VIL-uhj, not VIH-luhj.
    for a, b in zip(syls, syls[1:]):
        nucleus = next((p for p in a if is_vowel(p)), None)
        if (nucleus and is_vowel(a[-1]) and b and not is_vowel(b[0]) and stress(nucleus) in (1, 2)
                and base(nucleus) in SHORT_CLOSED):
            a.append(b.pop(0))

    out = []
    for syl in syls:
        vi = next((i for i, p in enumerate(syl) if is_vowel(p)), None)
        closed = vi is not None and vi < len(syl) - 1
        chunks = []
        for i, p in enumerate(syl):
            b = base(p)
            nxt = base(syl[i + 1]) if i + 1 < len(syl) else None
            if i == vi:
                st = stress(p)
                if b in SHORT_CLOSED and closed and (b in SHORT_SPELLED or st != 0):
                    chunks.append(SHORT_CLOSED[b])
                elif b == "AY" and vi > 0:
                    chunks.append("y")
                else:
                    chunks.append(RESPELL[b])
            elif b == "NG" and nxt in {"K", "G"}:
                chunks.append("n")
            else:
                chunks.append(RESPELL.get(b, b.lower()))
        if vi is not None and base(syl[vi]) == "AY" and closed:
            if base(syl[-1]) == "S":
                chunks[-1] = "ss"  # ice -> eyess, nice -> nyss (not "eyes", "nyse")
            elif vi > 0:
                chunks.append("e")  # ryte, tyme, lyke
        text = "".join(chunks)
        st = next((stress(p) for p in syl if is_vowel(p)), None)
        out.append(text.upper() if caps and st == 1 and len(syls) > 1 else text)
    return "-".join(out)


def pronunciation_notes(phones: list[str], surface: list[str]) -> list[str]:
    notes = []
    if "DX" in surface:
        notes.append(
            "American flap T: the T/D between vowels here is a quick tap of the tongue, "
            "almost like a soft D (water → WAW-dur, city → SID-ee)."
        )
    if any(base(p) == "ER" for p in phones) or any(base(p) == "R" for p in phones):
        notes.append(
            "American R: always pronounce the R, including after vowels and at the end of "
            "words. Curl or bunch the tongue back; the lips round slightly; the tongue tip never touches."
        )
    if any(base(p) in {"TH", "DH"} for p in phones):
        notes.append("TH: put the tongue tip lightly between the teeth and blow air; don't stop the air like T/D.")
    if base(phones[-1]) == "L" if phones else False:
        notes.append("Final L is a 'dark L': raise the back of the tongue while the tip touches the ridge.")
    return notes


@dataclass
class WordPron:
    word: str
    phones: list[str] | None
    surface: list[str] | None = None
    variants: list[list[str]] = field(default_factory=list)

    @property
    def known(self) -> bool:
        return self.phones is not None

    def describe(self) -> dict:
        if not self.phones:
            return {"word": self.word, "known": False}
        surface = self.surface or self.phones
        return {
            "word": self.word,
            "known": True,
            "arpabet": " ".join(self.phones),
            "ipa": "/" + to_ipa(surface) + "/",
            "ipa_dictionary": "/" + to_ipa(self.phones) + "/",
            "respelling": to_respelling(surface),
            "syllables": len(syllabify(self.phones)),
            "notes": pronunciation_notes(self.phones, surface),
            "variants": ["/" + to_ipa(v) + "/" for v in self.variants[1:]],
        }


def pronounce(word: str) -> WordPron:
    phones = lookup(word)
    return WordPron(
        word=word,
        phones=phones,
        surface=american_surface(phones) if phones else None,
        variants=all_pronunciations(word),
    )
