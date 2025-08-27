# tavern-ordering-system/backend/app/nlp.py
"""
Basic Greek-capable classification module.

Strategy:
- Try to use spaCy Greek model (el_core_news_sm) if available to get lemmas/tokens.
- Otherwise fallback to simple substring matching on normalized lines.
- Return a list of dicts: [{"text": original_line, "category": "grill"|"kitchen"|"drinks"}, ...]
"""

from typing import List, Dict
import re

# Try to import spaCy Greek model if available
try:
    import spacy

    # Try to load the Greek small model; it may be installed via the setup script.
    try:
        nlp_model = spacy.load("el_core_news_sm")
    except Exception:
        # model not present
        nlp_model = None
except Exception:
    nlp_model = None

# Basic Greek keyword stems for grill vs kitchen/drinks
# These are purposely stem-ish (no final letters) to match variants.
GRILL_STEMS = [
    "μπριζολ",  # μπριζόλα, μπριζόλες
    "παϊδ",     # παϊδάκι/παϊδάκια
    "παιδ",     # greek accents variants
    "σχάρα",    # σχάρα / στη σχάρα
    "σουβλα",   # σουβλάκι / σουβλάκια
    "μπέικον",  # if exists
    "μπριζόλ",  # alternative accent spelling
    "παϊδ",     # repetition safe
    "μπριζο"    # fallback
]

KITCHEN_STEMS = [
    "φούρν",  # φούρνος / στο φούρνο
    "τηγαν",  # τηγανιτό / τηγανιστό
    "σαλἀτ" , # incorrect spelling placeholder — we'll rely mostly on substring matching below
]

DRINK_STEMS = [
    "μπύρ",  # μπύρα
    "ουζ",   # ούζο
    "κρασ",  # κρασί
    "ποτό",  # ποτό
    "τσίπ"   # τσίπουρο (stem)
]


def _normalize(text: str) -> str:
    """Lowercase, strip, remove punctuation (but keep Greek letters), collapse spaces."""
    t = text.strip().lower()
    # remove punctuation but keep letters/numbers/space
    t = re.sub(r"[^\w\sάέήίόύώϊϋΐΰΆΈΉΊΌΎΏΑ-Ωα-ω0-9]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _contains_stem(text: str, stems: List[str]) -> bool:
    for s in stems:
        if s in text:
            return True
    return False


def classify_order(order_text: str) -> List[Dict]:
    """
    Input: multi-line Greek order text (one dish per line)
    Output: list of {"text": line, "category": "grill"|"kitchen"|"drinks"}
    """

    results = []
    lines = [ln for ln in order_text.splitlines() if ln.strip()]
    for ln in lines:
        norm = _normalize(ln)

        # If we have spaCy, try to get lemmas to improve matching
        lemmas = ""
        if nlp_model:
            try:
                doc = nlp_model(norm)
                lemmas = " ".join([tok.lemma_ for tok in doc])
            except Exception:
                lemmas = norm
        else:
            lemmas = norm

        # Decide category
        if _contains_stem(lemmas, GRILL_STEMS):
            category = "grill"
        elif _contains_stem(lemmas, DRINK_STEMS):
            category = "drinks"
        else:
            # Default to kitchen for anything else (including oven dishes)
            # But also treat explicit oven stem as kitchen:
            if _contains_stem(lemmas, KITCHEN_STEMS) or "φούρνο" in lemmas or "φούρνος" in lemmas:
                category = "kitchen"
            else:
                category = "kitchen"

        results.append({"text": ln.strip(), "category": category})

    return results
