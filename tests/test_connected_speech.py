import re

from app.connected_speech import TOPICS, topic
from app.lexicon import VOWELS, lookup, tokenize

CONSONANTS = {"B", "CH", "D", "DH", "DX", "F", "G", "HH", "JH", "K", "L", "M", "N", "NG", "P", "R", "S", "SH",
              "T", "TH", "V", "W", "Y", "Z", "ZH"}


def test_topics_are_complete_and_unique():
    ids = [t["id"] for t in TOPICS]
    assert len(ids) == len(set(ids))
    for t in TOPICS:
        assert t["title"] and t["rule"] and t["how"] and t["level"] in (1, 2, 3) and t["sentences"]
        assert topic(t["id"]) is t


def test_items_have_valid_casual_pronunciations():
    for t in TOPICS:
        written = [i["written"] for i in t["items"]]
        assert len(written) == len(set(written)), t["id"]
        for i in t["items"]:
            assert i["spoken"] and i["ipa"], i
            for p in i["arpabet"].split():
                m = re.fullmatch(r"([A-Z]+)([012]?)", p)
                assert m, (i["written"], p)
                ph, st = m.groups()
                assert (ph in VOWELS and st) or (ph in CONSONANTS and not st), (i["written"], p)


def test_sentences_drill_their_items():
    for t in TOPICS:
        written = {i["written"] for i in t["items"]}
        for s in t["sentences"]:
            assert s["spoken"], s["text"]
            for name in s["items"]:
                assert name in written, (t["id"], name)
                # the item appears in the sentence (plural / possessive endings allowed)
                assert re.search(r"(?<![a-z])" + re.escape(name.lower()), s["text"].lower()), (t["id"], s["text"], name)
        drilled = {n for s in t["sentences"] for n in s["items"]}
        assert written <= drilled, (t["id"], written - drilled)


def test_every_sentence_word_can_be_scored():
    missing = {w for t in TOPICS for s in t["sentences"] for w in tokenize(s["text"]) if not lookup(w)}
    assert not missing, sorted(missing)


def test_every_sentence_groups_its_items_and_can_be_voiced():
    from app import casual

    for t in TOPICS:
        for k, s in enumerate(t["sentences"]):
            found, items = casual.sentence(t["id"], k)
            units = casual.group(tokenize(s["text"]), items)
            assert {i["written"] for _, i in units if i} == set(s["items"]), (t["id"], s["text"])
            prons = casual.prons(s["text"], items)
            assert all(p.known for p in prons), (t["id"], s["text"])
            assert casual.kokoro(s["text"], items), s["text"]


def test_casual_unit_scores_either_form():
    from app import casual
    from app.feedback import analyze
    from tests.test_core import heard

    _, items = casual.sentence("going-to", 0)  # "I'm going to call you after lunch."
    text = "I'm going to call you after lunch."
    gonna = heard("aɪ", "m", "ɡ", "ɑ", "n", "ə", "k", "ɔ", "l", "j", "u", "æ", "f", "t", "ɚ", "l", "ʌ", "n", "tʃ")
    res = analyze(text, gonna, detail_heard=gonna, prons=casual.prons(text, items))
    unit = next(w for w in res["words"] if w["word"] == "going to")
    assert unit["issues"] == [] and casual.form_used(unit["arpabet"].split(), items[0]) == "casual"
    full = heard("aɪ", "m", "ɡ", "oʊ", "ɪ", "ŋ", "t", "u", "k", "ɔ", "l", "j", "u", "æ", "f", "t", "ɚ", "l", "ʌ", "n", "tʃ")
    res = analyze(text, full, detail_heard=full, prons=casual.prons(text, items))
    unit = next(w for w in res["words"] if w["word"] == "going to")
    assert unit["issues"] == [] and casual.form_used(unit["arpabet"].split(), items[0]) == "careful"
