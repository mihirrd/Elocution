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


# --- two recognizers: an accent-faithful primary and a dictionary-leaning detail model ---

def test_known_accent_pattern_is_confirmed_even_if_detail_model_misses_it():
    # Primary hears "dis"; the detail model, biased toward the dictionary, hears "this".
    r = analyze("this", heard("d", "ɪ", "s"), detail_heard=heard("ð", "ɪ", "s"))
    issue = r["words"][0]["issues"][0]
    assert issue["confidence"] == "confirmed" and issue["expected"] == "ð"


def test_one_off_unknown_deviation_is_only_possible():
    r = analyze("bit", heard("b", "ɛ", "t"), detail_heard=heard("b", "ɪ", "t"))
    issue = r["words"][0]["issues"][0]
    assert issue["confidence"] == "possible"
    assert r["words"][0]["status"] == "good"


def test_repeated_deviation_is_confirmed():
    r = analyze("bit sit", heard("b", "ɛ", "t", "s", "ɛ", "t"),
                detail_heard=heard("b", "ɪ", "t", "s", "ɪ", "t"))
    assert all(w["issues"][0]["confidence"] == "confirmed" for w in r["words"])


def test_hard_t_comes_from_detail_model_only():
    # The primary model has no flap symbol, so its "t" is not evidence of a hard T...
    native = analyze("water", heard("w", "ɔ", "t", "ɚ"), detail_heard=heard("w", "ɔ", "ɾ", "ɚ"))
    assert native["words"][0]["issues"] == []
    # ...but when the detail model hears a real t, the American flap is missing.
    hard = analyze("water", heard("w", "ɔ", "t", "ɚ"), detail_heard=heard("w", "ɔ", "t", "ɚ"))
    assert "hard T" in hard["words"][0]["issues"][0]["tip"]


def test_non_rhotic_er_is_flagged():
    r = analyze("water", heard("w", "ɔ", "ɾ", "ə"))
    assert any("R" in i["tip"] for i in r["words"][0]["issues"])


# --- word segmentation (forced alignment) ---

def _fake_log_probs(frames, vocab):
    """frames: list of token strings (or "_" for blank), one per 20 ms frame."""
    import numpy as np
    lp = np.full((len(frames), len(vocab)), -10.0)
    for t, tok in enumerate(frames):
        lp[t, vocab["<pad>" if tok == "_" else tok]] = 0.0
    return lp


def test_forced_alignment_finds_word_boundaries():
    from app.segment import word_spans
    vocab = {"<pad>": 0, "h": 1, "aɪ": 2, "ð": 3, "ɛ": 4, "ɹ": 5}
    # "hi" then a pause then "there"
    frames = ["_", "h", "h", "aɪ", "aɪ", "aɪ", "_", "_", "_", "_", "_", "_", "ð", "ɛ", "ɛ", "ɹ", "_"]
    lp = _fake_log_probs(frames, vocab)
    spans = word_spans(lp, vocab, 0, 0.02, [["HH", "AY1"], ["DH", "EH1", "R"]], len(frames) * 0.02, max_pad=0.04)
    (s1, e1), (s2, e2) = spans
    assert abs(s1 - 0.0) < 0.03 and abs(e1 - 0.16) < 0.03   # phones at frames 1-5, +40 ms pad
    assert abs(s2 - 0.20) < 0.03 and abs(e2 - 0.34) < 0.03  # phones at frames 12-15, -40 ms pad
    assert e1 <= s2


def test_forced_alignment_splits_touching_words_at_the_gap():
    from app.segment import word_spans
    vocab = {"<pad>": 0, "s": 1, "iː": 2, "ɪ": 3, "t": 4}
    frames = ["s", "iː", "iː", "_", "s", "ɪ", "t"]  # "see" + "sit", no pause
    spans = word_spans(_fake_log_probs(frames, vocab), vocab, 0, 0.02, [["S", "IY1"], ["S", "IH1", "T"]], 0.14)
    assert spans[0][1] == spans[1][0] == 0.07  # boundary in the middle of the blank frame


# --- natural voice: text -> Kokoro phonemes ---

def test_kokoro_phonemes_match_kokoro_lexicon():
    from app.tts import text_to_kokoro
    # Reference values from Kokoro's own American lexicon (misaki us_gold).
    expected = {"water": "wˈɔɾəɹ", "little": "lˈɪɾᵊl", "about": "əbˈWt", "bird": "bˈɜɹd",
                "judge": "ʤˈʌʤ", "thirty": "θˈɜɹɾi", "corner": "kˈɔɹnəɹ"}
    for word, ps in expected.items():
        assert text_to_kokoro(word) == ps, word


def test_kokoro_sentence_keeps_punctuation_and_unstresses_function_words():
    from app.tts import text_to_kokoro
    assert text_to_kokoro("The car, 2 cats!") == "ðə kˈɑɹ, tˈu kˈæts!"


def test_flap_applies_before_final_y():
    from app.lexicon import american_surface, lookup
    assert "DX" in american_surface(lookup("thirty"))
