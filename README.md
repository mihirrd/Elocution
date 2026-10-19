# American Accent Coach

A local app that records your voice, works out which sounds you actually made, compares them with
General American pronunciation, and tells you what to fix, with the correct IPA, a plain-English
respelling, and audio for every word.

## Run it

Requires [uv](https://docs.astral.sh/uv/) and `ffmpeg` (`brew install ffmpeg`).

```bash
uv sync
uv run python -m app
```

Open http://127.0.0.1:8000 in Chrome, Safari, or Firefox and allow microphone access.
The first start downloads the speech models and voice (~3.3 GB). Requires Python 3.12 (uv installs it). After that everything runs offline.

## What it does

- **Practice a sentence**: pick a focus (TH, R, R/L, V/W, short vowels, the American A, flap T,
  final consonants) or type your own sentence, listen to an American voice, then record yourself.
- **Free speech**: say anything. Whisper works out which words you meant, then each word is checked.
- **Pronunciation lookup**: type any word or sentence to get the American IPA, a respelling
  (`comfortable` → `KUHM-fur-duh-buhl`), ARPAbet, accepted variants, and notes.

Pronunciations are shown as plain-English "say it like" spellings (`about` → `uh-BOWT`; CAPS marks
the stressed syllable), and each sound is named with an example word (`"th" (as in think)`). Switch
on **Show IPA symbols** in the top right to also see IPA and ARPAbet.

For each recording you get:
- an overall score, and each word colored good / needs work / mispronounced
- per word: the correct IPA, what you said in IPA, a sound-by-sound comparison, and buttons to hear
  the correct version (normal or slow) and replay **your own** version of that word
- a specific tip for each mistake (e.g. "/θ/ → /s/: move the tongue forward so the tip touches the
  back of the upper teeth…")
- your recurring mistakes across the recording
- what a listener understood (the Whisper transcript), which shows whether you were intelligible

Space bar starts and stops recording.

## The voice

**Listen** and **Slowly** use [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0),
a small open-source voice model that runs locally (~0.3 s per sentence, then cached). It's given
phonemes, not text, built from the same American pronunciations the coach scores against, so the voice
says exactly what it teaches (the soft T in "water", the R in "corner").

## How it works

```
mic → browser MediaRecorder → /api/analyze
        ├─ ffmpeg → 16 kHz mono, trim silence
        ├─ phoneme recognizer A: mrrubino/wav2vec2-large-xlsr-53-l2-arctic-phoneme
        │     trained on L2-ARCTIC, where annotators wrote down what accented speakers ACTUALLY said
        ├─ phoneme recognizer B: facebook/wav2vec2-lv-60-espeak-cv-ft
        │     leans toward dictionary pronunciations, but hears the flap T and non-English sounds
        ├─ Whisper (faster-whisper small.en) → the words you meant / a listener heard
        └─ CMUdict → expected American phones per word
              → weighted alignment of A and B (app/align.py) → combined verdict → tips (app/feedback.py)
```

Whisper alone can't find pronunciation mistakes, because it auto-corrects: "I sink so" comes back
as "I think so".

**Why two phoneme recognizers.** Recognizer B was trained on labels generated from the *text* of
each recording, so it partly guesses the dictionary pronunciation. A British speaker's "car"
(no R) comes out of it as `kɑːɹ`, which hides mild and moderate accents. Recognizer A was trained
on human transcriptions of accented speech, so it hears the dropped R, TH→D, V→F and so on, but it
is noisier. Each mistake is therefore graded:

- **confirmed:** both recognizers hear it, *or* it's a textbook accent pattern (TH→D, V→W, R→L,
  dropped R, final Z→S…), *or* the same mistake repeats in the recording. Noise is random; accent
  features are consistent.
- **possible:** a one-off that only recognizer A heard. It's shown with a "Possible issue" tag and
  barely affects the score.
- The flap T and non-English sounds (rolled R, retroflex T) come from recognizer B, since A has
  no symbols for them.

Benchmark (5 sentences × 11 synthetic voices; issues = confirmed non-American sounds):

| Voice | Score | Issues | Top features found |
|---|---|---|---|
| American | 96 | 4 | (noise) |
| British | 90 | 13 | dropped R ("bird" → "bud", "car" → "kah") |
| Indian English ×3 | 77–87 | 18–31 | hard T, TH→D/T, V→F, "bird" with the "book" vowel |
| Chinese-accented | 80 | 29 | hard T, final Z→S, "sit" → "seat" |
| Spanish/French/German/Japanese/Russian | 30–51 | 76–122 | many |

With only recognizer B (the original design), the Indian and British voices scored 94–99 and got
2–6 issues, which was no different from the American voice.

The scoring is designed not to penalize normal American speech:
- flap T/D (`water` → WAH-der, `sit in` → si-din), glottal T, the cot/caught merger
- reduced unstressed vowels, and all dictionary variants (`Wednesday` with -dee or -day)
- connected-speech merges (`please‿sit`, `visited‿the`)
- r-colored vowels heard as vowel + ɹ

| File | Role |
|---|---|
| `app/lexicon.py` | CMUdict lookup, suffix fallback, IPA, respelling, syllables, flap rule, numbers |
| `app/phones.py` | recognizer token → American phone mapping, substitution/insertion/deletion costs |
| `app/align.py` | Needleman–Wunsch alignment, best-variant rescoring, insertion attribution |
| `app/feedback.py` | per-word scores, tips knowledge base, recurring patterns |
| `app/tts.py` | natural American voice for Listen (Kokoro-82M), fed the coach's own American pronunciations |
| `app/segment.py` | finds each word in the recording (CTC forced alignment) for "play your version" |
| `app/recognizer.py` | audio decoding, wav2vec2 phoneme recognition, Whisper |
| `app/main.py` | FastAPI server and API |
| `static/` | web UI (typeset in EB Garamond, bundled in `static/fonts/` under the SIL Open Font License) |

Configuration via environment variables: `ACCENT_WHISPER_MODEL` (default `small.en`; `base.en`
is faster, `medium.en` more accurate), `ACCENT_PHONEME_MODEL`, `ACCENT_DETAIL_MODEL`, and `ACCENT_VOICE`
(default `af_heart`; other American voices include `af_bella`, `am_michael`, `am_fenrir`).

## Tests

```bash
uv run pytest
```

## Limitations

- The recognizers are good but not perfect. "Possible issue" items especially are hints, so trust
  the recurring-mistakes list most.
- The benchmark uses synthetic voices. Real accents vary more, so results on your own voice may differ.
- Scoring covers individual sounds. Intonation, rhythm, and word stress aren't scored yet.
- Words not in CMUdict (and not reachable via simple suffixes) are shown but not scored.
