"""Align the sounds that were heard against the sounds that were expected."""

from __future__ import annotations

from dataclasses import dataclass

from .lexicon import base, is_vowel
from .phones import Heard, deletion_cost, insertion_cost, is_vowel_unit, rhotic_pair_cost, substitution_cost


@dataclass
class Op:
    kind: str                 # "match" | "sub" | "del" | "ins"
    word: int                 # index of the word this op belongs to
    expected: str | None      # ARPAbet with stress, None for insertions
    heard: Heard | None       # None for deletions
    cost: float
    pos: int = -1             # index of the expected phone within its word
    confidence: str = "confirmed"  # "confirmed" (both recognizers agree) | "possible"

    @property
    def severity(self) -> str:
        if self.cost <= 0.15:
            return "ok"
        if self.cost < 0.6:
            return "accent"
        return "error"


def align(expected: list[tuple[int, str]], heard: list[Heard], hard_t: bool = True) -> list[Op]:
    """Weighted Needleman-Wunsch alignment. `expected` is [(word_index, phone), ...].

    `hard_t`: penalize a hard T where Americans flap it. Only meaningful for a recognizer
    that distinguishes the flap from T."""
    n, m = len(expected), len(heard)
    sub = [(*_sub_context(expected, i), hard_t) for i in range(n)]
    pos = [sum(1 for w, _ in expected[:i] if w == expected[i][0]) for i in range(n)]
    dele = [_del_context(expected, i) for i in range(n)]
    INF = float("inf")
    dp = [[INF] * (m + 1) for _ in range(n + 1)]
    back: list[list[str]] = [[""] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            cur = dp[i][j]
            if cur == INF:
                continue
            if i < n and j < m:
                c = cur + substitution_cost(expected[i][1], heard[j].unit, *sub[i])
                if c < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1], back[i + 1][j + 1] = c, "S"
            if i < n and j + 1 < m:
                pc = rhotic_pair_cost(expected[i][1], heard[j].unit, heard[j + 1].unit)
                if pc is not None and cur + pc < dp[i + 1][j + 2]:
                    dp[i + 1][j + 2], back[i + 1][j + 2] = cur + pc, "P"
            if i < n:
                c = cur + deletion_cost(expected[i][1], *dele[i])
                if c < dp[i + 1][j]:
                    dp[i + 1][j], back[i + 1][j] = c, "D"
            if j < m:
                c = cur + insertion_cost(heard[j].unit)
                if c < dp[i][j + 1]:
                    dp[i][j + 1], back[i][j + 1] = c, "I"

    ops: list[Op] = []
    i, j = n, m
    while i > 0 or j > 0:
        move = back[i][j]
        if move == "S":
            i, j = i - 1, j - 1
            cost = substitution_cost(expected[i][1], heard[j].unit, *sub[i])
            kind = "match" if cost <= 0.15 else "sub"
            ops.append(Op(kind, expected[i][0], expected[i][1], heard[j], cost, pos[i]))
        elif move == "P":
            i, j = i - 1, j - 2
            cost = rhotic_pair_cost(expected[i][1], heard[j].unit, heard[j + 1].unit)
            ops.append(Op("match" if cost <= 0.15 else "sub", expected[i][0], expected[i][1],
                          _join(heard[j], heard[j + 1]), cost, pos[i]))
        elif move == "D":
            i -= 1
            cost = deletion_cost(expected[i][1], *dele[i])
            ops.append(Op("del", expected[i][0], expected[i][1], None, cost, pos[i]))
        else:
            j -= 1
            ops.append(Op("ins", -1, None, heard[j], insertion_cost(heard[j].unit)))
    ops.reverse()
    _attribute_insertions(ops, expected)
    return ops


def _sub_context(expected: list[tuple[int, str]], i: int) -> tuple[str | None, bool]:
    """(next phone within the same word, whether a flap is natural here)."""
    w, ph = expected[i]
    nxt = expected[i + 1] if i + 1 < len(expected) else None
    prv = expected[i - 1] if i > 0 else None
    next_in_word = nxt[1] if nxt and nxt[0] == w else None
    flap_ok = (
        base(ph) == "T" and prv is not None and nxt is not None
        and (is_vowel(prv[1]) or base(prv[1]) == "R") and is_vowel(nxt[1])
        and (nxt[0] != w or nxt[1].endswith("0"))
    )
    return next_in_word, flap_ok


def _del_context(expected: list[tuple[int, str]], i: int) -> tuple[str | None, str | None, bool]:
    """(previous phone, next phone, whether this phone ends its word)."""
    prv = expected[i - 1][1] if i > 0 else None
    nxt = expected[i + 1] if i + 1 < len(expected) else None
    return prv, nxt[1] if nxt else None, nxt is None or nxt[0] != expected[i][0]


def best_variant(word: int, variants: list[list[str]], ops: list[Op], before: str | None,
                 hard_t: bool = True) -> tuple[list[str], list[Op]] | None:
    """Re-align the sounds heard for one word against each dictionary variant of it and
    return the closest (variant, ops), e.g. 'Wednesday' as -dee or -day."""
    span = [o.heard for o in ops if o.word == word and o.heard is not None]
    current = sum(o.cost for o in ops if o.word == word)
    best = None
    for v in variants:
        exp = ([(-1, before)] if before else []) + [(word, p) for p in v]
        local = [o for o in align(exp, span, hard_t) if o.word == word or o.kind == "ins"]
        for o in local:
            o.word = word
        cost = sum(o.cost for o in local)
        if cost < current - 1e-9:
            current, best = cost, (v, local)
    return best


def combine(primary: list[Op], detail: list[Op]) -> None:
    """Merge the verdicts of two recognizers, in place on `primary`.

    `primary` comes from a recognizer trained on what accented speakers actually said; it
    catches real substitutions and dropped sounds but is noisier. `detail` comes from a
    recognizer that leans toward dictionary pronunciations: when it also hears a mistake, the
    mistake is confirmed; when it doesn't, the mistake is only "possible". The detail
    recognizer alone is trusted for sounds the primary one can't represent: the American
    flap T and non-English sounds (rolled R, retroflex T...)."""
    by_pos = {(o.word, o.pos): o for o in detail if o.expected is not None}
    detail_extra = {o.word for o in detail if o.kind == "ins" and o.severity != "ok"}
    for o in primary:
        if o.expected is None:
            if o.severity != "ok" and o.word not in detail_extra:
                o.confidence = "possible"
            continue
        d = by_pos.get((o.word, o.pos))
        if o.severity != "ok":
            if d is None or d.severity == "ok":
                o.confidence = "possible"
        elif d is not None and d.severity != "ok" and d.heard is not None and (
            d.heard.foreign or d.heard.unit == base(d.expected)  # foreign sound / hard T
        ):
            o.kind, o.heard, o.cost = d.kind, d.heard, d.cost


def _join(a: Heard, b: Heard) -> Heard:
    unit = "ER" if a.unit in {"ER", "AH"} else a.unit
    return Heard(unit, a.ipa + b.ipa, a.start, b.end)


def _attribute_insertions(ops: list[Op], expected: list[tuple[int, str]]) -> None:
    """Give each inserted sound to a word: the surrounding word, or at a word boundary the
    previous word (an extra vowel after a final consonant), except for a vowel before an
    S-cluster, which belongs to the next word ("eschool")."""
    for k, op in enumerate(ops):
        if op.kind != "ins":
            continue
        prev = next((o for o in reversed(ops[:k]) if o.kind != "ins"), None)
        nxt_i = next((i for i in range(k + 1, len(ops)) if ops[i].kind != "ins"), None)
        nxt = ops[nxt_i] if nxt_i is not None else None
        if prev is None:
            op.word = nxt.word if nxt else 0
        elif nxt is None or prev.word == nxt.word:
            op.word = prev.word
        else:
            after = [o for o in ops[nxt_i:] if o.word == nxt.word and o.expected]
            s_cluster = (
                len(after) >= 2 and base(after[0].expected) == "S" and not is_vowel(after[1].expected)
            )
            op.word = nxt.word if (s_cluster and is_vowel_unit(op.heard.unit)) else prev.word
        if op.word < 0:
            op.word = 0
