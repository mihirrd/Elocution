from app.align import align
from app.feedback import analyze, phrase_pronunciation
from app.lexicon import american_surface, lookup, to_ipa, to_respelling, tokenize
from app.phones import Heard, tokens_to_heard


def heard(*tokens):
    return tokens_to_heard([(t, i * 0.1, i * 0.1 + 0.1) for i, t in enumerate(tokens)])


def test_tokenize_spells_numbers():
    assert tokenize("I have 3 cats, don't I?") == ["I", "have", "three", "cats", "don't", "I"]


def test_ipa_and_respelling():
    assert to_ipa(lookup("about")) == "əˈbaʊt"
    assert to_respelling(lookup("about")) == "uh-BOWT"
    assert [to_respelling(lookup(w)) for w in ["think", "sit", "my", "right", "ice"]] == [
        "think", "sit", "my", "ryte", "eyess"]
    assert to_respelling(american_surface(lookup("village"))) == "VIL-uhj"
    assert to_ipa(lookup("think")) == "θɪŋk"


def test_flap_t():
    surface = american_surface(lookup("water"))
    assert "DX" in surface
    assert to_ipa(surface).endswith("ɾɚ")


def test_morphological_fallback():
    assert lookup("unfriendliness") is not None
    assert lookup("qzxv") is None


def test_perfect_match_scores_100():
    r = analyze("think", heard("θ", "ɪ", "ŋ", "k"))
    assert r["overall"] == 100
    assert r["words"][0]["issues"] == []


def test_th_to_s_is_flagged_with_tip():
    r = analyze("think", heard("s", "ɪ", "ŋ", "k"))
    w = r["words"][0]
    assert w["score"] < 100
    assert w["issues"][0]["expected"] == "θ" and w["issues"][0]["heard"] == "s"
    assert "S" in w["issues"][0]["tip"]


def test_flap_is_accepted_for_t():
    r = analyze("water", heard("w", "ɔ", "ɾ", "ɚ"))
    assert r["words"][0]["score"] == 100


def test_trilled_r_is_accent_feature():
    r = analyze("red", heard("r", "ɛ", "d"))
    issue = r["words"][0]["issues"][0]
    assert issue["severity"] == "accent"
    assert "rolled" in issue["tip"]


def test_dropped_r_and_final_consonant():
    r = analyze("car", heard("k", "ɑː"))
    assert any(i["type"] == "missing" and "R" in i["tip"] for i in r["words"][0]["issues"])


def test_epenthetic_vowel_attaches_to_next_s_cluster_word():
    r = analyze("my school", heard("m", "aɪ", "ɛ", "s", "k", "uː", "l"))
    school = r["words"][1]
    assert any(i["type"] == "extra" for i in school["issues"])
    assert r["words"][0]["score"] == 100


def test_align_handles_empty_heard():
    ops = align([(0, "HH"), (0, "AY1")], [])
    assert [o.kind for o in ops] == ["del", "del"]


def test_phrase_pronunciation():
    d = phrase_pronunciation("hello world")
    assert d["words"][0]["known"] and d["words"][1]["known"]
    assert "wɝld" in d["ipa"]


def test_r_colored_vowel_heard_as_vowel_plus_r():
    r = analyze("around", heard("ɚ", "ɹ", "aʊ", "n", "d"))
    assert r["words"][0]["score"] == 100


def test_r_not_stolen_across_word_boundary():
    r = analyze("the red", heard("ð", "ə", "ɹ", "ɛ", "d"))
    assert [w["score"] for w in r["words"]] == [100, 100]


def test_dictionary_variant_is_accepted():
    # Wednesday: first CMUdict entry ends in -dee, but -day is also standard.
    r = analyze("Wednesday", heard("w", "ɛ", "n", "z", "d", "eɪ"))
    assert r["words"][0]["score"] == 100


def test_dh_after_alveolar_is_minor():
    r = analyze("visited the", heard("v", "ɪ", "z", "ɪ", "ɾ", "ɪ", "d", "ə"))
    assert r["words"][1]["issues"][0]["severity"] == "accent"


def test_flap_across_word_boundary():
    r = analyze("sit in", heard("s", "ɪ", "d", "ɪ", "n"))
    assert [w["score"] for w in r["words"]] == [100, 100]


def test_consonant_merge_across_words():
    r = analyze("this seat", heard("ð", "ɪ", "s", "iː", "t"))
    assert r["words"][0]["status"] == "good"
