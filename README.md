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
The first start downloads the speech models (~1.7 GB). After that everything runs offline.

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

## How it works

```
mic → browser MediaRecorder → /api/analyze
        ├─ ffmpeg → 16 kHz mono, trim silence
        ├─ wav2vec2 phoneme recognizer (facebook/wav2vec2-lv-60-espeak-cv-ft)
        │     → the IPA sounds you actually made, with timestamps
        ├─ Whisper (faster-whisper small.en) → the words you meant / a listener heard
        └─ CMUdict → expected American phones per word
              → weighted alignment (app/align.py) → per-sound errors → tips (app/feedback.py)
```

Whisper alone can't find pronunciation mistakes, because it auto-corrects: "I sink so" comes back
as "I think so". The phoneme recognizer reports the raw sounds, including non-English ones like a
trilled `r`, retroflex `ʈ`, or `ʋ`. These are mapped to specific accent tips.

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
| `app/recognizer.py` | audio decoding, wav2vec2 phoneme recognition, Whisper |
| `app/main.py` | FastAPI server and API |
| `static/` | web UI |

Configuration via environment variables: `ACCENT_WHISPER_MODEL` (default `small.en`; `base.en`
is faster, `medium.en` more accurate) and `ACCENT_PHONEME_MODEL`.

## Tests

```bash
uv run pytest
```

## Limitations

- The phoneme recognizer is good but not perfect. Treat a single flagged sound as a hint, and
  trust patterns that repeat.
- Scoring covers individual sounds. Intonation, rhythm, and word stress aren't scored yet.
- Words not in CMUdict (and not reachable via simple suffixes) are shown but not scored.
