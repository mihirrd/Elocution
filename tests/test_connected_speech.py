import re

from app import casual, ipa
from app.connected_speech import GUIDE, PARTS, TOPICS, topic
from app.lexicon import VOWELS, lookup, tokenize

CONSONANTS = {"B", "CH", "D", "DH", "DX", "F", "G", "HH", "JH", "K", "L", "M", "N", "NG", "P", "R", "S", "SH",
              "T", "TH", "V", "W", "Y", "Z", "ZH"}


def test_topics_follow_the_reference():
    ids = [t["id"] for t in TOPICS]
    assert len(ids) == len(set(ids))
    assert sorted(t["number"] for t in TOPICS if t["number"]) == list(range(1, 23))  # all 22 processes
    parts = {p["id"] for p in PARTS}
    for t in TOPICS:
        assert t["part"] in parts and t["title"] and t["rule"] and t["sentences"], t["id"]
        assert topic(t["id"]) is t
    for _, topic_ids in GUIDE["priority"]:
        assert all(topic(i) for i in topic_ids)


def test_every_ipa_cell_converts_for_voice_and_scoring():
    for t in TOPICS:
        for i in t["items"]:
            assert ipa.forms(i["ipa"]), i
            assert ipa.to_kokoro(casual.voice_ipa(i).strip("[]")), i
            for phones in casual.casual_forms(i):
                for p in phones:
                    m = re.fullmatch(r"([A-Z]+)([012]?)", p)
                    ph, st = m.groups()
                    assert (ph in VOWELS and st) or (ph in CONSONANTS and not st), (i["written"], p)
            if i.get("say"):  # `say` only adds stress: same sounds as the reference
                strip = lambda s: re.sub(r"[ˈˌ.\[\] ̚]", "", s)
                assert strip(i["say"]) in [strip(f) for f in ipa.forms(i["ipa"])], i["written"]


def test_ipa_conversion_matches_the_reference_examples():
    assert ipa.to_arpabet("ˈwɑɾɚ") == ["W", "AA1", "DX", "ER0"]
    assert ipa.to_arpabet("ˈbʌʔn̩") == ["B", "AH1", "T", "N"]
    assert ipa.to_arpabet("ˈɡʌnə") == ["G", "AH1", "N", "AH0"]
    assert ipa.to_arpabet("bɪɡːeɪm") == ["B", "IH1", "G", "EY1", "M"]  # held g = one g
    assert ipa.to_kokoro("ˈwɑɾɚ") == "wˈɑɾəɹ"
    assert ipa.to_kokoro("ˈlɪɾl̩") == "lˈɪɾᵊl"
    assert ipa.to_kokoro("ˈdɪ.dʒə") == "dˈɪʤə"
    assert ipa.forms("[ˈpipəl] → [ˈpipl̩]") == ["ˈpipl̩"]
    assert ipa.forms("[ən], [n̩]") == ["ən", "n̩"]


def test_sentences_drill_their_items():
    for t in TOPICS:
        written = {i["written"] for i in t["items"]}
        for k, s in enumerate(t["sentences"]):
            assert s["spoken"], s["text"]
            for name in s["items"]:
                assert name in written, (t["id"], name)
            _, items = casual.sentence(t["id"], k)
            units = casual.group(tokenize(s["text"]), items)
            assert {i["written"] for _, i in units if i} == set(s["items"]), (t["id"], s["text"])
            assert casual.kokoro(s["text"], items, s.get("ipa")), s["text"]
        drilled = {n for s in t["sentences"] for n in s["items"]}
        assert written <= drilled, (t["id"], written - drilled)


def test_every_word_can_be_scored():
    missing = {w for t in TOPICS for s in t["sentences"] for w in tokenize(s["text"]) if not lookup(w)}
    missing |= {w for t in TOPICS for i in t["items"] for w in tokenize(i["written"]) if not lookup(w)}
    assert not missing, sorted(missing)


def test_connected_unit_scores_either_form():
    from app.feedback import analyze
    from tests.test_core import heard

    text = "I'm going to call you after lunch."
    _, items = casual.sentence("reduced-forms", 0)
    gonna = heard("aɪ", "m", "ɡ", "ʌ", "n", "ə", "k", "ɔ", "l", "j", "u", "æ", "f", "t", "ɚ", "l", "ʌ", "n", "tʃ")
    unit = next(w for w in analyze(text, gonna, detail_heard=gonna, prons=casual.prons(text, items))["words"]
                if w["word"] == "going to")
    assert unit["issues"] == [] and casual.form_used(unit["arpabet"].split(), items[0]) == "casual"
    full = heard("aɪ", "m", "ɡ", "oʊ", "ɪ", "ŋ", "t", "u", "k", "ɔ", "l", "j", "u", "æ", "f", "t", "ɚ", "l", "ʌ", "n", "tʃ")
    unit = next(w for w in analyze(text, full, detail_heard=full, prons=casual.prons(text, items))["words"]
                if w["word"] == "going to")
    assert unit["issues"] == [] and casual.form_used(unit["arpabet"].split(), items[0]) == "careful"
