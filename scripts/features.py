"""Which accent feature each expected sound belongs to, shared by the evaluation scripts
(scripts/eval_corpus.py and scripts/eval_l2arctic.py)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.acoustics import aspiration_positions  # noqa: E402
from app.lexicon import american_surface, base, is_vowel, stress  # noqa: E402

FEATURES = ["aspiration", "th", "vw", "dark_l", "r", "ey_ow", "ae", "aa", "ah", "ih_iy", "uh_uw", "z", "flap"]


def phone_features(phones: list[str]) -> list[str | None]:
    """The feature each phone of one word belongs to (None if it isn't a tracked feature)."""
    surface = american_surface(phones)
    asp = set(aspiration_positions([(0, p) for p in phones], stops=("P", "T", "K")))
    out: list[str | None] = []
    for i, p in enumerate(phones):
        b, nxt = base(p), phones[i + 1] if i + 1 < len(phones) else None
        if surface[i] == "DX":
            f = "flap"
        elif i in asp:
            f = "aspiration"
        elif b in {"TH", "DH"}:
            f = "th"
        elif b in {"V", "W"}:
            f = "vw"
        elif b == "L" and (nxt is None or not is_vowel(nxt)) and i > 0:
            f = "dark_l"
        elif b in {"R", "ER"}:
            f = "r"
        elif b in {"EY", "OW"}:
            f = "ey_ow"
        elif b == "AE":
            f = "ae"
        elif b == "AA":
            f = "aa"
        elif b == "AH" and stress(p) == 1:
            f = "ah"
        elif b in {"IH", "IY"} and stress(p) >= 1:
            f = "ih_iy"
        elif b in {"UH", "UW"}:
            f = "uh_uw"
        elif b == "Z" and nxt is None:
            f = "z"
        else:
            f = None
        out.append(f)
    return out
