"""Connected-speech practice: score and voice a corpus sentence with its connected forms.

Each item of a sentence ("going to" -> [ˈɡʌnə]) becomes one scoring unit whose accepted
pronunciations are the reference's connected forms first and the careful dictionary forms after
them, so either is correct and the result says which one the speaker used. Scoring and the voice
both read the reference's IPA (see ipa.py), so they say and accept exactly what is shown."""

from __future__ import annotations

import itertools
import re

from . import ipa
from .connected_speech import topic
from .lexicon import WordPron, all_pronunciations, american_surface, lookup, tokenize
from .tts import text_to_kokoro

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


def voice_ipa(item: dict) -> str:
    """The IPA the voice says: the item's `say` (the reference's IPA with stress added) or the
    reference's first connected form."""
    return item.get("say") or ipa.forms(item["ipa"])[0]


def casual_forms(item: dict) -> list[list[str]]:
    """Every connected form the reference gives, as ARPAbet. Recognizers hear some of these
    sounds as something else, so those spellings count too: a glottal stop [ʔ] as no T at all,
    and a syllabic [n̩] / [l̩] as "ən" / "əl" (a full vowel there is still a mistake)."""
    out: list[list[str]] = []
    for f in [voice_ipa(item).strip("[]")] + ipa.forms(item["ipa"]):
        variants = [f]
        if "n̩" in f or "l̩" in f:
            variants.append(f.replace("n̩", "ən").replace("l̩", "əl"))
        if "ʔ" in f:
            variants += [v.replace("ʔ", "") for v in variants]
        for g in variants:
            phones = ipa.to_arpabet(g)
            if phones and phones not in out:
                out.append(phones)
    return out


def prons(text: str, items: list[dict]) -> list[WordPron]:
    """The pronunciations to score `text` against, with each item as one unit."""
    from .lexicon import pronounce

    out = []
    for unit, item in group(tokenize(text), items):
        if item is None:
            out.append(pronounce(unit))
            continue
        forms = casual_forms(item)
        variants = forms + [v for v in _careful(unit) if v not in forms]
        out.append(WordPron(word=unit, phones=forms[0], surface=american_surface(forms[0]), variants=variants))
    return out


def form_used(phones: list[str], item: dict) -> str:
    return "casual" if phones in casual_forms(item) else "careful"


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*|\d+|[.,!?;:—…]")


def kokoro(text: str, items: list[dict], sentence_ipa: str | None = None) -> str:
    """Kokoro phonemes for `text` in connected speech. With the reference's IPA for the whole
    sentence (the worked examples), that is used as is; otherwise every item is said in its
    connected form and the other words as usual."""
    final = re.search(r"[.!?…]+$", text.strip())
    if sentence_ipa:
        return " ".join(ipa.to_kokoro(f) for f in ipa.forms(sentence_ipa)) + (final.group() if final else "")
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
        parts.append(text_to_kokoro(unit) if item is None else ipa.to_kokoro(voice_ipa(item).strip("[]")))
        # skip the unit's words (and punctuation inside it: "yes, I can")
        while n and k < len(tokens):
            n -= tokens[k][0].isalnum()
            k += 1
    return " ".join(p for p in parts if p)
