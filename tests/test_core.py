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
    assert "American R" in issue["tip"]


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


def test_dh_merged_into_previous_word_is_accepted():
    # "visited the" -> "visitid'uh": normal in American connected speech (CMU ARCTIC).
    r = analyze("visited the", heard("v", "ɪ", "z", "ɪ", "ɾ", "ɪ", "d", "ə"))
    assert r["words"][1]["issues"] == []


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


def test_tapped_r_is_named_and_tipped():
    issue = analyze("red", heard("ɾ", "ɛ", "d"))["words"][0]["issues"][0]
    assert issue["severity"] == "accent" and issue["heard"] == "ɾ"
    assert "tapped" in issue["tip"]


def test_flap_t_is_not_called_a_tapped_r():
    assert analyze("pretty", heard("p", "ɹ", "ɪ", "ɾ", "i"))["words"][0]["issues"] == []


def test_rolled_r_wins_when_primary_heard_another_sound():
    # The primary recognizer has no rolled R: it writes "car" as "k ɑ d" or "really" with an L.
    for text, primary, detail in [
        ("car", heard("k", "ɑ", "d"), heard("k", "a", "r")),
        ("really", heard("l", "i", "l", "i"), heard("r", "i", "l", "i")),
        ("red", heard("ɛ", "d"), heard("r", "ɛ", "d")),
    ]:
        w = analyze(text, primary, detail_heard=detail)["words"][0]
        r_issue = next(i for i in w["issues"] if i.get("expected") == "ɹ")
        assert r_issue["heard"] == "r" and r_issue["confidence"] == "confirmed"
        assert "American R" in r_issue["tip"]


def test_tapped_r_wins_when_primary_heard_d():
    w = analyze("very", heard("v", "ɛ", "d", "i"), detail_heard=heard("v", "ɛ", "ɾ", "i"))["words"][0]
    assert [i["heard"] for i in w["issues"]] == ["ɾ"] and "tapped" in w["issues"][0]["tip"]


def test_american_r_is_not_flagged_when_detail_agrees():
    assert analyze("car", heard("k", "ɑ", "ɹ"), detail_heard=heard("k", "ɑːɹ"))["words"][0]["issues"] == []


def _ratios(**by_index):
    return lambda phones, words: {"r_color": {int(k[1:]): v for k, v in by_index.items()}}


def _vots(**by_index):
    return lambda phones, words: {"vot": {int(k[1:]): v for k, v in by_index.items()}}


def test_r_without_american_color_is_flagged_even_if_recognizers_heard_r():
    # "red" = R EH D: phone 0 is the R. Both recognizers heard an American R; F3 says no.
    w = analyze("red", heard("ɹ", "ɛ", "d"), detail_heard=heard("ɹ", "ɛ", "d"),
                measure=_ratios(i0=0.95))["words"][0]
    assert w["issues"][0]["severity"] == "error" and "American R" in w["issues"][0]["tip"]
    assert w["score"] <= 60


def test_clear_american_r_overrules_a_false_rolled_r():
    w = analyze("red", heard("ɹ", "ɛ", "d"), detail_heard=heard("r", "ɛ", "d"),
                measure=_ratios(i0=0.70))["words"][0]
    assert w["issues"] == [] and w["score"] == 100


def test_er_without_r_color_is_flagged():
    # "her" = HH ER
    w = analyze("her", heard("h", "ɚ"), detail_heard=heard("h", "ɚ"), measure=_ratios(i1=0.97))["words"][0]
    assert w["issues"][0]["expected"] == "ɝ" and "American R" in w["issues"][0]["tip"]


def test_unclear_measurement_leaves_verdict_alone():
    w = analyze("red", heard("ɹ", "ɛ", "d"), detail_heard=heard("ɹ", "ɛ", "d"),
                measure=_ratios(i0=0.82))["words"][0]
    assert w["issues"] == []


def test_unaspirated_t_is_flagged():
    # "time" = T AY M: phone 0 is the T; 20 ms of voice onset time = no puff of air.
    w = analyze("time", heard("t", "aɪ", "m"), detail_heard=heard("t", "aɪ", "m"), measure=_vots(i0=20))["words"][0]
    assert w["issues"][0]["severity"] == "accent" and "puff of air" in w["issues"][0]["tip"]


def test_aspirated_t_passes():
    w = analyze("time", heard("t", "aɪ", "m"), detail_heard=heard("t", "aɪ", "m"), measure=_vots(i0=70))["words"][0]
    assert w["issues"] == []


def test_aspiration_positions():
    from app.acoustics import aspiration_positions
    from app.lexicon import pronounce

    def where(*words):
        wp = [(wi, p) for wi, w in enumerate(words) for p in pronounce(w).phones]
        return [(words[wp[i][0]], i - next(k for k, (w, _) in enumerate(wp) if w == wp[i][0]))
                for i in aspiration_positions(wp)]

    assert where("time") == [("time", 0)]
    assert where("attack") == [("attack", 1)]      # T before the stressed vowel
    assert where("stop") == []                      # after S: unaspirated in American English too
    assert where("water") == []                     # before an unstressed vowel: a flap
    assert where("robert", "ordered") == []         # word-final T, even before a vowel


def test_unaspirated_p_and_k_are_flagged_with_their_own_thresholds():
    # "pin" = P IH N, "cat" = K AE T: phone 0 is the stop.
    p = analyze("pin", heard("p", "ɪ", "n"), detail_heard=heard("p", "ɪ", "n"), measure=_vots(i0=20))["words"][0]
    assert p["issues"][0]["heard"] == "p˭" and "P had no puff" in p["issues"][0]["tip"]
    k = analyze("cat", heard("k", "æ", "t"), detail_heard=heard("k", "æ", "t"), measure=_vots(i0=38))["words"][0]
    assert k["issues"][0]["heard"] == "k˭"
    # 38 ms is unaspirated for K but would be fine for P.
    p2 = analyze("pin", heard("p", "ɪ", "n"), detail_heard=heard("p", "ɪ", "n"), measure=_vots(i0=38))["words"][0]
    assert p2["issues"] == []


def _l_f2(**by_index):
    return lambda phones, words: {"l_f2": {int(k[1:]): v for k, v in by_index.items()}}


def test_clear_l_after_a_vowel_is_flagged():
    # "feel" = F IY L: phone 2 is the L.
    w = analyze("feel", heard("f", "i", "l"), detail_heard=heard("f", "i", "l"), measure=_l_f2(i2=0.95))["words"][0]
    assert w["issues"][0]["heard"] == "l" and "dark" in w["issues"][0]["tip"]


def test_dark_l_heard_as_w_or_dropped_is_accepted():
    # "all" = AO L: an American dark L often sounds like "w" or disappears for the recognizers.
    for primary in (heard("ɔ", "w"), heard("ɔ")):
        w = analyze("all", primary, detail_heard=heard("ɔ", "l"), measure=_l_f2(i1=0.6))["words"][0]
        assert w["issues"] == [], w["issues"]


def _gop(**by_index):
    return lambda phones, words: {"vw_gop": {int(k[1:]): v for k, v in by_index.items()}}


def test_w_that_sounds_like_v_is_flagged():
    # "west" = W EH S T: phone 0 is the W.
    w = analyze("west", heard("w", "ɛ", "s", "t"), detail_heard=heard("w", "ɛ", "s", "t"), measure=_gop(i0=-0.5))["words"][0]
    assert w["issues"][0]["heard"] == "ʋ" and "round the lips" in w["issues"][0]["tip"]
    ok = analyze("west", heard("w", "ɛ", "s", "t"), detail_heard=heard("w", "ɛ", "s", "t"), measure=_gop(i0=-6.4))["words"][0]
    assert ok["issues"] == []


def test_softened_the_inside_a_sentence_is_not_flagged():
    # Americans often merge "the" into the previous word: "in the" -> "in'uh".
    r = analyze("sit in the car", heard("s", "ɪ", "t", "ɪ", "n", "ə", "k", "ɑ", "ɹ"))
    the = r["words"][2]
    assert the["issues"] == [], the["issues"]


def test_final_z_devoiced_only_at_the_end_of_the_sentence():
    end = analyze("I like dogs", heard("aɪ", "l", "aɪ", "k", "d", "ɔ", "ɡ", "s"))
    assert end["words"][2]["issues"] == []
    mid = analyze("dogs are here", heard("d", "ɔ", "ɡ", "s", "ɑ", "ɹ", "h", "ɪ", "ɹ"))
    assert mid["words"][0]["issues"][0]["heard"] == "s"


def test_password_protects_every_route(monkeypatch):
    import base64

    from fastapi.testclient import TestClient

    from app import main

    monkeypatch.setattr(main, "PASSWORD", "s3cret")
    client = TestClient(main.app)
    assert client.get("/api/sentences").status_code == 401
    assert "Basic" in client.get("/").headers["www-authenticate"]
    wrong = base64.b64encode(b"friend:nope").decode()
    assert client.get("/api/sentences", headers={"Authorization": f"Basic {wrong}"}).status_code == 401
    right = base64.b64encode(b"anyone:s3cret").decode()
    assert client.get("/api/sentences", headers={"Authorization": f"Basic {right}"}).status_code == 200
    monkeypatch.setattr(main, "PASSWORD", "")
    assert client.get("/api/sentences").status_code == 200  # no password set: open, as before


def test_impact_ranks_word_changing_mistakes_first():
    from app.feedback import HIGH, LOW, MEDIUM, _impact

    assert _impact("V", "W", "very") == HIGH          # vest / west
    assert _impact("IH1", "IY", "live") == HIGH       # live / leave
    assert _impact("IH0", "IY", "rabbit") == MEDIUM   # unstressed: not a word contrast
    assert _impact("TH", "T", "think") == MEDIUM      # noticeable, still understood
    assert _impact("T", "~t˭", "time") == MEDIUM
    assert _impact("L", "~l", "feel") == LOW          # finishing touch
    assert _impact("AE1", "AH", "at") == LOW          # "at" → ət is normal reduction
    assert _impact("K", "-", "walked") == HIGH        # dropped consonant changes the word
    assert _impact("T", "-", "last", final=True) == MEDIUM
    assert _impact("AH0", "-", "about") == LOW


def _issues(text, *tokens, measure=None):
    res = analyze(text, heard(*tokens), detail_heard=heard(*tokens), measure=measure)
    return {w["word"]: [x["tip"][:40] for x in w["issues"]] for w in res["words"]}


def test_connected_speech_is_not_a_mistake():
    assert _issues("written", "ɹ", "ɪ", "ʔ", "n") == {"written": []}           # glottal T, no vowel
    assert _issues("written", "ɹ", "ɪ", "t", "ə", "n") == {"written": []}      # careful T is fine too
    assert _issues("tell him", "t", "ɛ", "l", "ɪ", "m")["him"] == []           # tell'im
    assert _issues("right there", "ɹ", "aɪ", "ð", "ɛ", "ɹ")["right"] == []     # righ' there
    assert _issues("don't you", "d", "oʊ", "n", "tʃ", "u") == {"don't": [], "you": []}
    assert _issues("I can see", "aɪ", "k", "ə", "n", "s", "i",                # kən, barely aspirated
                   measure=_vots(i1=10))["can"] == []


def test_connected_speech_rules_stay_narrow():
    assert _issues("he can", "i", "k", "ɛ", "n")["he"]                        # sentence start: H needed
    assert _issues("right", "ɹ", "aɪ")["right"]                                # nothing follows: T needed
    assert _issues("I can't see", "aɪ", "k", "ə", "n", "t", "s", "i")["can't"]  # can't keeps its vowel


def test_r_after_t_needs_stronger_evidence():
    # "try" = T R AY: after T the R starts voiceless, so 0.855 isn't enough to call it non-American.
    assert analyze("try", heard("t", "ɹ", "aɪ"), detail_heard=heard("t", "ɹ", "aɪ"),
                   measure=_ratios(i1=0.855))["words"][0]["issues"] == []
    assert analyze("try", heard("t", "ɹ", "aɪ"), detail_heard=heard("t", "ɹ", "aɪ"),
                   measure=_ratios(i1=0.95))["words"][0]["issues"]
