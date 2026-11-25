"""Evaluate detection on public speech collections, broken down by native language and gender.

    uv run python scripts/eval_corpus.py run --per-speaker 4     # analyze a sample (cached)
    uv run python scripts/eval_corpus.py report                  # tables from the cache
    uv run python scripts/eval_corpus.py report --by gender

Collections (downloaded into data/, which git ignores):
  data/svarah/data/*.parquet     Svarah (AI4Bharat, CC BY 4.0): Indian speakers of 19 native
                                 languages, with gender / age / state per recording
  data/cmu_arctic/<speaker>/     CMU ARCTIC: American English speakers bdl, slt, clb, rms
                                 (the false-alarm reference), and ksp, aup, gka, slp, axb (Indian English)

Each analyzed recording is cached in data/eval_cache/<collection>/<id>.json with its labels,
the per-phone verdicts and the acoustic measurements. `run` skips cached recordings; delete the
cache (or pass --fresh) after changing the scoring code.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval import FEATURES, phone_features  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "eval_cache"
CMU_SPEAKERS = {
    "bdl": ("American English", "male"), "rms": ("American English", "male"),
    "slt": ("American English", "female"), "clb": ("American English", "female"),
    # Indian English speakers (festvox.org/cmu_arctic lists them as "US English (Indian)");
    # their native languages aren't published.
    "ksp": ("Indian English (CMU)", "male"), "aup": ("Indian English (CMU)", "male"),
    "gka": ("Indian English (CMU)", "male"), "slp": ("Indian English (CMU)", "male"),
    "axb": ("Indian English (CMU)", "female"),
}


# ---------- Collections: each yields (id, audio bytes or array, text, labels) ----------

def svarah_items(per_speaker: int, seed: int):
    import pyarrow.parquet as pq

    rows = []
    for f in sorted((DATA / "svarah" / "data").glob("*.parquet")):
        t = pq.read_table(f, columns=["text", "duration", "gender", "age-group", "primary_language",
                                      "native_place_state", "native_place_district",
                                      "highest_qualification", "job_category"])
        for i, r in enumerate(t.to_pylist()):
            rows.append((f, i, r))
    # Svarah has no speaker id: recordings sharing every speaker attribute come from one speaker.
    by_speaker = defaultdict(list)
    for f, i, r in rows:
        if 2.0 <= (r["duration"] or 0) <= 15.0 and len(r["text"].split()) >= 4:
            key = tuple(r[k] for k in ["gender", "age-group", "primary_language", "native_place_state",
                                       "native_place_district", "highest_qualification", "job_category"])
            by_speaker[key].append((f, i, r))
    rng = random.Random(seed)
    chosen = []
    for key, items in sorted(by_speaker.items()):
        rng.shuffle(items)
        chosen += [(key, it) for it in items[:per_speaker]]
    tables: dict[Path, object] = {}
    for key, (f, i, r) in chosen:
        if f not in tables:
            tables[f] = pq.read_table(f, columns=["audio_filepath"])
        audio = tables[f].slice(i, 1).to_pylist()[0]["audio_filepath"]
        speaker = hashlib.sha1(repr(key).encode()).hexdigest()[:8]
        yield (f"{f.stem}-{i}", audio["bytes"], r["text"],
               {"collection": "svarah", "speaker": speaker, "language": r["primary_language"] or "unknown",
                "gender": (r["gender"] or "unknown").lower()})


def cmu_items(per_speaker: int, seed: int):
    rng = random.Random(seed)
    for spk, (lang, gender) in CMU_SPEAKERS.items():
        d = DATA / "cmu_arctic" / spk
        prompts = d / "etc" / "txt.done.data"
        if not prompts.exists():
            continue
        lines = []
        for line in prompts.read_text(encoding="utf-8").splitlines():
            # ( arctic_a0001 "Author of the danger trail, Philip Steels, etc." )
            line = line.strip().strip("()").strip()
            if " " in line:
                utt, text = line.split(" ", 1)
                lines.append((utt, text.strip().strip('"')))
        rng.shuffle(lines)
        for utt, text in lines[:per_speaker]:
            yield (f"{spk}-{utt}", (d / "wav" / f"{utt}.wav").read_bytes(), text,
                   {"collection": "cmu_arctic", "speaker": spk, "language": lang, "gender": gender})


COLLECTIONS = {"svarah": svarah_items, "cmu_arctic": cmu_items}


# ---------- Run ----------

def run(args) -> None:
    from app import main, recognizer
    from app.lexicon import tokenize

    for name in args.collections:
        out_dir = CACHE / name
        out_dir.mkdir(parents=True, exist_ok=True)
        done = errors = 0
        t0 = time.time()
        for item_id, data, text, labels in COLLECTIONS[name](args.per_speaker, args.seed):
            out = out_dir / f"{item_id}.json"
            if out.exists() and not args.fresh:
                continue
            try:
                audio, _ = recognizer.load_audio(data)
                if not tokenize(text) or len(audio) < recognizer.SAMPLE_RATE * 0.5:
                    continue
                result, measurements = main.score(audio, text, *main.recognize(audio))
            except Exception as e:  # one bad file shouldn't stop a long run
                errors += 1
                print(f"  {item_id}: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            out.write_text(json.dumps({
                "id": item_id, "text": text, "labels": labels, "measurements": measurements,
                "phones": _phone_verdicts(result),
            }, ensure_ascii=False), encoding="utf-8")
            done += 1
            if done % 25 == 0:
                print(f"  {name}: {done} analyzed ({(time.time() - t0) / done:.1f} s each)", flush=True)
        print(f"{name}: {done} analyzed, {errors} errors, {time.time() - t0:.0f} s")


def _phone_verdicts(result: dict) -> list[dict]:
    """Per tracked phone: word, feature, expected/heard, status."""
    out = []
    for w in result["words"]:
        if not w.get("known") or "phones" not in w:
            continue
        phones = w["arpabet"].split()
        views = [v for v in w["phones"] if v["expected"]]
        if len(views) != len(phones):
            continue
        for feat, v in zip(phone_features(phones), views):
            if feat:
                out.append({"word": w["word"], "feature": feat, "expected": v["expected"],
                            "heard": v["heard"], "status": v["status"]})
    return out


# ---------- Report ----------

def report(args) -> None:
    recs = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CACHE.glob("*/*.json"))]
    if not recs:
        print("Nothing analyzed yet: run `scripts/eval_corpus.py run` first.")
        return
    key = args.by
    groups = sorted({r["labels"][key] for r in recs}, key=lambda g: (g != "American English", g))
    speakers = defaultdict(set)
    for r in recs:
        speakers[r["labels"][key]].add(r["labels"]["speaker"])
    groups = [g for g in groups if len(speakers[g]) >= args.min_speakers]

    flagged = defaultdict(lambda: [0, 0])
    values = defaultdict(list)
    for r in recs:
        g = r["labels"][key]
        for p in r["phones"]:
            flagged[(p["feature"], g)][0] += p["status"] != "ok"
            flagged[(p["feature"], g)][1] += 1
        for m in r["measurements"]:
            values[(m["kind"], g)].append(m["value"])

    print(f"{len(recs)} recordings, {sum(len(s) for s in speakers.values())} speakers; "
          f"groups with at least {args.min_speakers} speaker(s)\n")
    print("Share of target sounds flagged (American English = false alarms; Indian groups = detections)\n")
    print(f"{'group':<28}{'spk':>4}{'rec':>5}" + "".join(f"{f:>12}" for f in FEATURES))
    for g in groups:
        n_rec = sum(1 for r in recs if r["labels"][key] == g)
        cells = []
        for f in FEATURES:
            k, n = flagged.get((f, g), (0, 0))
            cells.append(f"{100 * k / n:>11.0f}%" if n >= 5 else f"{'·':>12}")
        print(f"{g[:27]:<28}{len(speakers[g]):>4}{n_rec:>5}" + "".join(cells))

    print("\nAcoustic measurements: median [10th-90th percentile]")
    for kind in sorted({k for k, _ in values}):
        print(f"  {kind}")
        for g in groups:
            v = sorted(values.get((kind, g), []))
            if len(v) >= 5:
                q = lambda p: v[min(len(v) - 1, int(p * len(v)))]  # noqa: E731
                print(f"    {g[:30]:<32}{statistics.median(v):>8.2f}  [{q(.1):.2f} - {q(.9):.2f}]  n={len(v)}")


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--collections", nargs="+", default=["cmu_arctic", "svarah"], choices=list(COLLECTIONS))
    r.add_argument("--per-speaker", type=int, default=4)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--fresh", action="store_true", help="re-analyze cached recordings")
    p = sub.add_parser("report")
    p.add_argument("--by", default="language", choices=["language", "gender", "collection", "speaker"])
    p.add_argument("--min-speakers", type=int, default=1)
    args = ap.parse_args()
    run(args) if args.cmd == "run" else report(args)


if __name__ == "__main__":
    main_cli()
