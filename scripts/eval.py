"""Measure how well each accent feature is detected, on the labelled test-set recordings.

    uv run python scripts/eval.py             # re-analyze every recording with the current code
    uv run python scripts/eval.py --saved     # use the results saved at recording time (fast)
    uv run python scripts/eval.py --feature dark_l   # one feature, with every flagged word listed

For each feature and each label (speaker / style) it prints how many target sounds were flagged.
What "good" looks like:
  friend / natural  (American speech)      flagged rarely: under 5%
  me / natural      (Indian English)        flagged often, where the accent really has the feature
  me / american     (best American attempt) somewhere in between, and falling as you improve
It also prints the spread of each acoustic measurement per label, for setting thresholds.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
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


def load(saved: bool) -> list[dict]:
    records = []
    for f in sorted((ROOT / "recordings").glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        label = rec.get("label")
        if not label or not label.get("speaker"):
            continue
        if not saved:
            from app import main, recognizer

            audio, _ = recognizer.load_audio(f.with_suffix(".audio").read_bytes())
            rec["result"], rec["measurements"] = main.score(audio, rec["target"], *main.recognize(audio))
        rec["_file"] = f.name
        records.append(rec)
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", action="store_true", help="use saved results instead of re-analyzing")
    ap.add_argument("--feature", help="list every target sound of this feature")
    args = ap.parse_args()

    records = load(args.saved)
    if not records:
        print("No labelled recordings yet. Record some in the Test set tab.")
        return

    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])  # (feature, label) -> [flagged, total]
    detail: list[tuple[str, str, str, str, str]] = []
    labels = sorted({f"{r['label']['speaker']}/{r['label']['style']}" for r in records})
    for rec in records:
        lab = f"{rec['label']['speaker']}/{rec['label']['style']}"
        for w in rec["result"]["words"]:
            if not w.get("known") or "phones" not in w:
                continue
            phones = w["arpabet"].split()
            views = [v for v in w["phones"] if v["expected"]]  # drop inserted sounds
            if len(views) != len(phones):
                continue
            for p, feat, v in zip(phones, phone_features(phones), views):
                if feat is None:
                    continue
                flagged = v["status"] != "ok"
                counts[(feat, lab)][0] += flagged
                counts[(feat, lab)][1] += 1
                detail.append((feat, lab, w["word"], f"{v['expected']}→{v['heard'] or '∅'}", v["status"]))

    print(f"{len(records)} labelled recordings\n")
    print("Flagged target sounds per feature")
    print(f"{'feature':<12}" + "".join(f"{lab:>20}" for lab in labels))
    for feat in FEATURES:
        cells = []
        for lab in labels:
            flagged, total = counts.get((feat, lab), (0, 0))
            cells.append(f"{flagged:>4}/{total:<4}{(100 * flagged / total if total else 0):>4.0f}%    " if total else f"{'-':>20}")
        print(f"{feat:<12}" + "".join(f"{c:>20}" for c in cells))

    print("\nAcoustic measurements per label (median [min-max], n)")
    values: dict[tuple[str, str], list[float]] = defaultdict(list)
    for rec in records:
        lab = f"{rec['label']['speaker']}/{rec['label']['style']}"
        for m in rec.get("measurements") or []:
            values[(m["kind"], lab)].append(m["value"])
    for kind in sorted({k for k, _ in values}):
        for lab in labels:
            v = values.get((kind, lab))
            if v:
                print(f"  {kind:<10} {lab:<18} {statistics.median(v):>7.2f} [{min(v):.2f}-{max(v):.2f}]  n={len(v)}")

    if args.feature:
        print(f"\nEvery '{args.feature}' target sound")
        for feat, lab, word, sounds, status in detail:
            if feat == args.feature:
                print(f"  {lab:<18} {word:<14} {sounds:<10} {status}")


if __name__ == "__main__":
    main()
