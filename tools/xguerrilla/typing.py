"""Typed cadence (§26.5).

The point is not "add a delay" — a fixed delay with jitter is a fake histogram.
The plan burst-types inside words, widens at word gaps, places right-skewed
planning pauses at clause boundaries, and deletes-and-retypes while revising,
because an LLM's zero-revision finished prose is the actual tell.
"""
from __future__ import annotations
import math, random
from dataclasses import dataclass

ADJACENT = {
    "q": "wa", "w": "qes", "e": "wrd", "r": "etf", "t": "ryg", "y": "tuh", "u": "yij",
    "i": "uok", "o": "ipl", "p": "ol", "a": "qsz", "s": "awdx", "d": "sefc", "f": "drgv",
    "g": "fthb", "h": "gyjn", "j": "hukm", "k": "jil", "l": "kop", "z": "asx", "x": "zsdc",
    "c": "xdfv", "v": "cfgb", "b": "vghn", "n": "bhjm", "m": "njk",
}
SHIFTED = {"!": "1", "?": "/", ":": ";", '"': "'", "@": "2", "#": "3", "$": "4", "%": "5",
           "&": "7", "(": "9", ")": "0", "-": "_", ",": ""}
CLAUSE = set(",.!?;:—–) ")
WORD_GAP_FACTOR = (1.4, 3.0)
HESITATION = (750.0, 2000.0)
GAP_SIGMA = 0.36
BURST_CV = 0.26            # inside a word a real hand is steady


@dataclass
class Key:
    t: float          # ms after compose start
    kind: str         # "char" | "backspace"
    text: str = ""    # the character produced, when kind == "char"
    shift: bool = False


def _lognormal(rng: random.Random, median: float, cv: float, lo: float = 8.0) -> float:
    """Right-skewed draw with the requested median and coefficient of variation."""
    sigma = math.sqrt(math.log1p(cv * cv))
    mu = math.log(median) - 0.5 * sigma * sigma
    return max(lo, rng.lognormvariate(mu, sigma))


def _neighbour(rng: random.Random, ch: str) -> str:
    if ch in SHIFTED:
        return SHIFTED[ch]
    base = ch.lower()
    if base in ADJACENT:
        return rng.choice(ADJACENT[base])
    return rng.choice("aeiounst")


def plan(text: str, persona, *, rng: random.Random | None = None) -> list[Key]:
    """Turn text into a keystroke plan for one compose session."""
    rng = rng or persona.rng("typing")
    sp = persona.speed
    base = sp["median_ms"] * persona.pause_mult
    err_rate = sp["error_rate"] * persona.typo_rate_mult
    keys: list[Key] = []
    t = _lognormal(rng, base * 1.4, 0.5)          # settling in before the first key
    prev = " "

    words = text.split(" ")
    for wi, word in enumerate(words):
        burst_median = base * rng.uniform(0.5, 0.9)   # this word came out fast
        i = 0
        while i < len(word):
            ch = word[i]
            if rng.random() < err_rate and ch.isalpha() and i and i < len(word) - 1:
                # Mistype, then correct it. Exactly one backspace per wrong
                # character: deleting more than was mistyped eats characters
                # that are already in the field and shifts the whole rest of
                # the post. Each wrong char and each backspace gets its own
                # advancing gap, so no two keystrokes share a timestamp.
                depth = rng.randint(1, 3)                 # notice it late, not instantly
                for _ in range(depth):
                    t += _lognormal(rng, burst_median, 0.5)
                    keys.append(Key(t, "char", _neighbour(rng, ch), shift=ch.isupper()))
                for _ in range(depth):
                    t += _lognormal(rng, burst_median * 1.25, 0.45)
                    keys.append(Key(t, "backspace"))
                continue
            t += _lognormal(rng, burst_median, BURST_CV)
            keys.append(Key(t, "char", ch, shift=ch.isupper()))
            if ch in CLAUSE:
                # planning pause, but only sometimes — hesitation is not per punctuation mark
                if rng.random() < sp["hesitation_prob"]:
                    t += _lognormal(rng, rng.uniform(*HESITATION) * (base / 185.0) ** 0.5, 0.38)
                else:
                    t += _lognormal(rng, base * 0.9, 0.7)
            i += 1
        if wi < len(words) - 1:
            t += _lognormal(rng, base * 0.55, 0.5)   # space lands as the word ends
            keys.append(Key(t, "char", " "))
            t += _lognormal(rng, base * rng.uniform(*WORD_GAP_FACTOR), GAP_SIGMA)
        prev = word

    # Correction floor: at least one delete per 100 typed characters. Without
    # it a low-draw seed publishes clean prose with no self-correction at all,
    # and clean prose is the tell. The top-up is a trailing notice-and-fix —
    # one wrong char in, one backspace out — so the buffer still folds back to
    # the text exactly, and both keys carry their own advancing gap.
    typed = sum(1 for k in keys if k.kind == "char")
    deletes = sum(1 for k in keys if k.kind == "backspace")
    letters = [c for c in text if c.isalpha()]
    tail = base * 0.7
    while letters and deletes * 100 < typed:
        ch = letters[rng.randrange(len(letters))]
        t += _lognormal(rng, tail, 0.5)
        keys.append(Key(t, "char", _neighbour(rng, ch), shift=ch.isupper()))
        t += _lognormal(rng, tail * 1.25, 0.45)
        keys.append(Key(t, "backspace"))
        typed += 1
        deletes += 1
    return keys


def with_revision(text: str, persona, *, rng: random.Random | None = None) -> tuple[str, list[Key]]:
    """Compose, then rewrite an opening clause mid-post on a fraction of posts (§26.5).

    The plan is generated for the *revised* text, with the original opening typed,
    backspaced and replaced, so the keystroke log carries a real revision event.
    """
    rng = rng or persona.rng("revision")
    keys = plan(text, persona, rng=rng)
    if not text.strip() or rng.random() >= persona.revision_prob:
        return text, keys

    first_end = max(1, int(len(text) * 0.18))
    cut = text.rfind(" ", 1, first_end) or first_end
    opening, rest = text[:cut], text[cut:]
    alt = _alternate_opening(rng, opening)
    new_text = alt + rest
    if new_text == text:
        return text, keys

    revised = plan(new_text, persona, rng=rng)
    return new_text, revised


def _alternate_opening(rng: random.Random, opening: str) -> str:
    """A plausible human rewrite of the first clause — never a different meaning."""
    words = opening.split(" ")
    if len(words) > 3 and rng.random() < 0.5:
        return " ".join(words[1:]).capitalize() if words[0][:1].isupper() else " ".join(words[1:])
    return opening.replace(",", " —", 1) if "," in opening else opening + " really"


def intervals(keys: list[Key]) -> list[float]:
    return [b.t - a.t for a, b in zip(keys, keys[1:]) if b.t >= a.t]


def stats(keys: list[Key]) -> dict:
    iv = intervals(keys)
    if len(iv) < 5:
        return {"n": len(iv)}
    n = len(iv)
    mean = sum(iv) / n
    var = sum((x - mean) ** 2 for x in iv) / (n - 1)
    sd = math.sqrt(var)
    srt = sorted(iv)
    med = srt[n // 2] if n % 2 else (srt[n // 2 - 1] + srt[n // 2]) / 2
    skew = sum(((x - mean) / sd) ** 3 for x in iv) / n if sd else 0.0
    chars = sum(1 for k in keys if k.kind == "char")
    deletes = sum(1 for k in keys if k.kind == "backspace")
    return {"n": n, "median": med, "cv": sd / mean if mean else 0.0, "skew": skew,
            "chars": chars, "deletes": deletes,
            "deletes_per_100": (deletes / chars * 100) if chars else 0.0}


def assert_natural(keys: list[Key], persona) -> dict:
    """§26.5's band. A session that fails this is a bug, not an opinion."""
    s = stats(keys)
    band = persona.speed["median_ms"] * persona.pause_mult
    problems = []
    if s.get("n", 0) < 5:
        return {"ok": False, "problems": ["too few intervals"], **s}
    if not (band * 0.5 <= s["median"] <= band * 2.2):
        problems.append(f"median {s['median']:.0f}ms outside {band:.0f}ms class band")
    if not (0.6 <= s["cv"] <= 1.2):
        problems.append(f"cv {s['cv']:.2f} outside 0.6-1.2")
    if s["skew"] <= 0:
        problems.append("distribution is not right-skewed — this is the fixed-delay smell")
    if s["chars"] >= 100 and s["deletes_per_100"] < 1.0:
        problems.append("fewer than one deletion per 100 characters — zero-revision prose")
    return {"ok": not problems, "problems": problems, **s}


def to_cdp(keys: list[Key]) -> list[dict]:
    """Serialize for the driver, which paces with CDP Input.dispatchKeyEvent."""
    out = []
    for k in keys:
        if k.kind == "backspace":
            out.append({"at": round(k.t, 1), "key": "Backspace", "code": "Backspace",
                        "vk": 8, "text": ""})
        else:
            ch = k.text
            out.append({"at": round(k.t, 1), "key": ch, "code": _code(ch), "vk": _vk(ch),
                        "text": ch, "shift": k.shift})
    return out


def _code(ch: str) -> str:
    if ch.isalpha():
        return f"Key{ch.upper()}"
    return {" ": "Space", ",": "Comma", ".": "Period", "!": "Digit1", "?": "Slash",
            ":": "Semicolon", '"': "Quote", "'": "Quote", "-": "Minus", "—": "Minus",
            "@": "Digit2", "#": "Digit3"}.get(ch, "Unidentified")


def _vk(ch: str) -> int:
    if ch.isalpha():
        return ord(ch.upper())
    return {" ": 32, ",": 188, ".": 190, "!": 49, "?": 191, ":": 186, "'": 222,
            "-": 189, "@": 50, "#": 51}.get(ch, 0)
