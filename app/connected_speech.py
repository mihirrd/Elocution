"""Connected-speech study material, following "American English Connected Speech: A Complete
Reference". IPA and "sounds like" spellings are the reference's own; keep them in sync with it.

GUIDE   the reference's conventions, symbols, practice method and priority order
PARTS   the five parts (plus the worked examples), in the reference's order
TOPICS  one per process (1-22), per prosody section, and the worked examples. Each has
          number    process number in the reference (None for prosody / worked examples)
          part      PARTS id
          title, rule (the one-line rule), text (the section's explanation), notes (its
          exceptions and warnings)
          nudge     True: saying the careful form gets a gentle "Americans say ... here".
                    False: the process is optional / for listening first, so the careful
                    form is simply correct (the reference's own advice).
          items     phrases from the reference's table:
                      written   as spelled (matched in sentences)
                      ipa       the reference's IPA cell, shown as is ("[ən], [n̩]", "[ˈpipəl] → [ˈpipl̩]")
                      spoken    the reference's "sounds like" (empty when it gives none)
                      detail    the table's other column (strong form, careful form, note...)
                      say       the IPA the voice uses when the cell has no stress marks
                                (the reference's sounds, with stress added; nothing else changes)
                      example, example_spoken   weak forms: the reference's example phrase
                      join      the spelling attaches to the word before (she's, they're)
          tables    information tables (prosody), shown as they are in the reference
          sentences practice sentences: text, items drilled, and optionally spoken (the
                    reference's own rendering), ipa (the reference's sentence IPA, used for the
                    voice), detail (meaning, beats, processes)
"""

from __future__ import annotations

import re

GUIDE = {
    "intro": "Fluent General American speech applies 22 sound-change processes across and inside words.",
    "conventions": [
        "IPA in square brackets shows what is actually said, e.g. [ˈwɑɾɚ]. A period marks a syllable break; "
        "ˈ marks the stressed syllable.",
        "Respelling uses everyday letters, e.g. wah-der; it is approximate, so trust the IPA when they disagree.",
        "Register: Parts 1–2 happen in all natural speech, including careful speech. Parts 3–4 grow stronger as "
        "speech gets faster and more casual.",
    ],
    "symbols": [
        ["ə", "schwa, the relaxed \"uh\"", "about"],
        ["ɚ", "r-colored schwa", "butter"],
        ["ɾ", "flap, a quick tapped \"d\"", "water"],
        ["ʔ", "glottal stop, the catch in \"uh-oh\"", "button"],
        ["ˌ / ˈ", "secondary / primary stress", "ˈphotoˌgraph"],
        ["̚", "unreleased stop", "stop that"],
        ["ː", "held (lengthened) sound", "big game"],
        ["̩ (under n, l)", "syllabic consonant", "button, little"],
    ],
    "practice_method": [
        ["Listen and mark", "Take a 30-second clip of natural American speech (a podcast or TV interview) and "
                            "transcribe it, marking each stressed syllable."],
        ["Find the processes", "Label every place where the audio differs from the spelling with its process number "
                               "from this reference."],
        ["Rhythm first", "Tap the beats on the table and say only the stressed words; then fit the reduced words in "
                         "between without slowing the beat."],
        ["Shadow", "Play the clip and speak along with it, half a second behind, matching rhythm and linking rather "
                   "than individual sounds."],
        ["Record and compare", "Record your version and play it next to the original; listen for missing flaps, "
                               "full-vowel function words, and pauses inside thought groups."],
    ],
    # The reference's priority order: the biggest gain in naturalness per hour of practice.
    "priority": [
        ["Stress timing and weak forms", ["stress-timing", "weak-forms"]],
        ["Consonant–vowel linking", ["cv-linking"]],
        ["Flapping", ["flapping"]],
        ["Syllabic n/l and glottal stop", ["syllabic", "glottal-stop"]],
        ["tr/dr affrication", ["tr-dr"]],
        ["Coalescent assimilation and reduced forms", ["coalescence", "reduced-forms"]],
    ],
    "priority_rest": "Everything else, mostly for listening comprehension",
}

PARTS = [
    {"id": "linking", "title": "Part 1 — Linking", "register": "all",
     "text": "American speakers never pause between words inside a phrase; they join each word to the next, so "
             "\"pick it up\" is heard as one word. Linking happens in all registers, including slow, careful speech."},
    {"id": "consonants", "title": "Part 2 — Consonant changes", "register": "all",
     "text": "At word boundaries American English changes /t/ and /d/ more than any other sounds: they flap, "
             "glottalize, drop, shift position, or merge with a following \"y.\" These six processes account for most "
             "of what makes speech sound American rather than British or Indian English."},
    {"id": "reductions", "title": "Part 3 — Reductions", "register": "casual",
     "text": "Unstressed grammar words lose their full vowel, and often a consonant too, so the stressed content words "
             "stand out. Pronouncing every \"to\", \"and\" and \"of\" in full is the most common reason fluent "
             "non-native speech still sounds foreign."},
    {"id": "within-word", "title": "Part 4 — Within-word processes", "register": "casual",
     "text": "Several changes happen inside single words, so even an isolated word like \"family\" or \"tree\" sounds "
             "different from its spelling. Most of these are the normal dictionary pronunciation in American English, "
             "not slang."},
    {"id": "prosody", "title": "Part 5 — Prosody (rhythm and stress)", "register": "all",
     "text": "American English is stress-timed: stressed syllables arrive at roughly even intervals, and every "
             "unstressed syllable between them is compressed to fit. That compression is the engine behind weak "
             "forms, elision, flapping and schwa loss, so getting the rhythm right makes Parts 1–4 happen almost "
             "automatically."},
    {"id": "together", "title": "Putting it together", "register": "casual",
     "text": "In real speech the processes stack: a five-word question can use four or five of them at once. Each "
             "sentence shows the careful form, the natural connected form, and the process numbers it uses."},
]


def _i(written, ipa, spoken="", **extra):
    return {"written": written, "ipa": ipa, "spoken": spoken, **extra}


def _s(text, *items, **extra):
    return {"text": text, "items": list(items), **extra}


TOPICS: list[dict] = [
    # ---------------------------------------------------------------- Part 1 — Linking
    {
        "id": "cv-linking", "number": 1, "part": "linking", "nudge": True,
        "title": "Consonant–vowel linking",
        "rule": "Final consonant starts the next word",
        "text": "When a word ends in a consonant and the next starts with a vowel, the consonant moves over and begins "
                "the next syllable. If that consonant is a t or d, it usually flaps too (process 4).",
        "notes": ["Common mistake: a glottal catch before the vowel (\"pick | it | up\") sounds choppy and non-native."],
        "items": [
            _i("pick it up", "[pɪ.kɪ.ɾʌp]", "pi-ki-dup", say="[pɪ.kɪ.ˈɾʌp]"),
            _i("turn off", "[tɝ.nɔf]", "tur-noff", say="[tɝ.ˈnɔf]"),
            _i("an apple", "[ə.næ.pl̩]", "uh-napple", say="[ə.ˈnæ.pl̩]"),
            _i("check it out", "[tʃɛ.kɪ.ɾaʊt]", "che-ki-dout", say="[tʃɛ.kɪ.ˈɾaʊt]"),
            _i("look at it", "[lʊ.kæ.ɾɪt]", "loo-ka-dit", say="[ˈlʊ.kæ.ɾɪt]"),
            _i("hold on", "[hoʊl.dɑn]", "hol-dahn", say="[hoʊl.ˈdɑn]"),
        ],
        "sentences": [
            _s("Can you pick it up on your way home?", "pick it up"),
            _s("Please turn off the lights.", "turn off"),
            _s("I had an apple for lunch.", "an apple"),
            _s("Check it out, it's really good.", "check it out"),
            _s("Look at it carefully.", "look at it"),
            _s("Hold on, I'm almost ready.", "hold on"),
        ],
    },
    {
        "id": "vv-linking", "number": 2, "part": "linking", "nudge": False,
        "title": "Vowel–vowel linking (glides)",
        "rule": "/j/ or /w/ glide bridges two vowels",
        "text": "Two vowels meeting across a word boundary are bridged by a short glide. The first vowel decides which "
                "one: after [i, eɪ, aɪ, ɔɪ] (front, ends high) → /j/ (\"y\"); after [u, oʊ, aʊ] (rounded) → /w/.",
        "notes": ["\"The\" is often said [ði] (\"thee\") before a vowel precisely so the /j/ glide can link it."],
        "items": [
            _i("I am", "[aɪ.jæm]", "I-yam", say="[aɪ.ˈjæm]"),
            _i("see it", "[si.jɪt]", "see-yit", say="[ˈsi.jɪt]"),
            _i("say it", "[seɪ.jɪt]", "say-yit", say="[ˈseɪ.jɪt]"),
            _i("the end", "[ði.jɛnd]", "thee-yend", say="[ði.ˈjɛnd]"),
            _i("go on", "[ɡoʊ.wɑn]", "go-wahn", say="[ɡoʊ.ˈwɑn]"),
            _i("do it", "[du.wɪt]", "doo-wit", say="[ˈdu.wɪt]"),
            _i("how often", "[haʊ.wɔ.fən]", "how-woffen", say="[haʊ.ˈwɔ.fən]"),
        ],
        "sentences": [
            _s("I am ready to start.", "I am"),
            _s("Let me see it first.", "see it"),
            _s("Say it again, please.", "say it"),
            _s("Wait until the end.", "the end"),
            _s("Go on, tell me more.", "go on"),
            _s("I'll do it tomorrow.", "do it"),
            _s("How often do you go there?", "how often"),
        ],
    },
    {
        "id": "linking-r", "number": 3, "part": "linking", "nudge": False,
        "title": "Linking r",
        "rule": "Final r joins the next vowel",
        "text": "American English is rhotic: every written r is pronounced, so a final r simply joins the next vowel.",
        "notes": ["The \"intrusive r\" of British English (\"law-r-and order\", \"idea-r-of\") does not occur in "
                  "General American; adding it sounds British or regional."],
        "items": [
            _i("far away", "[fɑ.ɹə.weɪ]", "fa-ruh-way", say="[ˌfɑ.ɹə.ˈweɪ]"),
            _i("for it", "[fɔ.ɹɪt]", "fo-rit", say="[ˈfɔ.ɹɪt]"),
            _i("where is", "[wɛ.ɹɪz]", "whe-riz", say="[ˈwɛ.ɹɪz]"),
            _i("there are", "[ðɛ.ɹɚ]", "the-rer", say="[ˈðɛ.ɹɚ]"),
        ],
        "sentences": [
            _s("The station is far away.", "far away"),
            _s("Thanks, I'll pay for it.", "for it"),
            _s("Where is the meeting room?", "where is"),
            _s("There are three of us.", "there are"),
        ],
    },
    # ---------------------------------------------------------------- Part 2 — Consonant changes
    {
        "id": "flapping", "number": 4, "part": "consonants", "nudge": True,
        "title": "Flapping",
        "rule": "t/d between vowels → [ɾ]",
        "text": "/t/ or /d/ becomes a quick tongue tap [ɾ] when it sits between two vowels (or r + vowel) and the "
                "second vowel is unstressed. Across word boundaries it happens whenever the word ends in t/d and the "
                "next begins with a vowel.",
        "notes": ["No flap when the following vowel is stressed: atˈtack, Itaˈlian keep a true [tʰ].",
                  "Because of flapping, latter/ladder and writer/rider sound nearly identical; the vowel before the "
                  "flap is slightly longer in ladder and rider."],
        "items": [
            _i("water", "[ˈwɑɾɚ]", "wah-der"),
            _i("better", "[ˈbɛɾɚ]", "bedder"),
            _i("city", "[ˈsɪɾi]", "siddy"),
            _i("party", "[ˈpɑɹɾi]", "par-dy"),
            _i("get it", "[ɡɛ.ɾɪt]", "ge-dit", say="[ˈɡɛ.ɾɪt]"),
            _i("a lot of", "[ə.ˈlɑ.ɾə]", "uh-lah-duh"),
            _i("what about", "[wʌ.ɾə.ˈbaʊt]", "wuh-duh-bout"),
            _i("put it on", "[pʊ.ɾɪ.ɾɑn]", "pu-di-dahn", say="[pʊ.ɾɪ.ˈɾɑn]"),
        ],
        "sentences": [
            _s("Can I get a glass of water?", "water"),
            _s("This one is much better.", "better"),
            _s("The city is very busy.", "city"),
            _s("Are you coming to the party?", "party"),
            _s("I finally get it.", "get it"),
            _s("We have a lot of work this week.", "a lot of"),
            _s("What about tomorrow?", "what about"),
            _s("Put it on the table.", "put it on"),
        ],
    },
    {
        "id": "glottal-stop", "number": 5, "part": "consonants", "nudge": True,
        "title": "Glottal stop",
        "rule": "t before n or a consonant → [ʔ]",
        "text": "/t/ is replaced by a throat catch [ʔ] in two places: before a syllabic n, and at the end of a word "
                "before a consonant.",
        "notes": ["In \"button\", the tongue stays on the ridge behind the teeth through the [ʔ] and releases straight "
                  "into [n]; there is no vowel between them."],
        "items": [
            _i("button", "[ˈbʌʔn̩]", "buh-n"),
            _i("mountain", "[ˈmaʊʔn̩]", "mow-n"),
            _i("certain", "[ˈsɝʔn̩]", "ser-n"),
            _i("not now", "[nɑʔ naʊ]", "nah' now", say="[ˈnɑʔ ˈnaʊ]"),
            _i("that car", "[ðæʔ kɑɹ]", "tha' car", say="[ðæʔ ˈkɑɹ]"),
            _i("get back", "[ɡɛʔ bæk]", "ge' back", say="[ɡɛʔ ˈbæk]"),
        ],
        "sentences": [
            _s("Press the red button.", "button"),
            _s("We climbed the mountain.", "mountain"),
            _s("Are you certain about that?", "certain"),
            _s("Not now, I'm busy.", "not now"),
            _s("Whose is that car?", "that car"),
            _s("I'll get back to you.", "get back"),
        ],
    },
    {
        "id": "elision", "number": 6, "part": "consonants", "nudge": True,
        "title": "Elision (dropped t and d)",
        "rule": "t/d between consonants drops",
        "text": "/t/ or /d/ squeezed between two consonants usually disappears, and /t/ after /n/ is often dropped "
                "inside words.",
        "notes": ["The /nt/ → [n] drop happens only before an unstressed vowel: center → cenner, but contain keeps "
                  "its [t]."],
        "items": [
            _i("next day", "[nɛks deɪ]", "neks day", say="[ˈnɛks ˈdeɪ]"),
            _i("last night", "[læs naɪt]", "las night", say="[ˈlæs ˈnaɪt]"),
            _i("must be", "[mʌs bi]", "muss be", say="[ˈmʌs bi]"),
            _i("old man", "[oʊl mæn]", "ole man", say="[ˈoʊl ˈmæn]"),
            _i("asked", "[æst]", "ast", say="[ˈæst]"),
            _i("facts", "[fæks]", "facks", say="[ˈfæks]"),
            _i("twenty", "[ˈtwɛni]", "twenny"),
            _i("internet", "[ˈɪnɚˌnɛt]", "inner-net"),
            _i("interview", "[ˈɪnɚvju]", "inner-view"),
        ],
        "sentences": [
            _s("I'll call you the next day.", "next day"),
            _s("I didn't sleep well last night.", "last night"),
            _s("That must be the new manager.", "must be"),
            _s("An old man sat by the door.", "old man"),
            _s("She asked a good question.", "asked"),
            _s("Let's look at the facts.", "facts"),
            _s("I'll be there in twenty minutes.", "twenty"),
            _s("The internet is down again.", "internet"),
            _s("I have an interview on Monday.", "interview"),
        ],
    },
    {
        "id": "place-assimilation", "number": 7, "part": "consonants", "nudge": False,
        "title": "Place assimilation",
        "rule": "n/t/d copy the next sound's position",
        "text": "/n/, /t/, /d/ at the end of a word shift toward the mouth position of the next consonant: before "
                "p/b/m they become lip sounds, before k/g they become back-of-tongue sounds.",
        "notes": ["This is a light shift: listeners still hear the intended word because context fills it in."],
        "items": [
            _i("ten boys", "[tɛm bɔɪz]", "tem boys", say="[ˈtɛm ˈbɔɪz]"),
            _i("in person", "[ɪm ˈpɝsən]", "im person"),
            _i("green bag", "[ɡɹim bæɡ]", "greem bag", say="[ˈɡɹim ˈbæɡ]"),
            _i("in case", "[ɪŋ keɪs]", "ing case", say="[ɪŋ ˈkeɪs]"),
            _i("good boy", "[ɡʊb bɔɪ]", "goob boy", say="[ˈɡʊb ˈbɔɪ]"),
            _i("that place", "[ðæp pleɪs]", "thap place", say="[ðæp ˈpleɪs]"),
            _i("good girl", "[ɡʊɡ ɡɝl]", "goog girl", say="[ˈɡʊɡ ˈɡɝl]"),
        ],
        "sentences": [
            _s("There were ten boys in the class.", "ten boys"),
            _s("Let's meet in person.", "in person"),
            _s("I'll take the green bag.", "green bag"),
            _s("Bring an umbrella, just in case.", "in case"),
            _s("He's a good boy.", "good boy"),
            _s("I love that place.", "that place"),
            _s("What a good girl!", "good girl"),
        ],
    },
    {
        "id": "coalescence", "number": 8, "part": "consonants", "nudge": True,
        "title": "Coalescent assimilation (yod coalescence)",
        "rule": "t/d/s/z + you merge",
        "text": "A final /t, d, s, z/ followed by \"you/your/yet\" fuses with the /j/ into a single new sound.",
        "notes": ["The same fusion is permanent inside words such as nature [ˈneɪtʃɚ] and education [ˌɛdʒəˈkeɪʃən]."],
        "items": [
            _i("don't you", "[ˈdoʊn.tʃə]", "doncha", detail="t + y → [tʃ] \"ch\""),
            _i("what you", "[ˈwʌ.tʃə]", "whatcha", detail="t + y → [tʃ] \"ch\""),
            _i("got you", "[ˈɡɑ.tʃə]", "gotcha", detail="t + y → [tʃ] \"ch\""),
            _i("did you", "[ˈdɪ.dʒə]", "didja", detail="d + y → [dʒ] \"j\""),
            _i("would you", "[ˈwʊ.dʒə]", "wouldja", detail="d + y → [dʒ] \"j\""),
            _i("miss you", "[ˈmɪ.ʃu]", "mishoo", detail="s + y → [ʃ] \"sh\""),
            _i("this year", "[ðɪʃ jɪɹ]", "thish year", detail="s + y → [ʃ] \"sh\"", say="[ðɪʃ ˈjɪɹ]"),
            _i("as you", "[æ.ʒu]", "azhoo", detail="z + y → [ʒ] \"zh\""),
            _i("how's your", "[haʊ.ʒɚ]", "how-zhur", detail="z + y → [ʒ] \"zh\"", say="[ˈhaʊ.ʒɚ]"),
        ],
        "sentences": [
            _s("Don't you want to come?", "don't you"),
            _s("Is that what you wanted?", "what you"),
            _s("Got you, I'll fix it now.", "got you"),
            _s("Did you get my message?", "did you"),
            _s("Would you like some water?", "would you"),
            _s("I really miss you.", "miss you"),
            _s("This year has been busy.", "this year"),
            _s("As you know, we start at nine.", "as you"),
            _s("How's your new job?", "how's your"),
        ],
    },
    {
        "id": "gemination", "number": 9, "part": "consonants", "nudge": False,
        "title": "Gemination (shared consonants)",
        "rule": "Same consonant twice = one held sound",
        "text": "When one word ends with the same consonant the next begins with, say it once, held slightly longer, "
                "with no release between.",
        "notes": ["It also applies to near-twins: good time [ɡʊtːaɪm] (d before t), bad guy (d assimilates, then "
                  "holds g)."],
        "items": [
            _i("big game", "[bɪɡːeɪm]", "bi-game", detail="held g", say="[ˌbɪˈɡːeɪm]"),
            _i("bus stop", "[bʌsːtɑp]", "bu-stop", detail="held s", say="[ˈbʌsːtɑp]"),
            _i("hot tea", "[hɑtːi]", "ho-tea", say="[ˌhɑˈtːi]"),
            _i("black cat", "[blækːæt]", "bla-cat", say="[ˌblæˈkːæt]"),
            _i("some more", "[səmːɔɹ]", "suh-more", say="[səˈmːɔɹ]"),
        ],
        "sentences": [
            _s("Did you watch the big game?", "big game"),
            _s("I'll meet you at the bus stop.", "bus stop"),
            _s("Would you like some hot tea?", "hot tea"),
            _s("A black cat crossed the road.", "black cat"),
            _s("Can I have some more rice?", "some more"),
        ],
    },
    # ---------------------------------------------------------------- Part 3 — Reductions
    {
        "id": "weak-forms", "number": 10, "part": "reductions", "nudge": True,
        "title": "Weak forms",
        "rule": "Function words reduce to schwa",
        "text": "Use the strong form only when the word is stressed, quoted, or at the end of a phrase "
                "(\"Who's it for?\" → [fɔɹ]).",
        "notes": ["can vs. can't: weak can is [kən]; can't keeps a full vowel [kæn(ʔ)] and is stressed. American "
                  "listeners tell them apart by that vowel and stress, not by hearing the t."],
        "items": [
            _i("a", "[ə]", "uh", detail="strong [eɪ]", example="a cup", example_spoken="uh cup"),
            _i("the", "[ðə]", "thuh", detail="strong [ði]", example="the book", example_spoken="thuh book"),
            _i("and", "[ən], [n̩]", "'n'", detail="strong [ænd]", example="rock and roll",
               example_spoken="rock 'n' roll", say="[n̩]"),
            _i("to", "[tə]", "tuh", detail="strong [tu]", example="want to go", example_spoken="want tuh go"),
            _i("of", "[əv], [ə]", "uh", detail="strong [ʌv]", example="cup of coffee", example_spoken="cuppa coffee"),
            _i("for", "[fɚ]", "fer", detail="strong [fɔɹ]", example="for you", example_spoken="fer you"),
            _i("from", "[fɹəm]", "frum", detail="strong [fɹʌm]", example="from home", example_spoken="frum home"),
            _i("at", "[ət]", "ut", detail="strong [æt]", example="at home", example_spoken="ut home"),
            _i("can", "[kən]", "kin", detail="strong [kæn]", example="I can do it", example_spoken="I kin do it"),
            _i("was", "[wəz]", "wuz", detail="strong [wʌz]", example="it was fine", example_spoken="it wuz fine"),
            _i("have", "[əv]", "a", detail="strong [hæv]", example="should have", example_spoken="shoulda", join=True),
            _i("has", "[əz]", "'s", detail="strong [hæz]", example="she has been", example_spoken="she's been",
               join=True),
            _i("do", "[də]", "duh", detail="strong [du]", example="how do you", example_spoken="how-duh-ya"),
            _i("you", "[jə]", "ya", detail="strong [ju]", example="see you", example_spoken="see ya"),
            _i("your", "[jɚ]", "yer", detail="strong [jɔɹ]", example="your car", example_spoken="yer car"),
            _i("them", "[əm]", "'em", detail="strong [ðɛm]", example="tell them", example_spoken="tell 'em"),
            _i("are", "[ɚ]", "'re", detail="strong [ɑɹ]", example="they are", example_spoken="they're", join=True),
            _i("or", "[ɚ]", "er", detail="strong [ɔɹ]", example="two or three", example_spoken="two er three"),
            _i("but", "[bət]", "b't", detail="strong [bʌt]", example="but why", example_spoken="b't why"),
            _i("some", "[səm]", "s'm", detail="strong [sʌm]", example="some water", example_spoken="s'm water"),
        ],
        "sentences": [
            _s("I need a cup of coffee.", "a", "of", spoken="I need uh cuppa coffee."),
            _s("Put the book on the shelf.", "the"),
            _s("Salt and pepper, please.", "and"),
            _s("I want to go home.", "to"),
            _s("This is for you.", "for", "you"),
            _s("I'm working from home today.", "from"),
            _s("She's at home.", "at"),
            _s("I can do it.", "can"),
            _s("It was fine.", "was"),
            _s("You should have told me.", "have"),
            _s("She has been busy.", "has"),
            _s("How do you know?", "do", "you", spoken="How-duh-ya know?"),
            _s("Is this your car?", "your"),
            _s("Tell them I said hi.", "them"),
            _s("They are on their way.", "are"),
            _s("Two or three days.", "or"),
            _s("I'd like to, but I'm busy.", "but"),
            _s("Some water, please.", "some"),
            _s("Who's it for?", detail="Strong form: \"for\" ends the phrase, so it stays [fɔɹ]."),
        ],
    },
    {
        "id": "reduced-forms", "number": 11, "part": "reductions", "nudge": True,
        "title": "Informal reduced forms",
        "rule": "Common chunks fuse",
        "text": "These chunks are standard in casual American speech, including on TV and in meetings. They are "
                "written in full but spoken fused.",
        "notes": ["\"Wanna\" is only possible when \"want\" and \"to\" belong together: Who do you wanna see? works, "
                  "but Who do you want to win? does not reduce, because \"who\" is the one winning."],
        "items": [
            _i("going to", "[ˈɡʌnə]", "gonna"),
            _i("want to", "[ˈwɑnə]", "wanna"),
            _i("got to", "[ˈɡɑɾə]", "gotta"),
            _i("have to", "[ˈhæftə]", "hafta"),
            _i("has to", "[ˈhæstə]", "hasta"),
            _i("supposed to", "[səˈpoʊstə]", "s'poseta"),
            _i("used to", "[ˈjustə]", "yoosta"),
            _i("ought to", "[ˈɑɾə]", "oughta"),
            _i("let me", "[ˈlɛmi]", "lemme"),
            _i("give me", "[ˈɡɪmi]", "gimme"),
            _i("kind of", "[ˈkaɪndə]", "kinda"),
            _i("sort of", "[ˈsɔɹɾə]", "sorta"),
            _i("out of", "[ˈaʊɾə]", "outta"),
            _i("don't know", "[dəˈnoʊ]", "dunno"),
            _i("should have", "[ˈʃʊdə]", "shoulda"),
            _i("could have", "[ˈkʊdə]", "coulda"),
            _i("would have", "[ˈwʊdə]", "woulda"),
            _i("what do you", "[ˈwʌɾəjə]", "whaddaya"),
            _i("what are you", "[ˈwʌɾɚjə]", "whaddarya"),
            _i("did you eat", "[ˈdʒit]", "jeet"),
        ],
        "sentences": [
            _s("I'm going to call you after lunch.", "going to"),
            _s("Do you want to grab a coffee?", "want to"),
            _s("I've got to finish this report.", "got to"),
            _s("We have to leave soon.", "have to"),
            _s("He has to sign the form.", "has to"),
            _s("We're supposed to meet at noon.", "supposed to"),
            _s("I used to live in Chicago.", "used to"),
            _s("You ought to try the soup.", "ought to"),
            _s("Let me check my calendar.", "let me"),
            _s("Give me a second.", "give me"),
            _s("I'm kind of tired today.", "kind of"),
            _s("It was sort of a surprise.", "sort of"),
            _s("Get out of the car.", "out of"),
            _s("I don't know where he went.", "don't know"),
            _s("You should have called me.", "should have"),
            _s("We could have won.", "could have"),
            _s("I would have helped you.", "would have"),
            _s("What do you think?", "what do you"),
            _s("What are you doing later?", "what are you"),
            _s("Did you eat yet?", "did you eat"),
        ],
    },
    {
        "id": "h-dropping", "number": 12, "part": "reductions", "nudge": True,
        "title": "H-dropping",
        "rule": "h drops in unstressed he/him/her",
        "text": "In unstressed he, him, her, his, have, has, had, the /h/ drops and the word links to the one before it.",
        "notes": ["At the start of a sentence or under stress the h stays: He left. / I saw HIM, not her."],
        "items": [
            _i("tell him", "[ˈtɛ.lɪm]", "tell-im"),
            _i("ask her", "[ˈæs.kɚ]", "ass-ker"),
            _i("did he", "[ˈdɪ.di]", "diddy"),
            _i("was his", "[wə.zɪz]", "wuh-ziz"),
            _i("must have", "[ˈmʌs.təv]", "musta"),
        ],
        "sentences": [
            _s("Tell him I said hi.", "tell him"),
            _s("Ask her if she's free.", "ask her"),
            _s("Did he call you back?", "did he"),
            _s("What was his name again?", "was his"),
            _s("You must have been tired.", "must have"),
            _s("He left.", detail="Start of a sentence: the h stays."),
        ],
    },
    {
        "id": "dh-assimilation", "number": 13, "part": "reductions", "nudge": False,
        "title": "/ð/ assimilation",
        "rule": "th copies n/l/z before it",
        "text": "In fast, casual speech, the \"th\" of the, that, them, this, there takes on the sound just before it "
                "(n, l, or z).",
        "notes": ["Treat this as a listening skill first; in your own careful speech, a clear [ð] is always correct."],
        "items": [
            _i("in the", "[ɪ.nə]", "in-nuh"),
            _i("on the", "[ɑ.nə]", "ah-nuh"),
            _i("all the", "[ɔ.lə]", "al-luh", say="[ˈɔ.lə]"),
            _i("is that", "[ɪ.zæt]", "iz-zat", say="[ɪ.ˈzæt]"),
            _i("was that", "[wə.zæt]", "wuz-zat", say="[wə.ˈzæt]"),
        ],
        "sentences": [
            _s("The keys are in the car.", "in the"),
            _s("It's on the table.", "on the"),
            _s("I ate all the cookies.", "all the"),
            _s("Is that your bag?", "is that"),
            _s("Who was that man?", "was that"),
        ],
    },
    {
        "id": "ing", "number": 14, "part": "reductions", "nudge": False,
        "title": "-ing → -in'",
        "rule": "[ɪŋ] → [ɪn]",
        "text": "In casual speech, unstressed -ing is [ɪn] instead of [ɪŋ]. It is informal, not incorrect, and used by "
                "educated speakers in relaxed settings.",
        "notes": ["It never applies to stressed -ing words: sing, thing, king always keep [ŋ]."],
        "items": [
            _i("going", "[ˈɡoʊ.ɪn]", "goin'", detail="careful [ˈɡoʊ.ɪŋ]"),
            _i("nothing", "[ˈnʌθ.ɪn]", "nothin'", detail="careful [ˈnʌθ.ɪŋ]"),
            _i("something", "[ˈsʌm.θɪn]", "somethin'", detail="careful [ˈsʌm.θɪŋ]"),
            _i("working", "[ˈwɝ.kɪn]", "workin'", detail="careful [ˈwɝ.kɪŋ]"),
        ],
        "sentences": [
            _s("Where are you going?", "going"),
            _s("There's nothing to worry about.", "nothing"),
            _s("I forgot something.", "something"),
            _s("I'm working late tonight.", "working"),
        ],
    },
    # ---------------------------------------------------------------- Part 4 — Within-word processes
    {
        "id": "schwa-elision", "number": 15, "part": "within-word", "nudge": True,
        "title": "Schwa elision (syllable deletion)",
        "rule": "Unstressed vowel drops a syllable",
        "text": "An unstressed vowel between two consonants, usually right after the stressed syllable, drops out and "
                "the word loses a syllable.",
        "notes": [],
        "items": [
            _i("family", "[ˈfæm.li]", "fam-lee", detail="spelled fam-i-ly (3)"),
            _i("chocolate", "[ˈtʃɑk.lət]", "chock-lit", detail="spelled choc-o-late (3)"),
            _i("every", "[ˈɛv.ɹi]", "ev-ree", detail="spelled ev-er-y (3)"),
            _i("different", "[ˈdɪf.ɹənt]", "dif-rent", detail="spelled dif-fer-ent (3)"),
            _i("probably", "[ˈpɹɑb.li]", "prob-lee", detail="spelled prob-a-bly (3)"),
            _i("camera", "[ˈkæm.ɹə]", "cam-ruh", detail="spelled cam-er-a (3)"),
            _i("vegetable", "[ˈvɛdʒ.tə.bl̩]", "vej-tuh-bl", detail="spelled veg-e-ta-ble (4)"),
            _i("interesting", "[ˈɪn.tɹɛs.tɪŋ]", "in-tress-ting", detail="spelled in-ter-est-ing (4)"),
            _i("comfortable", "[ˈkʌmf.tɚ.bl̩]", "cumf-ter-bl", detail="spelled com-for-ta-ble (4)"),
            _i("temperature", "[ˈtɛm.pɚ.tʃɚ]", "tem-per-cher", detail="spelled tem-per-a-ture (4)"),
            _i("Wednesday", "[ˈwɛnz.deɪ]", "wenz-day", detail="spelled Wed-nes-day (3)"),
        ],
        "sentences": [
            _s("My family lives in Delhi.", "family"),
            _s("I love dark chocolate.", "chocolate"),
            _s("I go there every week.", "every"),
            _s("That's a different story.", "different"),
            _s("It'll probably rain tomorrow.", "probably"),
            _s("Turn on your camera, please.", "camera"),
            _s("Is a tomato a vegetable?", "vegetable"),
            _s("That was a really interesting talk.", "interesting"),
            _s("These chairs are comfortable.", "comfortable"),
            _s("The temperature dropped last night.", "temperature"),
            _s("The meeting is on Wednesday.", "Wednesday"),
        ],
    },
    {
        "id": "syllabic", "number": 16, "part": "within-word", "nudge": True,
        "title": "Syllabic consonants",
        "rule": "n/l form a syllable alone",
        "text": "After /t/ or /d/ (and often after other consonants), /n/ and /l/ form a syllable by themselves with no "
                "vowel. The tongue stays on the ridge and the sound is released through the nose (n) or the sides of "
                "the tongue (l).",
        "notes": ["Adding a full vowel (\"lit-tel\", \"sud-den\") is a strong marker of non-native speech."],
        "items": [
            _i("little", "[ˈlɪɾl̩]", "li-dl"),
            _i("middle", "[ˈmɪɾl̩]", "mi-dl"),
            _i("bottle", "[ˈbɑɾl̩]", "bah-dl"),
            _i("sudden", "[ˈsʌdn̩]", "sud-n"),
            _i("written", "[ˈɹɪʔn̩]", "rih-n"),
            _i("button", "[ˈbʌʔn̩]", "buh-n"),
            _i("people", "[ˈpipəl] → [ˈpipl̩]", "pee-pl"),
        ],
        "sentences": [
            _s("Wait a little longer.", "little"),
            _s("Put it in the middle.", "middle"),
            _s("I bought a bottle of water.", "bottle"),
            _s("It was a sudden change.", "sudden"),
            _s("It's written on the board.", "written"),
            _s("Press the button twice.", "button"),
            _s("There were so many people.", "people"),
        ],
    },
    {
        "id": "unreleased", "number": 17, "part": "within-word", "nudge": False,
        "title": "Unreleased stops",
        "rule": "Final stop has no puff of air",
        "text": "A final /p, t, k, b, d, g/, or one before another consonant, is formed in the mouth but held: no puff "
                "of air comes out. The listener hears it through the vowel cut-off before it.",
        "notes": [],
        "items": [
            _i("stop that", "[stɑp̚ ðæt]", "stop' that", say="[ˈstɑp ˈðæt]"),
            _i("good day", "[ɡʊd̚ deɪ]", "goo' day", say="[ɡʊd ˈdeɪ]"),
            _i("back door", "[bæk̚ dɔɹ]", "ba' door", say="[ˈbæk ˈdɔɹ]"),
            _i("sit down", "[sɪt̚ daʊn]", "si' down", say="[sɪt ˈdaʊn]"),
            _i("big deal", "[bɪɡ̚ dil]", "bi' deal", say="[ˈbɪɡ ˈdil]"),
            _i("I don't know", "[aɪ doʊn̚ noʊ]", "don' know", detail="at the end of a phrase",
               say="[aɪ doʊn ˈnoʊ]"),
        ],
        "sentences": [
            _s("Please stop that right now.", "stop that"),
            _s("Have a good day.", "good day"),
            _s("Use the back door.", "back door"),
            _s("Please sit down.", "sit down"),
            _s("It's not a big deal.", "big deal"),
            _s("I don't know.", "I don't know", spoken="I don' know."),
        ],
    },
    {
        "id": "tr-dr", "number": 18, "part": "within-word", "nudge": True,
        "title": "tr / dr affrication",
        "rule": "tr → chr, dr → jr",
        "text": "Before /r/, /t/ slides toward \"ch\" [tʃ] and /d/ toward \"j\" [dʒ], because the tongue pulls back for "
                "the r. Learners most often miss this process.",
        "notes": ["Many speakers also shift str toward shtr (\"shtreet\"); this is common but regional, so it is "
                  "optional."],
        "items": [
            _i("tree", "[tʃɹi]", "chree", say="[ˈtʃɹi]"),
            _i("train", "[tʃɹeɪn]", "chrain", say="[ˈtʃɹeɪn]"),
            _i("true", "[tʃɹu]", "chroo", say="[ˈtʃɹu]"),
            _i("country", "[ˈkʌn.tʃɹi]", "cun-chree"),
            _i("drive", "[dʒɹaɪv]", "jrive", say="[ˈdʒɹaɪv]"),
            _i("dream", "[dʒɹim]", "jream", say="[ˈdʒɹim]"),
            _i("address", "[ˈæ.dʒɹɛs]", "a-jress"),
        ],
        "sentences": [
            _s("There's a big tree outside.", "tree"),
            _s("I missed the train.", "train"),
            _s("Is that true?", "true"),
            _s("Which country are you from?", "country"),
            _s("I'll drive you home.", "drive"),
            _s("I had a strange dream.", "dream"),
            _s("What's your email address?", "address"),
        ],
    },
    {
        "id": "clusters", "number": 19, "part": "within-word", "nudge": False,
        "title": "Cluster simplification",
        "rule": "3+ consonants lose one",
        "text": "Three or more consonants in a row lose one, usually the middle stop or the th.",
        "notes": [],
        "items": [
            _i("months", "[mʌns]", "munss", say="[ˈmʌns]"),
            _i("clothes", "[kloʊz]", "close", say="[ˈkloʊz]"),
            _i("fifths", "[fɪfs]", "fifs", say="[ˈfɪfs]"),
            _i("sixths", "[sɪks]", "sicks", say="[ˈsɪks]"),
            _i("texts", "[tɛks]", "tecks", say="[ˈtɛks]"),
            _i("tests", "[tɛss] → [tɛs]", "tess", say="[ˈtɛs]"),
            _i("friendship", "[ˈfɹɛn.ʃɪp]", "fren-ship"),
            _i("exactly", "[ɪɡˈzæk.li]", "ig-zack-lee"),
        ],
        "sentences": [
            _s("It took three months.", "months"),
            _s("I need to wash my clothes.", "clothes"),
            _s("Two fifths of the class passed.", "fifths"),
            _s("Cut the cake into sixths.", "sixths"),
            _s("She sent me three texts.", "texts"),
            _s("We have two tests next week.", "tests"),
            _s("Their friendship is strong.", "friendship"),
            _s("That's exactly right.", "exactly"),
        ],
    },
    {
        "id": "epenthesis", "number": 20, "part": "within-word", "nudge": False,
        "title": "Epenthesis (added stops)",
        "rule": "A stop slips in after a nasal",
        "text": "Between a nasal and a following s, t, or th, the airflow change creates a small extra stop.",
        "notes": [],
        "items": [
            _i("prince", "[pɹɪnts]", "prints", detail="sounds like \"prints\"", say="[ˈpɹɪnts]"),
            _i("sense", "[sɛnts]", "cents", detail="sounds like \"cents\"", say="[ˈsɛnts]"),
            _i("hamster", "[ˈhæmpstɚ]", detail="a p appears"),
            _i("something", "[ˈsʌmpθɪŋ]", detail="a p appears"),
            _i("warmth", "[wɔɹmpθ]", detail="a p appears", say="[ˈwɔɹmpθ]"),
            _i("length", "[lɛŋkθ]", detail="a k appears", say="[ˈlɛŋkθ]"),
        ],
        "sentences": [
            _s("The prince waved to the crowd.", "prince"),
            _s("That makes sense.", "sense"),
            _s("My son has a hamster.", "hamster"),
            _s("I forgot something.", "something"),
            _s("I love the warmth of the sun.", "warmth"),
            _s("What's the length of the room?", "length"),
        ],
    },
    {
        "id": "smoothing", "number": 21, "part": "within-word", "nudge": False,
        "title": "Smoothing (vowel compression)",
        "rule": "Diphthong + r collapses",
        "text": "A diphthong followed by r or another vowel collapses, so the word loses a syllable or a glide.",
        "notes": [],
        "items": [
            _i("fire", "[faɪɚ] → [faɚ]", detail="one syllable", say="[ˈfaɚ]"),
            _i("our", "[aʊɚ] → [ɑɹ]", "are", detail="same as \"are\"", say="[ˈɑɹ]"),
            _i("hour", "[aʊɚ] → [aɚ]", detail="one syllable", say="[ˈaɚ]"),
            _i("really", "[ˈɹiə.li] → [ˈɹɪ.li]", "rih-lee"),
            _i("idea", "[aɪˈdiə]", detail="not smoothed: stress protects it"),
            _i("going to", "[ˈɡoʊ.ɪŋ tə] → [ˈɡʌnə]", "gonna"),
        ],
        "sentences": [
            _s("Sit by the fire.", "fire"),
            _s("This is our house.", "our"),
            _s("The meeting lasted an hour.", "hour"),
            _s("That's really nice.", "really"),
            _s("That's a great idea.", "idea"),
            _s("I'm going to call you later.", "going to"),
        ],
    },
    {
        "id": "flapped-to", "number": 22, "part": "within-word", "nudge": True,
        "title": "Flapped \"to\"",
        "rule": "to after a vowel → duh",
        "text": "After a vowel or r, the /t/ of weak \"to\" flaps, so \"to\" sounds like \"duh.\"",
        "notes": ["In \"need to\" the d and t merge (gemination), then the combined sound flaps."],
        "items": [
            _i("go to", "[ɡoʊ.ɾə]", "go-duh", say="[ˈɡoʊ.ɾə]"),
            _i("how to", "[haʊ.ɾə]", "how-duh", say="[ˈhaʊ.ɾə]"),
            _i("where to", "[wɛɹ.ɾə]", "wair-duh", say="[ˈwɛɹ.ɾə]"),
            _i("try to", "[tʃɹaɪ.ɾə]", "chry-duh", say="[ˈtʃɹaɪ.ɾə]"),
            _i("need to", "[ni.ɾə]", "nee-duh", say="[ˈni.ɾə]"),
        ],
        "sentences": [
            _s("I have to go to the bank.", "go to"),
            _s("Do you know how to cook?", "how to"),
            _s("I'm not sure where to start.", "where to"),
            _s("Try to relax.", "try to"),
            _s("I need to leave now.", "need to"),
        ],
    },
    # ---------------------------------------------------------------- Part 5 — Prosody
    {
        "id": "stress-timing", "number": None, "part": "prosody", "nudge": False,
        "title": "Stress timing",
        "rule": "Stressed beats come at even intervals; everything between is squeezed",
        "text": "The three sentences below take nearly the same time to say, because each has three stressed beats; "
                "the extra words are squeezed between the beats.",
        "notes": ["Syllable-timed languages (Hindi, Marathi, Spanish, French) give each syllable similar length; "
                  "carrying that rhythm into English is the largest single source of a non-native accent."],
        "items": [],
        "sentences": [
            _s("Cats chase mice.", spoken="CATS CHASE MICE.", detail="3 beats"),
            _s("The cats will chase the mice.", spoken="The CATS will CHASE the MICE.", detail="3 beats"),
            _s("The cats have been chasing the mice.", spoken="The CATS have been CHASing the MICE.",
               detail="3 beats"),
        ],
    },
    {
        "id": "content-function", "number": None, "part": "prosody", "nudge": False,
        "title": "Content words vs. function words",
        "rule": "Content words are stressed; function words are reduced",
        "text": "A function word gets full stress only when it is contrasted (\"I said ON the table, not UNder it\") "
                "or at the end of a phrase (\"What are you looking AT?\").",
        "notes": [],
        "items": [],
        "tables": [{
            "headers": ["Stressed (content words)", "Reduced (function words)"],
            "rows": [
                ["Nouns: car, idea, Purdue", "Articles: a, an, the"],
                ["Main verbs: run, think, build", "Prepositions: to, of, for, at, from"],
                ["Adjectives: fast, blue", "Auxiliaries: can, will, have, do, be"],
                ["Adverbs: quickly, never", "Pronouns: he, him, you, them"],
                ["Negatives: not, can't, don't", "Conjunctions: and, but, or, that"],
                ["Question words: what, where, how", "Possessives: my, your, his"],
            ],
        }],
        "sentences": [
            _s("I said on the table, not under it.", spoken="I said ON the table, not UNder it.",
               detail="Contrast: the function words take the stress."),
            _s("What are you looking at?", spoken="What are you looking AT?",
               detail="End of the phrase: \"at\" is stressed."),
        ],
    },
    {
        "id": "sentence-focus", "number": None, "part": "prosody", "nudge": False,
        "title": "Sentence focus",
        "rule": "The new or contrasted word takes the strongest stress",
        "text": "The word carrying new or contrasted information takes the strongest stress, with a pitch jump, and "
                "moving it changes the meaning. By default, focus falls on the last content word of the phrase: "
                "I'm going to the STORE.",
        "notes": [],
        "items": [],
        "sentences": [
            _s("I didn't say he stole it.", spoken="I DIDN'T say he stole it.", detail="I deny saying it."),
            _s("I didn't say he stole it.", spoken="I didn't SAY he stole it.", detail="I implied it."),
            _s("I didn't say he stole it.", spoken="I didn't say HE stole it.", detail="Someone else stole it."),
            _s("I didn't say he stole it.", spoken="I didn't say he STOLE it.", detail="He borrowed it."),
            _s("I didn't say he stole it.", spoken="I didn't say he stole IT.", detail="He stole something else."),
            _s("I'm going to the store.", spoken="I'm going to the STORE.",
               detail="Default: the last content word."),
        ],
    },
    {
        "id": "thought-groups", "number": None, "part": "prosody", "nudge": False,
        "title": "Thought groups",
        "rule": "Speak in chunks of 2–5 stressed words",
        "text": "Speech is delivered in chunks of roughly 2–5 stressed words, each with one focus word and a small pitch "
                "fall or rise at its end. Linking and reduction apply within a chunk; a short pause or pitch reset "
                "separates chunks.",
        "notes": ["Pausing mid-chunk (\"I'd left | my keys\") breaks linking and makes even correct sounds seem "
                  "foreign."],
        "items": [],
        "sentences": [
            _s("When I got home, I realized I'd left my keys at the office.",
               spoken="When I got HOME / I realized / I'd left my KEYS / at the OFfice."),
        ],
    },
    {
        "id": "intonation", "number": None, "part": "prosody", "nudge": False,
        "title": "Intonation basics",
        "rule": "Statements fall, yes/no questions rise",
        "text": "",
        "notes": [],
        "items": [],
        "tables": [{
            "headers": ["Pattern", "Use", "Example"],
            "rows": [
                ["Fall ↘", "Statements, wh-questions, commands", "Where do you LIVE? ↘"],
                ["Rise ↗", "Yes/no questions", "Do you live HERE? ↗"],
                ["Fall-rise ↘↗", "Unfinished thought, polite doubt, contrast", "Well, I COULD… ↘↗"],
                ["Rise then fall", "Lists: rise on each item, fall on the last", "apples ↗, pears ↗, and plums ↘"],
            ],
        }],
        "sentences": [
            _s("Where do you live?", spoken="Where do you LIVE? ↘", detail="Fall"),
            _s("Do you live here?", spoken="Do you live HERE? ↗", detail="Rise"),
            _s("Well, I could.", spoken="Well, I COULD… ↘↗", detail="Fall-rise"),
            _s("Apples, pears, and plums.", spoken="apples ↗, pears ↗, and plums ↘", detail="Rise then fall"),
        ],
    },
    # ---------------------------------------------------------------- Putting it together
    {
        "id": "worked-examples", "number": None, "part": "together", "nudge": False,
        "title": "Worked examples",
        "rule": "Several processes at once",
        "text": "In real speech the processes stack: a five-word question can use four or five of them at once.",
        "notes": [],
        "items": [],
        "sentences": [
            _s("What are you going to do?", spoken="whaddarya gonna do", ipa="[ˈwʌɾɚjə ˈɡʌnə du]",
               detail="Processes 4, 10, 11"),
            _s("Did you eat yet?", spoken="jeet yet", ipa="[ˈdʒit jɛt]", detail="Processes 8, 11"),
            _s("I don't know what to do.", spoken="I dunno whadduh do", ipa="[aɪ dəˈnoʊ ˈwʌɾə du]",
               detail="Processes 4, 10, 11"),
            _s("Let me get it for you.", spoken="lemme ge-dit fer ya", ipa="[ˈlɛmi ˈɡɛɾɪt fɚjə]",
               detail="Processes 1, 4, 10, 11"),
            _s("Put it in the bottle.", spoken="pu-di-din-nuh bah-dl", ipa="[ˈpʊɾɪɾɪnə ˈbɑɾl̩]",
               detail="Processes 1, 4, 13, 16"),
            _s("I should have asked him.", spoken="I shoulda as-tim", ipa="[aɪ ˈʃʊdə ˈæstɪm]",
               detail="Processes 6, 11, 12"),
            _s("Tell them to try it again.", spoken="tell-em tuh chry-yi-duh-gen",
               ipa="[ˈtɛləm tə ˈtʃɹaɪjɪɾəˈɡɛn]", detail="Processes 1, 2, 4, 10, 18"),
            _s("Don't you want to go to the city?", spoken="doncha wanna go-duh thuh siddy",
               ipa="[ˈdoʊntʃə ˈwɑnə ˈɡoʊɾə ðə ˈsɪɾi]", detail="Processes 4, 8, 11, 22"),
            _s("I've got to finish it next month.", spoken="I've gotta fini-shit neks munth",
               ipa="[aɪv ˈɡɑɾə ˈfɪnɪʃɪt nɛks mʌnθ]", detail="Processes 1, 6, 11"),
            _s("It was probably in the interview.", spoken="it wuz prob-lee in-nuh inner-view",
               ipa="[ɪt wəz ˈpɹɑbli ɪnə ˈɪnɚvju]", detail="Processes 6, 10, 13, 15"),
        ],
    },
]


def topic(topic_id: str) -> dict | None:
    return next((t for t in TOPICS if t["id"] == topic_id), None)


def sentence_spoken(t: dict, s: dict) -> str:
    """How a sentence sounds: the reference's own rendering when it gives one, otherwise the
    sentence with each drilled item replaced by the reference's spelling of it."""
    if s.get("spoken"):
        return s["spoken"]
    text = s["text"]
    by_name = {i["written"]: i for i in t["items"]}
    for name in sorted(s["items"], key=len, reverse=True):
        item = by_name[name]
        if not item.get("spoken"):
            continue
        pattern = r"(?<![A-Za-z'])" + re.escape(name) + r"(?![A-Za-z'])"
        if item.get("join"):  # "she has been" -> "she's been"
            text = re.sub(r"\s+" + pattern, lambda m: item["spoken"], text, flags=re.I)
        else:
            text = re.sub(pattern, lambda m: item["spoken"], text, flags=re.I)
    return text[:1].upper() + text[1:]


for _t in TOPICS:
    for _sentence in _t["sentences"]:
        _sentence["spoken"] = sentence_spoken(_t, _sentence)
