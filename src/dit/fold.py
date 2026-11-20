"""Matching-only folding: invisible characters and lookalike letters must not hide a word from a gate."""

from __future__ import annotations

import re
import unicodedata

# Letters from other scripts that look like Latin ones. Folded only inside a word that
# already mixes in Latin letters, so genuine Cyrillic or Greek text is left alone.
_LOOKALIKES = {
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0445": "x",
    "\u0443": "y", "\u0456": "i", "\u0458": "j", "\u0455": "s", "\u04bb": "h",
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K", "\u041c": "M", "\u041d": "H",
    "\u041e": "O", "\u0420": "P", "\u0421": "C", "\u0422": "T", "\u0425": "X",
    "\u03b1": "a", "\u03bf": "o", "\u03bd": "v", "\u03c1": "p",
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u0397": "H", "\u0399": "I", "\u039a": "K",
    "\u039c": "M", "\u039d": "N", "\u039f": "O", "\u03a1": "P", "\u03a4": "T", "\u03a7": "X",
    "\u03a5": "Y", "\u0396": "Z",
}
_WORD = re.compile(r"\w+", re.UNICODE)


def fold_for_matching(text: str) -> str:
    """Drop invisible format characters and fold lookalike letters inside mixed-script words.

    The gates match fixed English words letter for letter, so a zero-width character
    or one Cyrillic lookalike inside a word hid it from them. Format characters
    (zero-width space and joiners, bidi marks, soft hyphen) carry no meaning in
    running text and are removed. A lookalike is replaced only when its word also
    holds a Latin letter, so ordinary Cyrillic or Greek words are untouched. A word
    made only of lookalikes (a lone Greek capital iota, say) is not folded.
    """
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")

    def fix(match: "re.Match[str]") -> str:
        word = match.group(0)
        if not any("a" <= ch.lower() <= "z" for ch in word):
            return word
        return "".join(_LOOKALIKES.get(ch, ch) for ch in word)

    return _WORD.sub(fix, text)
