"""Connected-speech practice: score and voice a corpus sentence with its casual forms.

Each item of a sentence ("going to" -> G AA1 N AH0) becomes one scoring unit whose accepted
pronunciations are the casual form first and the careful dictionary forms after it, so either is
correct and the result says which one the speaker used. The voice says the casual form."""

from __future__ import annotations

import itertools
import re

from .connected_speech import topic
from .lexicon import WordPron, all_pronunciations, american_surface, lookup, tokenize
from .tts import FUNCTION_WORDS as TTS_FUNCTION_WORDS
from .tts import word_to_kokoro, text_to_kokoro

MAX_CAREFUL = 6  # careful variants kept for a multi-word item (combinations of each word's variants)


def sentence(topic_id: str, index: int) -> tuple[dict, list[dict]] | None:
    """(sentence, its items) from the corpus, or None."""
    t = topic(topic_id)
    if t is None or not 0 <= index < len(t["sentences"]):
        return None
    s = t["sentences"][index]
    by_name = {i["written"]: i for i in t["items"]}
    return s, [by_name[n] for n in s["items"] if n in by_name]


def _norm(w: str) -> str:
    return w.lower().replace("’", "'")


def group(words: list[str], items: list[dict]) -> list[tuple[str, dict | None]]:
    """Join each item's words into one unit: ["I'm", "going", "to", "call"] ->
    [("I'm", None), ("going to", item), ("call", None)]. Longer items are matched first."""
    patterns = sorted(((tuple(_norm(w) for w in tokenize(i["written"])), i) for i in items),
                      key=lambda p: -len(p[0]))
    out, k = [], 0
    while k < len(words):
        for pat, item in patterns:
            if pat and tuple(_norm(w) for w in words[k:k + len(pat)]) == pat:
                out.append((" ".join(words[k:k + len(pat)]), item))
                k += len(pat)
                break
        else:
            out.append((words[k], None))
            k += 1
    return out


def _careful(text: str) -> list[list[str]]:
    per_word = []
    for w in tokenize(text):
        vs = all_pronunciations(w) or ([lookup(w)] if lookup(w) else [])
        if not vs:
            return []
        per_word.append(vs)
    combos = itertools.islice(itertools.product(*per_word), MAX_CAREFUL)
    return [[p for part in combo for p in part] for combo in combos]


def prons(text: str, items: list[dict]) -> list[WordPron]:
    """The pronunciations to score `text` against, with each item as one unit."""
    from .lexicon import pronounce

    out = []
    for unit, item in group(tokenize(text), items):
        if item is None:
            out.append(pronounce(unit))
            continue
        casual = item["arpabet"].split()
        forms = casual_forms(item)
        variants = forms + [v for v in _careful(unit) if v not in forms]
        out.append(WordPron(word=unit, phones=casual, surface=american_surface(casual), variants=variants))
    return out


def casual_forms(item: dict) -> list[list[str]]:
    """The item's casual ARPAbet, plus, for a held T (ʔ in the IPA), the same without that T:
    the catch in the throat is usually heard as no T at all ("right now" -> ry'-NOW)."""
    phones = item["arpabet"].split()
    forms = [phones]
    if "ʔ" in item["ipa"]:
        held = [p for k, p in enumerate(phones)
                if not (p == "T" and (k + 1 == len(phones) or phones[k + 1] in {"N", "M", "B", "T"}))]
        if held != phones:
            forms.append(held)
    return forms


def form_used(phones: list[str], item: dict) -> str:
    return "casual" if phones in casual_forms(item) else "careful"


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*|\d+|[.,!?;:—…]")


def kokoro(text: str, items: list[dict]) -> str:
    """Kokoro phonemes for `text`, with every item in its casual form ("I'm gonna call ya")."""
    tokens = _TOKEN_RE.findall(text)
    words = [t for t in tokens if t[0].isalnum()]
    units = iter(group(words, items))
    parts: list[str] = []
    k = 0
    while k < len(tokens):
        tok = tokens[k]
        if not tok[0].isalnum():
            if parts:
                parts[-1] += tok
            k += 1
            continue
        unit, item = next(units)
        n = len(unit.split())
        if item is None:
            parts.append(text_to_kokoro(unit))
        else:
            phones = item["arpabet"].split()
            multi = sum(p[-1].isdigit() for p in phones) > 1
            parts.append(word_to_kokoro(phones, multi or unit.lower() not in TTS_FUNCTION_WORDS))
        # skip the unit's words (and punctuation inside it: "yes, I can")
        while n and k < len(tokens):
            n -= tokens[k][0].isalnum()
            k += 1
    return " ".join(p for p in parts if p)
