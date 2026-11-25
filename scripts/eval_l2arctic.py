"""Measure detection accuracy against expert annotations: the L2-ARCTIC Hindi speakers.

    uv run python scripts/eval_l2arctic.py run       # analyze the 4 x 150 annotated sentences (cached)
    uv run python scripts/eval_l2arctic.py report    # catch rate / false-alarm rate per feature
    uv run python scripts/eval_l2arctic.py report --examples th   # list misses and false alarms

Trained phoneticians marked every sound in 150 sentences per speaker as correct, substituted
("DH,D,s": DH said as D), deviated ("T,T*,s": a T with a foreign quality, e.g. unaspirated or
curled back), or deleted ("R,sil,d"). For each feature this reports:
  caught        share of annotated mistakes the app flagged       (higher is better)
  false alarms  share of correctly-said sounds the app flagged    (lower is better)

Data: data/l2arctic/<SPK>/{wav,annotation,transcript} for ASI, RRBI (male) and SVBI, TNI
(female), all native Hindi speakers. Licence: CC BY-NC 4.0 (non-commercial use only).
Caveat: phoneme recognizer A was trained on L2-ARCTIC, so its contribution looks better here
than it will on new speakers. The acoustic checks (R color, T aspiration) are not trained.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from features import FEATURES, phone_features  # noqa: E402

DATA = ROOT / "data" / "l2arctic"
CACHE = ROOT / "data" / "eval_l2arctic"
SPEAKERS = {"ASI": "male", "RRBI": "male", "SVBI": "female", "TNI": "female"}


def read_textgrid(path: Path) -> dict[str, list[tuple[float, float, str]]]:
    """Tiers of a long-format TextGrid: {tier name: [(start, end, text), ...]}."""
    tiers: dict[str, list[tuple[float, float, str]]] = {}
    current = None
    xmin = xmax = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if m := re.match(r'name = "(.*)"', line):
            current = m.group(1)
            tiers[current] = []
        elif m := re.match(r"xmin = ([\d.]+)", line):
            xmin = float(m.group(1))
        elif m := re.match(r"xmax = ([\d.]+)", line):
            xmax = float(m.group(1))
        elif (m := re.match(r'text = "(.*)"', line)) and current is not None:
            tiers[current].append((xmin, xmax, m.group(1)))
    return tiers


def annotated_words(path: Path) -> list[dict]:
    """[{word, phones: [{expected, heard, error}]}] from one annotation file.

    `expected` is the ARPAbet phone without stress; `error` is None (correct), "sub" (a
    different phone), "dev" (the same phone with a foreign quality) or "del"."""
    tiers = read_textgrid(path)
    words = [(s, e, t) for s, e, t in tiers.get("words", []) if t.strip()]
    out = [{"word": t, "phones": []} for _, _, t in words]
    for s, e, label in tiers.get("phones", []):
        label = re.sub(r"\s", "", label)
        if not label or label in {"sil", "sp", "spn"} or label.startswith("sil,"):
            continue  # silence, or an added sound (not scored here)
        parts = label.split(",")
        cpl = re.sub(r"\d", "", parts[0]).upper()
        if len(parts) >= 3:
            ppl, kind = parts[1], parts[2]
            error = "del" if kind == "d" else "dev" if ppl.rstrip("*") == cpl or ppl == "err" else "sub"
            heard = "" if kind == "d" else ppl
        else:
            error, heard = None, cpl
        mid = (s + e) / 2
        wi = next((k for k, (ws, we, _) in enumerate(words) if ws <= mid <= we), None)
        if wi is not None:
            out[wi]["phones"].append({"expected": cpl, "heard": heard, "error": error})
    return out


def run(args) -> None:
    from app import main, recognizer
    from app.lexicon import base

    CACHE.mkdir(parents=True, exist_ok=True)
    n, t0 = 0, time.time()
    for spk in SPEAKERS:
        for ann in sorted((DATA / spk / "annotation").glob("*.TextGrid")):
            out = CACHE / f"{spk}-{ann.stem}.json"
            if out.exists() and not args.fresh:
                continue
            text = (DATA / spk / "transcript" / f"{ann.stem}.txt").read_text(encoding="utf-8").strip()
            audio, _ = recognizer.load_audio((DATA / spk / "wav" / f"{ann.stem}.wav").read_bytes())
            result, measurements = main.score(audio, text, *main.recognize(audio))

            gold = annotated_words(ann)
            app_words = [w for w in result["words"]]
            rows = []
            # Pair words in order by spelling; within a word, pair phones when both sides
            # expect the same sounds (the app may have chosen another dictionary variant).
            gi = 0
            for w in app_words:
                while gi < len(gold) and gold[gi]["word"].lower() != w["word"].lower():
                    gi += 1
                if gi >= len(gold):
                    break
                g = gold[gi]
                gi += 1
                if not w.get("known") or "phones" not in w:
                    continue
                phones = w["arpabet"].split()
                views = [v for v in w["phones"] if v["expected"]]
                if len(views) != len(phones) or [base(p) for p in phones] != [p["expected"] for p in g["phones"]]:
                    continue
                for p, feat, v, gp in zip(phones, phone_features(phones), views, g["phones"]):
                    rows.append({"word": w["word"], "phone": base(p), "feature": feat,
                                 "gold_error": gp["error"], "gold_heard": gp["heard"],
                                 "app_status": v["status"], "app_heard": v["heard"]})
            out.write_text(json.dumps({"speaker": spk, "gender": SPEAKERS[spk], "utt": ann.stem, "text": text,
                                       "phones": rows, "measurements": measurements}, ensure_ascii=False),
                           encoding="utf-8")
            n += 1
            if n % 50 == 0:
                print(f"  {n} analyzed ({(time.time() - t0) / n:.1f} s each)", flush=True)
    print(f"{n} analyzed in {time.time() - t0:.0f} s")


def report(args) -> None:
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CACHE.glob("*.json"))]
    if not recs:
        print("Nothing analyzed yet: run `scripts/eval_l2arctic.py run` first.")
        return
    groups = ["all"] + list(SPEAKERS)
    # (feature, group) -> [caught, annotated errors, false alarms, annotated correct]
    c = defaultdict(lambda: [0, 0, 0, 0])
    paired = sum(len(r["phones"]) for r in recs)
    for r in recs:
        for p in r["phones"]:
            feat = p["feature"] or "other"
            flagged = p["app_status"] != "ok"
            for g in ("all", r["speaker"]):
                for f in (feat, "ALL"):
                    cell = c[(f, g)]
                    if p["gold_error"]:
                        cell[0] += flagged
                        cell[1] += 1
                    else:
                        cell[2] += flagged
                        cell[3] += 1
    print(f"{len(recs)} sentences, {paired} sounds paired with an expert verdict\n")
    print("caught = annotated mistakes the app flagged · false = correct sounds the app flagged\n")
    header = f"{'feature':<12}" + "".join(f"{g:>22}" for g in groups)
    print(header)
    for f in FEATURES + ["other", "ALL"]:
        cells = []
        for g in groups:
            k, n, fa, m = c.get((f, g), (0, 0, 0, 0))
            caught = f"{100 * k / n:3.0f}% of {n:<4}" if n else "   ·      "
            false = f"{100 * fa / m:3.0f}%" if m else "  ·"
            cells.append(f"{caught} {false:>5}")
        print(f"{f:<12}" + "".join(f"{x:>22}" for x in cells))

    if args.examples:
        misses, alarms = defaultdict(int), defaultdict(int)
        for r in recs:
            for p in r["phones"]:
                if p["feature"] != args.examples:
                    continue
                flagged = p["app_status"] != "ok"
                key = (p["phone"], p["gold_heard"] or "∅", p["app_heard"] or "∅")
                if p["gold_error"] and not flagged:
                    misses[key] += 1
                elif not p["gold_error"] and flagged:
                    alarms[key] += 1
        print(f"\n'{args.examples}' missed mistakes (expected, annotators heard, app heard): count")
        for k, v in sorted(misses.items(), key=lambda kv: -kv[1])[:15]:
            print(f"  {k}: {v}")
        print(f"\n'{args.examples}' false alarms (expected, annotators heard, app heard): count")
        for k, v in sorted(alarms.items(), key=lambda kv: -kv[1])[:15]:
            print(f"  {k}: {v}")


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fresh", action="store_true")
    p = sub.add_parser("report")
    p.add_argument("--examples", help="list misses and false alarms for one feature")
    args = ap.parse_args()
    run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    main_cli()
