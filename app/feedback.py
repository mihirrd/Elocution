"""Turn alignment results into coaching: per-word verdicts and targeted tips."""

from __future__ import annotations

from collections import Counter

from .align import Op, align, best_variant, combine
from .lexicon import WordPron, american_surface, base, phone_ipa, pronounce, sound_name, stress, to_ipa
from .phones import NON_AMERICAN_R, Heard, heard_respelling, unit_name

# Tips for specific (expected, heard) confusions. Heard keys are ARPAbet, or "~ipa" for
# non-English sounds.
PAIR_TIPS: dict[tuple[str, str], str] = {
    ("TH", "T"): "You stopped the air like a T. For TH, rest the tongue tip between your teeth and let air hiss out continuously.",
    ("TH", "S"): "That came out as S. Move the tongue forward so the tip touches the back of the upper teeth (or sits between them), then blow.",
    ("TH", "F"): "That sounded like F. Keep your lips relaxed and use the tongue, not the lower lip, against the teeth.",
    ("DH", "D"): "You stopped the air like a D. For the voiced TH (this, the, that), put the tongue between the teeth and hum while air flows.",
    ("DH", "Z"): "That came out as Z. Bring the tongue tip forward to the teeth for the voiced TH.",
    ("V", "W"): "That sounded like W. For V, touch your upper teeth to your lower lip and buzz. Don't round the lips.",
    ("V", "B"): "That sounded like B. Don't close the lips: put your upper teeth on your lower lip and let the air buzz through.",
    ("W", "V"): "That sounded like V. For W, don't touch the teeth: round the lips into a small circle ('oo') and open them quickly.",
    ("R", "L"): "That sounded like L. For R, the tongue tip must NOT touch the roof of the mouth; pull it back and round the lips a little.",
    ("L", "R"): "That sounded like R. For L, press the tongue tip firmly on the ridge behind the upper teeth.",
    ("R", "~r"): "This wasn't an American R: it didn't have the R sound Americans make (your tongue tip probably touched the roof of the mouth, or stayed flat). Pull the tongue tip back so it touches nothing (or bunch the whole tongue up and back), round the lips slightly, and hold it, like the start of 'grrr'.",
    ("R", "~ɾ"): "Your R was tapped: the tongue tip flicked the ridge behind your teeth once, like a quick D. The American R has no tongue contact at all: curl the tip back (or bunch the tongue), round the lips slightly, and hold it.",
    ("R", "~ʁ"): "Your R came from the throat. Make the American R with the front of the tongue curled back, not with the back of the throat.",
    ("R", "~ɽ"): "Your R was a flapped retroflex sound. Keep the tongue from touching anything and hold the R as a smooth glide.",
    ("T", "~ʈ"): "Your T was retroflex (tongue curled back). American T is made with the tongue tip on the ridge just behind the upper teeth.",
    ("D", "~ɖ"): "Your D was retroflex. Touch the tongue tip to the ridge behind the upper teeth instead of curling it back.",
    ("L", "~l"): "Your L was a clear L, made with the tongue tip only. After a vowel (feel, milk, all, people), Americans use a 'dark' L: keep the tip on the ridge behind the teeth but also raise the back of the tongue toward the soft palate, so it sounds deeper and hollow, almost 'uhl'.",
    ("P", "~p˭"): "Your P had no puff of air. At the start of a word or a stressed syllable (pin, paper, appear), Americans release P with a small burst of breath, almost 'p-h'. Hold a hand in front of your mouth: you should feel the air.",
    ("K", "~k˭"): "Your K had no puff of air. At the start of a word or a stressed syllable (cat, keep, account), Americans release K with a small burst of breath, almost 'k-h'. Hold a hand in front of your mouth: you should feel the air.",
    ("T", "~t˭"): "Your T had no puff of air. At the start of a word or a stressed syllable (time, today, attack), Americans release T with a small burst of breath, almost 't-h'. Hold a hand in front of your mouth: you should feel the air.",
    ("T", "~t̪"): "Your T was dental. Place the tongue tip a bit further back, on the ridge behind the teeth, and release with a puff of air.",
    ("V", "~ʋ"): "That was between V and W. For V, press the upper teeth firmly on the lower lip so the air buzzes audibly.",
    ("W", "~ʋ"): "That was between W and V. For W, round the lips and keep the teeth away from the lip.",
    ("IH", "IY"): "You used a long EE (as in 'seat'). This is a short, relaxed IH (as in 'sit'): lower the tongue slightly and don't smile.",
    ("IY", "IH"): "You used a short IH (as in 'sit'). This is a long EE (as in 'seat'): spread the lips and hold the tongue high and tense.",
    ("AE", "EH"): "That sounded like 'eh' (bed). For the American A in 'cat', drop the jaw lower and spread the lips: almost 'eh-a'.",
    ("AE", "AA"): "That sounded like 'ah'. Keep the tongue more forward and spread the lips for the flat American A in 'cat'.",
    ("AE", "AH"): "That sounded like 'uh'. Open the jaw and push the tongue forward for A as in 'cat'.",
    ("EH", "AE"): "You opened your mouth too wide ('cat'). For EH (bed), keep the jaw only half open.",
    ("EH", "EY"): "You added a glide ('ay'). EH as in 'bed' is short with no glide.",
    ("AH", "AA"): "That sounded like 'ah' (father). For the short U in 'cup', keep the mouth relaxed and only slightly open: 'uh'.",
    ("AH", "AO"): "That sounded like 'aw'. For 'uh' (cup), don't round the lips; relax everything.",
    ("AA", "AH"): "That sounded like 'uh'. Open the jaw wide for 'ah' as in 'father'.",
    ("AA", "~ɒ"): "That's the British rounded O. Americans say this vowel with unrounded, open lips: 'ah' (hot → HAHT).",
    ("UH", "UW"): "You used a long OO (food). This is the short, relaxed vowel in 'book' and 'good': less lip rounding, shorter.",
    ("UW", "UH"): "You used the short vowel from 'book'. Round the lips more and hold it longer: 'oo' as in 'food'.",
    ("OW", "~o"): "Your O was a pure vowel. American O glides: start at 'oh' and end rounding toward 'oo' (go sounds like 'goh-oo').",
    ("OW", "~oː"): "Your O was a pure vowel. American O glides: start at 'oh' and finish with lips rounding toward 'oo'.",
    ("OW", "AO"): "That sounded like 'aw'. American O is a glide: 'oh-oo', with lips closing as you go.",
    ("OW", "~əʊ"): "That's the British 'əʊ' O. The American version starts rounder: 'oh-oo'.",
    ("EY", "~e"): "Your A was a pure vowel. American 'ay' glides from 'eh' toward 'ee' (day sounds like 'deh-ee').",
    ("EY", "~eː"): "Your A was a pure vowel. American 'ay' glides from 'eh' toward 'ee'.",
    ("EY", "EH"): "You dropped the glide. Say 'ay' fully: 'eh-ee'.",
    ("ER", "AH"): "This 'er' was missing the American R sound. The American 'er' (bird, her, teacher) is fully r-colored: hold the tongue in the R position through the vowel.",
    ("ER", "EH"): "Make this an r-colored 'er' sound, not 'eh'. Pull the tongue back into the R shape for the whole vowel.",
    ("ER", "~a"): "Don't open it into 'a'. The ending -er is an r-colored vowel: 'ur'.",
    ("Z", "S"): "That came out as S. Keep your voice buzzing for Z (put a hand on your throat; you should feel it vibrate).",
    ("S", "SH"): "That sounded like SH. Pull the lips back (not rounded) and keep the tongue tip near the upper teeth for S.",
    ("SH", "S"): "That sounded like S. Round the lips and pull the tongue slightly back for SH.",
    ("CH", "SH"): "That sounded like SH. CH starts with a T: block the air with the tongue, then release into SH ('t-sh').",
    ("JH", "Y"): "That sounded like Y. J (judge) starts with D: touch the tongue to the ridge, then release into a buzzing 'zh'.",
    ("JH", "ZH"): "Start the J with a D closure: 'd-zh'.",
    ("Y", "JH"): "That sounded like J. Y (yes) has no tongue contact: glide from an 'ee' position.",
    ("NG", "N"): "That sounded like N. For NG, lift the BACK of the tongue to the soft palate; the tip stays down.",
    ("N", "NG"): "That sounded like NG. Put the tongue tip on the ridge behind the teeth for N.",
    ("P", "B"): "That sounded like B. Release P with a puff of air (hold a sheet of paper in front of your mouth; it should move).",
    ("T", "T"): "You used a hard T. Between vowels Americans tap the tongue quickly, like a soft D: water → WAW-dur, better → BED-ur, little → LID-uhl.",
    ("T", "D"): "That sounded like D. American T is voiceless: release it with a small puff of air. (Only between vowels does it soften into the quick flap, as in 'water'.)",
    ("K", "G"): "That sounded like G. Release K with a puff of air.",
    ("F", "P"): "That sounded like P. Don't close the lips: put your upper teeth on your lower lip and blow.",
    ("ER", "UH"): "That sounded like the vowel in 'book'. The American 'ur' (bird, early, turn) is one r-colored sound: pull the tongue back into the R position for the whole vowel.",
    ("V", "F"): "That sounded like F. V is the same mouth position as F, but with your voice buzzing (of → uv, have → hav).",
    ("D", "T"): "That sounded like T. Keep your voice on through the end of the word for D (bed, not bet).",
    ("G", "K"): "That sounded like K. Keep your voice on for G (bag, not back).",
    ("B", "P"): "That sounded like P. Keep your voice on for B, with no puff of air.",
    ("HH", "~x"): "Your H was scratchy (from the throat). The English H is just a soft breath, like fogging a mirror.",
}

PHONE_TIPS: dict[str, str] = {
    "TH": "TH (think): tongue tip between the teeth, blow air without voice.",
    "DH": "voiced TH (this): tongue between the teeth and hum.",
    "R": "American R: tongue tip pulled back, touching nothing; lips slightly rounded.",
    "L": "L: tongue tip pressed on the ridge behind the upper teeth.",
    "V": "V: upper teeth on lower lip, voice buzzing.",
    "W": "W: round lips ('oo') and open quickly.",
    "AE": "A as in 'cat': jaw dropped, lips spread, tongue forward.",
    "IH": "short I as in 'sit': short and relaxed.",
    "IY": "long E as in 'see': lips spread, tongue high.",
    "ER": "'er' as in 'bird': r-colored vowel, tongue in R position throughout.",
    "AH": "'uh' as in 'cup': relaxed mouth, short.",
    "HH": "H: a soft breath, no throat friction.",
}


def _pair_tip(exp: str, heard: str) -> str | None:
    return PAIR_TIPS.get((base(exp), heard))


def _deletion_tip(exp: str, is_final: bool) -> str:
    b = base(exp)
    if b == "R":
        return "You dropped the R. American English is rhotic: always pronounce R after vowels (car, more, here)."
    if b == "HH":
        return "You dropped the H. Breathe it out audibly at the start of the word."
    if is_final:
        return f"You dropped the final {_say(exp)} sound. Finish the word clearly; final consonants change meaning (bed vs. bet vs. be)."
    return f"The {_say(exp)} sound was missing."


def _insertion_tip(heard: Heard, word_ops: list[Op], at_end: bool) -> str | None:
    if heard.unit in {"AH", "IH", "UH", "~ɨ"} and at_end:
        return "You added a vowel at the end of the word ('big-uh'). Stop cleanly on the final consonant."
    if heard.unit in {"AH", "IH", "IY", "EH"} and word_ops and word_ops[0].kind == "ins":
        return "You added a vowel before the word ('eschool'). Start directly with the consonant cluster."
    if heard.unit in {"AH", "IH", "UH"}:
        return "You added an extra vowel between consonants. Blend the consonants together without a vowel."
    if heard.unit == "Q":
        return None
    return f"An extra {_say_unit(heard.unit)} sound was added."


def _fmt(name: str, example: str | None) -> str:
    return f"“{name}” (as in {example})" if example else f"“{name}”"


def _say(phone: str) -> str:
    """'"th" (as in think)' for an expected phone."""
    return _fmt(*sound_name(phone))


def _say_unit(unit: str, reduced: bool = False) -> str:
    return _fmt(*unit_name(unit, reduced))


def _sound_view(name_example: tuple[str, str | None], prefix: str) -> dict:
    name, example = name_example
    return {f"{prefix}_say": name, f"{prefix}_example": example}


# Dropping these is a well-known accent feature (non-rhotic R, TH avoidance, H dropping).
KNOWN_DROPS = {"R", "ER", "DH", "TH", "HH"}


def _penalty(o: Op) -> float:
    """Points a single sound costs its word (out of 100). Fixed per mistake rather than per
    phone, so one clearly non-American sound in a short word still shows."""
    if o.severity == "ok":
        return 0.0
    if o.confidence == "possible":
        return 8.0
    return 40.0 if o.severity == "error" else 22.0


def _pattern(o: Op) -> tuple:
    if o.kind == "ins":
        return ("ins", o.heard.unit)
    if o.kind == "del":
        return ("del", base(o.expected))
    return ("sub", base(o.expected), o.heard.unit)


def _promote_likely_real(ops: list[Op]) -> None:
    """A mistake only one recognizer heard is promoted from "possible" to confirmed when it is a
    textbook accent pattern, or when the same mistake repeats in the recording: recognizer noise
    is random, real accent features are consistent."""
    possible = [o for o in ops if o.confidence == "possible" and o.severity != "ok"]
    repeats = Counter(_pattern(o) for o in possible)
    for o in possible:
        pat = _pattern(o)
        known = (pat[0] == "sub" and (pat[1], pat[2]) in PAIR_TIPS) or (pat[0] == "del" and pat[1] in KNOWN_DROPS)
        if known or repeats[pat] >= 2:
            o.confidence = "confirmed"


NO_R_COLOR_COST = 0.65  # the clearest marker of a non-American accent: count it as a real error
UNASPIRATED_COST = 0.45  # an accent feature: understood, but clearly not American
CLEAR_L_COST = 0.45
VW_COST = 0.6  # V/W confusion changes words (vest / west), so it counts as an error


def _apply_acoustics(ops: list[Op], chosen: list[tuple[int, str]], m: dict[str, dict[int, float]]) -> None:
    """Let the acoustic measurements (see acoustics.py) overrule the recognizers on the
    features they can't hear: R color, aspiration of P / T / K, the dark L, and V / W."""
    from .acoustics import CLEAR_L, CLEAR_R, DARK_L, GOP_FLAG, NO_R_COLOR, UNASPIRATED

    pos = {}
    for i, (wi, _) in enumerate(chosen):
        pos[i] = (wi, sum(1 for w, _ in chosen[:i] if w == wi))
    ratio_at = {pos[i]: r for i, r in m.get("r_color", {}).items()}
    vot_at = {pos[i]: v for i, v in m.get("vot", {}).items()}
    l_at = {pos[i]: v for i, v in m.get("l_f2", {}).items()}
    gop_at = {pos[i]: v for i, v in m.get("vw_gop", {}).items()}
    for o in ops:
        if o.expected is None:
            continue
        l_f2 = l_at.get((o.word, o.pos))
        if l_f2 is not None and base(o.expected) == "L":
            if l_f2 <= DARK_L and o.severity != "ok":
                # A dark L is often heard as "w" or as nothing ("all", "still"): it's the American L.
                h = o.heard
                start, end = (h.start, h.end) if h else (0.0, 0.0)
                o.kind, o.cost, o.heard = "match", 0.0, Heard("L", "ɫ", start, end)
            elif l_f2 >= CLEAR_L and o.severity == "ok" and o.heard is not None:
                o.kind, o.cost, o.confidence = "sub", CLEAR_L_COST, "confirmed"
                o.heard = Heard("~l", "l", o.heard.start, o.heard.end)
            continue
        if o.kind == "del" or o.heard is None:
            continue
        b = base(o.expected)
        h = o.heard
        ratio = ratio_at.get((o.word, o.pos))
        if ratio is not None and ratio <= CLEAR_R:
            if b == "R" and h.unit in NON_AMERICAN_R:
                o.kind, o.cost, o.heard = "match", 0.0, Heard("R", "ɹ", h.start, h.end)
        elif ratio is not None and ratio >= NO_R_COLOR:
            if b == "R" and (o.severity == "ok" or h.unit in NON_AMERICAN_R):
                ipa = h.ipa if h.unit in NON_AMERICAN_R else "r"
                o.kind, o.cost, o.confidence = "sub", NO_R_COLOR_COST, "confirmed"
                o.heard = Heard("~r", ipa, h.start, h.end)
            elif b == "ER" and o.severity == "ok":
                o.kind, o.cost, o.confidence = "sub", NO_R_COLOR_COST, "confirmed"
                o.heard = Heard("AH", "ə", h.start, h.end)
        gop = gop_at.get((o.word, o.pos))
        if b in GOP_FLAG and gop is not None and gop >= GOP_FLAG[b] and o.severity == "ok":
            # The Indian ʋ, between V and W: the recognizer's label said V/W, its probabilities didn't.
            o.kind, o.cost, o.confidence = "sub", VW_COST, "confirmed"
            o.heard = Heard("~ʋ", "ʋ", h.start, h.end)
        vot = vot_at.get((o.word, o.pos))
        if b in UNASPIRATED and vot is not None and vot <= UNASPIRATED[b] and o.severity == "ok":
            sym = b.lower() + "˭"
            o.kind, o.cost, o.confidence = "sub", UNASPIRATED_COST, "confirmed"
            o.heard = Heard("~" + sym, sym, h.start, h.end)


def _heard_ipa(op: Op) -> str:
    if op.heard is None:
        return ""
    if op.heard.foreign:
        return op.heard.ipa
    return phone_ipa(op.heard.unit + ("0" if op.heard.unit in {"AH", "ER"} and op.expected and stress(op.expected) == 0 else ""))


def analyze(text: str, heard: list[Heard], words: list[str] | None = None,
            detail_heard: list[Heard] | None = None, measure=None) -> dict:
    """Score `heard` against the expected pronunciation of `text`.

    `detail_heard`, when given, is a second recognizer's view of the same audio, used to
    confirm mistakes and to catch the flap T and non-English sounds (see align.combine).
    `measure`, when given, takes the utterance's expected (word index, phone) list and the words,
    and returns acoustic measurements per phone index (see acoustics.Acoustics.measure); they
    decide R color and T aspiration, which the recognizers can't hear."""
    from .lexicon import tokenize

    words = words if words is not None else tokenize(text)
    prons: list[WordPron] = [pronounce(w) for w in words]

    expected: list[tuple[int, str]] = []
    for wi, p in enumerate(prons):
        if p.phones:
            expected.extend((wi, ph) for ph in p.phones)

    two_models = detail_heard is not None
    ops = align(expected, heard, hard_t=not two_models) if expected else []

    # A word may have several accepted pronunciations; score against the closest one.
    for wi, p in enumerate(prons):
        if len(p.variants) < 2:
            continue
        before = next((ph for w, ph in reversed(expected) if w < wi), None)
        last = wi == max(w for w, _ in expected)
        found = best_variant(wi, p.variants, ops, before, hard_t=not two_models, last_word=last)
        if found:
            variant, local = found
            p.variants = [variant] + [v for v in p.variants if v != variant]
            p.phones, p.surface = variant, american_surface(variant)
            first = next(k for k, o in enumerate(ops) if o.word == wi)
            ops = [o for o in ops[:first] if o.word != wi] + local + [o for o in ops[first:] if o.word != wi]

    if two_models and expected:
        chosen = [(wi, ph) for wi, p in enumerate(prons) if p.phones for ph in p.phones]
        combine(ops, align(chosen, detail_heard))
        _promote_likely_real(ops)
    if measure is not None and expected:
        chosen = [(wi, ph) for wi, p in enumerate(prons) if p.phones for ph in p.phones]
        _apply_acoustics(ops, chosen, measure(chosen, words))

    word_results = []
    issue_counter: Counter[tuple[str, str]] = Counter()
    for wi, p in enumerate(prons):
        w_ops = [o for o in ops if o.word == wi]
        info = p.describe()
        if not p.known:
            word_results.append({**info, "index": wi, "score": None, "status": "unknown", "issues": [], "heard_ipa": ""})
            continue

        score = max(0.0, 1.0 - sum(_penalty(o) for o in w_ops) / 100)

        issues = []
        phones_view = []
        last_exp_idx = max((k for k, o in enumerate(w_ops) if o.expected), default=-1)
        for k, o in enumerate(w_ops):
            if o.kind == "ins":
                tip = _insertion_tip(o.heard, w_ops, at_end=k > last_exp_idx)
                if tip and o.severity != "ok":
                    issues.append({"type": "extra", "severity": o.severity, "confidence": o.confidence, "heard": o.heard.ipa, "tip": tip})
                    issue_counter[("+", o.heard.unit)] += 1
                phones_view.append({"expected": "", "heard": o.heard.ipa, "status": "extra" if o.severity != "ok" else "ok",
                                    "expected_say": "", "expected_example": None,
                                    **_sound_view(unit_name(o.heard.unit), "heard")})
                continue
            exp_ipa = phone_ipa(o.expected)
            exp_view = _sound_view(sound_name(o.expected), "expected")
            if o.kind == "del" and o.severity == "ok":
                # Faint but present (or merged into a neighbor): not worth flagging.
                phones_view.append({"expected": exp_ipa, "heard": exp_ipa, "status": "ok", **exp_view,
                                    **_sound_view(sound_name(o.expected), "heard")})
                continue
            if o.kind == "del":
                tip = _deletion_tip(o.expected, is_final=k == last_exp_idx)
                if o.severity == "accent" and base(o.expected) == "DH":
                    tip = "The TH blended into the previous sound. That's common in fast speech, but saying the 'th' clearly sounds more careful."
                issues.append({"type": "missing", "severity": o.severity, "confidence": o.confidence, "expected": exp_ipa, "tip": tip})
                issue_counter[(base(o.expected), "-")] += 1
                phones_view.append({"expected": exp_ipa, "heard": "", "status": "missing", **exp_view,
                                    "heard_say": "", "heard_example": None})
                continue
            heard_ipa = _heard_ipa(o)
            reduced = stress(o.expected) == 0
            heard_view = _sound_view(unit_name(o.heard.unit, reduced), "heard")
            if o.severity == "ok":
                phones_view.append({"expected": exp_ipa, "heard": heard_ipa, "status": "ok", **exp_view, **heard_view})
                continue
            tip = _pair_tip(o.expected, o.heard.unit)
            if not tip:
                generic = PHONE_TIPS.get(base(o.expected))
                tip = (f"You said {_say_unit(o.heard.unit, reduced)} instead of {_say(o.expected)}."
                       + (f" Target {generic}" if generic else ""))
            issues.append({
                "type": "substitution", "severity": o.severity, "confidence": o.confidence,
                "expected": exp_ipa, "heard": heard_ipa, "tip": tip,
            })
            issue_counter[(base(o.expected), o.heard.unit)] += 1
            phones_view.append({"expected": exp_ipa, "heard": heard_ipa, "status": o.severity, **exp_view, **heard_view})

        heard_seq = [o.heard for o in w_ops if o.heard is not None]
        word_results.append({
            **info,
            "index": wi,
            "score": round(score * 100),
            "status": "good" if score >= 0.85 else "fair" if score >= 0.6 else "poor",
            "issues": issues,
            "phones": phones_view,
            "heard_ipa": "/" + "".join(h.ipa for h in heard_seq) + "/" if heard_seq else "(not heard)",
            "heard_respelling": heard_respelling(heard_seq) if heard_seq else "(not heard)",
        })

    scored = [w for w in word_results if w["score"] is not None]
    overall = round(sum(w["score"] for w in scored) / len(scored)) if scored else 0

    patterns = []
    for (exp, got), count in issue_counter.most_common(6):
        if exp == "+":
            label, label_ipa = f"extra {_say_unit(got)}", f"extra /{_unit_ipa(got)}/"
        elif got == "-":
            label, label_ipa = f"dropped {_say(exp + '1')}", f"dropped /{phone_ipa(exp + '1')}/"
        elif exp == got:
            label = f"hard {_say(exp + '1')} where Americans tap a quick “d”"
            label_ipa = f"/{phone_ipa(exp + '1')}/ → /ɾ/"
        else:
            label = f"{_say(exp + '1')} → {_say_unit(got)}"
            label_ipa = f"/{phone_ipa(exp + '1')}/ → /{_unit_ipa(got)}/"
        tip = PAIR_TIPS.get((exp, got)) or PHONE_TIPS.get(exp) or ""
        tip = tip[:1].upper() + tip[1:]  # some PHONE_TIPS start lowercase ("voiced TH ...")
        if got == "-":
            tip = _deletion_tip(exp + "1", is_final=False)
        patterns.append({"label": label, "label_ipa": label_ipa, "count": count, "tip": tip})

    return {
        "text": " ".join(words),
        "overall": overall,
        "words": word_results,
        "patterns": patterns,
        "heard_ipa": "".join(h.ipa for h in heard),
        "expected_ipa": " ".join(w["ipa"].strip("/") for w in word_results if w.get("known")),
        "expected_respelling": " ".join(w["respelling"] for w in word_results if w.get("known")),
        "heard_respelling": " ".join(w["heard_respelling"] for w in word_results if w.get("known")),
    }


def _unit_ipa(unit: str) -> str:
    return unit[1:] if unit.startswith("~") else phone_ipa(unit + "1") if unit not in {"DX", "Q"} else phone_ipa(unit)


def phrase_pronunciation(text: str) -> dict:
    from .lexicon import tokenize

    words = [pronounce(w).describe() for w in tokenize(text)]
    return {
        "words": words,
        "ipa": " ".join(w["ipa"].strip("/") for w in words if w["known"]),
        "respelling": " ".join(w["respelling"] for w in words if w["known"]),
    }


__all__ = ["analyze", "phrase_pronunciation", "to_ipa"]
