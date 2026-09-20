"""
Input normalization for lexicon matching.

Closes bypass classes known from the C-kernel audit:
  1. Delimiter / spacing  — hyphens, dots, underscores, zero-width, letter-spacing
  2. Homoglyphs           — Cyrillic/Greek lookalikes of Latin letters

Applied once per evaluate() before any pattern scan.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Tuple

_HOMOGLYPHS = str.maketrans({
    "а": "a", "А": "a", "е": "e", "Е": "e", "о": "o", "О": "o",
    "р": "p", "Р": "p", "с": "c", "С": "c", "у": "y", "У": "y",
    "х": "x", "Х": "x", "і": "i", "І": "i", "ј": "j", "Ј": "j",
    "ѕ": "s", "Ѕ": "s", "һ": "h", "ԁ": "d", "ɡ": "g", "ԛ": "q",
    "ԝ": "w", "ѵ": "v", "Ѵ": "v", "ƅ": "b", "ӏ": "l", "ɴ": "n",
    "α": "a", "Α": "a", "β": "b", "Β": "b", "ε": "e", "Ε": "e",
    "η": "n", "Η": "h", "ι": "i", "Ι": "i", "κ": "k", "Κ": "k",
    "ν": "v", "Ν": "n", "ο": "o", "Ο": "o", "ρ": "p", "Ρ": "p",
    "τ": "t", "Τ": "t", "χ": "x", "Χ": "x", "γ": "y", "μ": "u",
    "ａ": "a", "ｂ": "b", "ｃ": "c", "ｄ": "d", "ｅ": "e",
    "ｆ": "f", "ｇ": "g", "ｈ": "h", "ｉ": "i", "ｊ": "j",
    "ｋ": "k", "ｌ": "l", "ｍ": "m", "ｎ": "n", "ｏ": "o",
    "ｐ": "p", "ｑ": "q", "ｒ": "r", "ｓ": "s", "ｔ": "t",
    "ｕ": "u", "ｖ": "v", "ｗ": "w", "ｘ": "x", "ｙ": "y", "ｚ": "z",
})

_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "2": "z", "3": "e", "4": "a",
    "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s", "!": "i", "|": "l",
})

_ZW_RE = re.compile(
    r"[\u200b\u200c\u200d\u2060\ufeff\u00ad\u200e\u200f\u202a-\u202e]"
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")


def normalize(text: str) -> Tuple[str, str, str]:
    """
    Returns (collapsed, folded, squeezed).

    collapsed : lowercased, homoglyph/leet folded, letter-spacing repaired
    folded    : alias of collapsed
    squeezed  : all non-alphanumeric removed
    """
    if not text:
        return "", "", ""

    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _ZW_RE.sub("", s)
    s = s.lower().translate(_HOMOGLYPHS).translate(_LEET_MAP)
    # Join hyphen/dot/underscore separated single chars: d-i-s-r-e-g-a-r-d → disregard
    s = re.sub(r"(?<![a-z0-9])(?:[a-z0-9][-._])+[a-z0-9](?![a-z0-9])",
               lambda m: re.sub(r"[-._]", "", m.group(0)), s)

    # Letter-spacing repair: "h o w   t o   h a r m" → "how to harm"
    # Multi-space marks original word boundaries after char-spacing mutators.
    if _MULTI_SPACE_RE.search(s):
        groups = _MULTI_SPACE_RE.split(s.strip())
        words = []
        for g in groups:
            parts = g.split()
            if not parts:
                continue
            if all(len(p) == 1 for p in parts):
                words.append("".join(parts))
            else:
                words.append("".join(parts) if all(len(p) == 1 for p in parts) else " ".join(parts))
        collapsed = " ".join(words)
    else:
        collapsed = " ".join(s.split())
        tokens = collapsed.split()
        if len(tokens) >= 4:
            singles = sum(1 for tok in tokens if len(tok) == 1)
            if singles >= len(tokens) * 0.5:
                # No multi-space clue: join all singles into one stream,
                # but also keep a space-joined singles form for word scan
                collapsed = "".join(tokens) if all(len(t) == 1 for t in tokens) else collapsed

    squeezed = _NON_ALNUM_RE.sub("", collapsed)
    return collapsed, collapsed, squeezed


def contains_pattern(pat: str, collapsed: str, squeezed: str) -> bool:
    """Match pattern against collapsed form or fully squeezed form.

    Short tokens (len <= 4) require word boundaries on collapsed so
    'harm' does not match 'harmlessly'. Also check squeezed substring
    for short stems when the stem is a full word in collapsed after
    letter-space repair.
    """
    if not pat:
        return False
    p = pat.lower()
    p_sq = _NON_ALNUM_RE.sub("", p)

    if len(p_sq) <= 4:
        # Word boundary only — never substring (skill≠kill, harmlessly≠harm)
        if re.search(r"(?<![a-z0-9])" + re.escape(p) + r"(?![a-z0-9])", collapsed):
            return True
        if re.search(r"(?<![a-z0-9])" + re.escape(p_sq) + r"(?![a-z0-9])", collapsed):
            return True
        return False

    if p in collapsed:
        return True
    if p_sq and p_sq in squeezed:
        return True
    return False
