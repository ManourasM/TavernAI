# backend/app/nlp.py
"""
Basic Greek-capable classification module.

Features:
- Accent/diacritics-insensitive normalization.
- Optional spaCy Greek model (el_core_news_sm) used if installed.
- Optional menu.json support (backend/data/menu.json) to add explicit menu items and categories.
- Module-level sets for grill/drink/kitchen targets (no accidental 'global' misuse).
- classify_order(order_text) -> List[{"text": line, "category": ...}]

Notes:
- menu.json may be either:
  1) a list of entries (strings or objects {name, category}) -- legacy behavior, or
  2) an object mapping category names (e.g. "Salads", "From the grill") to arrays of item objects
     (each object may include "id", "name", "price", "category").
- This module builds MENU_ITEMS (normalized name -> {id, name, price, category}) when menu.json is readable.
"""

from typing import List, Dict
import re
import os
import json
import unicodedata

# Try to import spaCy Greek model if available
try:
    import spacy
    try:
        nlp_model = spacy.load("el_core_news_sm")
    except Exception:
        nlp_model = None
except Exception:
    nlp_model = None

# Base stem lists (kept short and intentionally partial, you can expand)
GRILL_STEMS = [
    "μπριζολ", "παϊδ", "παϊδά", "μπριζόλ", "μπριζο", "μπιφτεκ", "μπιφτέκ", "λουκαν", "χοιριν",
    "μπουτι", "σνιτσελ", "σουβλα", "παϊδάκ", "μπεικον"
]

KITCHEN_STEMS = [
    "φούρν", "τηγαν", "ραγού", "σουπα", "σάλτ", "μπεσαμ", "γκρατεν", "ομελετ", "παστ",
]

DRINK_STEMS = [
    "μπύρ", "μπυρ", "ουζ", "κρασ", "ποτο", "τσιπουρ", "τσίπουρ", "αναψυκ",
    "νερ", "χυμ"
]

# Utilities
def _strip_accents(s: str) -> str:
    """Remove combining marks (accents/diacritics) from unicode string."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))

def _normalize_text_basic(s: str) -> str:
    """
    Lowercase, strip accents, remove punctuation (keep letters/numbers/space),
    collapse whitespace.
    """
    if not s:
        return ""
    s2 = str(s).strip().lower()
    s2 = _strip_accents(s2)
    # Keep letters/numbers/space by checking each char's categories
    kept_chars = []
    for ch in s2:
        # isalnum covers letters + digits in many scripts; isspace covers spaces/newlines/tabs
        if ch.isalnum() or ch.isspace():
            kept_chars.append(ch)
        # else drop punctuation
    s3 = "".join(kept_chars)
    s3 = re.sub(r"\s+", " ", s3).strip()
    return s3

# Build normalized sets for fast substring checks
def _norm_list_to_set(lst):
    s = set()
    for item in lst:
        n = _normalize_text_basic(item)
        if n:
            s.add(n)
    return s

GRILL_SET = _norm_list_to_set(GRILL_STEMS)
KITCHEN_SET = _norm_list_to_set(KITCHEN_STEMS)
DRINK_SET = _norm_list_to_set(DRINK_STEMS)

# MENU_ITEMS: normalized name -> { id, name, price, category }
MENU_ITEMS = {}

# Optional: try to load backend/data/menu.json to extend sets
try:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/app -> backend
    menu_path = os.path.join(BASE_DIR, "data", "menu.json")
    if os.path.exists(menu_path):
        try:
            with open(menu_path, "r", encoding="utf-8") as f:
                menu_j = json.load(f)

            def _categorize_raw(cat_raw):
                """Return one of 'grill', 'drinks', or None based on a raw category string."""
                if not cat_raw:
                    return None
                s = _normalize_text_basic(str(cat_raw))
                # heuristics: look for substrings that indicate drinks or grill
                if "grill" in s or "γρίλ" in s or "ψή" in s or "ψητ" in s or "gril" in s or "σχάρ" in s or "grill" in s:
                    return "grill"
                if "drink" in s or "drinks" in s or "beer" in s or "μπυρ" in s or "κρασ" in s or \
                   "wine" in s or "wines" in s or "spirits" in s or "spirit" in s or "beers" in s or \
                   "soft" in s or "αναψυκ" in s or "ποτο" in s or "drinks" in s or "συ" in s:
                    return "drinks"
                # check greek tokens
                if "ψητ" in s or "σχάρα" in s or "σχαρ" in s or "ψη" in s:
                    return "grill"
                if "κρασι" in s or "μπυρα" in s or "ουζο" in s or "ποτο" in s or "αναψυκ" in s:
                    return "drinks"
                return None

            # menu_j may be either an iterable list or a dict mapping category->list
            if isinstance(menu_j, dict):
                # Expected: { "Salads": [ {name, price, id, category?}, ... ], "Beers": [...], ... }
                for top_cat, items in menu_j.items():
                    if not isinstance(items, (list, tuple)):
                        continue
                    for entry in items:
                        if isinstance(entry, str):
                            name = entry
                            entry_cat = None
                            entry_id = None
                            entry_price = None
                        elif isinstance(entry, dict):
                            name = entry.get("name") or entry.get("title") or ""
                            entry_id = entry.get("id")
                            entry_price = entry.get("price")
                            # prefer explicit category on the entry, otherwise use the top-level key
                            entry_cat = entry.get("category") or top_cat
                        else:
                            continue

                        nn = _normalize_text_basic(name)
                        if not nn:
                            continue

                        # Decide category decision: prefer explicit mapping (if it maps clearly)
                        cat_guess = None
                        if entry_cat:
                            cat_guess = _categorize_raw(entry_cat)
                        if not cat_guess:
                            # fallback: try to detect from top_cat name
                            cat_guess = _categorize_raw(top_cat)

                        # store in MENU_ITEMS for potential use elsewhere (id/price)
                        MENU_ITEMS[nn] = {
                            "id": entry_id,
                            "name": name,
                            "price": entry_price,
                            "category": cat_guess or None
                        }

                        # add normalized name to appropriate stem-set for classification
                        if cat_guess == "grill":
                            GRILL_SET.add(nn)
                        elif cat_guess == "drinks":
                            DRINK_SET.add(nn)
                        else:
                            KITCHEN_SET.add(nn)

            else:
                # legacy behavior: menu_j is an iterable list of strings or objects
                for entry in menu_j:
                    if isinstance(entry, str):
                        name = entry
                        cat = None
                        entry_id = None
                        entry_price = None
                    elif isinstance(entry, dict):
                        name = entry.get("name") or entry.get("title") or ""
                        cat = entry.get("category")
                        entry_id = entry.get("id")
                        entry_price = entry.get("price")
                    else:
                        continue
                    nn = _normalize_text_basic(name)
                    if not nn:
                        continue

                    MENU_ITEMS[nn] = {
                        "id": entry_id,
                        "name": name,
                        "price": entry_price,
                        "category": (str(cat).lower() if cat else None)
                    }

                    if cat:
                        cat_l = str(cat).lower()
                        if cat_l == "grill":
                            GRILL_SET.add(nn)
                        elif cat_l in ("drinks", "drink"):
                            DRINK_SET.add(nn)
                        else:
                            KITCHEN_SET.add(nn)
                    else:
                        # heuristic: if any grill stem is substring, put in grill, etc
                        placed = False
                        for g in GRILL_SET:
                            if g in nn:
                                GRILL_SET.add(nn)
                                placed = True
                                break
                        if not placed:
                            for d in DRINK_SET:
                                if d in nn:
                                    DRINK_SET.add(nn)
                                    placed = True
                                    break
                        if not placed:
                            KITCHEN_SET.add(nn)
        except Exception:
            # ignore malformed menu.json (do not crash the service)
            pass
except Exception:
    pass

# Helper: check if any normalized stem appears in text (substring)
def _contains_stem(norm_text: str, stem_set: set) -> bool:
    if not norm_text:
        return False
    for s in stem_set:
        if s and s in norm_text:
            return True
    return False

def classify_order(order_text: str) -> List[Dict]:
    """
    Input: multi-line Greek order text (one dish per line)
    Output: list of {"text": original_line, "category": "grill"|"kitchen"|"drinks"}
    """
    results = []
    if not order_text:
        return results

    lines = [ln for ln in order_text.splitlines() if ln.strip()]
    for ln in lines:
        original = ln.strip()
        norm = _normalize_text_basic(original)

        # use spaCy lemmas if available to improve matching
        lemmas = norm
        if nlp_model:
            try:
                doc = nlp_model(norm)
                lemmas = " ".join([tok.lemma_ for tok in doc if tok.lemma_])
                lemmas = _strip_accents(lemmas.lower())
            except Exception:
                lemmas = norm

        # Decide category by priority: grill -> drinks -> kitchen (default)
        if _contains_stem(lemmas, GRILL_SET) or _contains_stem(norm, GRILL_SET):
            category = "grill"
        elif _contains_stem(lemmas, DRINK_SET) or _contains_stem(norm, DRINK_SET):
            category = "drinks"
        else:
            if _contains_stem(lemmas, KITCHEN_SET) or _contains_stem(norm, KITCHEN_SET):
                category = "kitchen"
            else:
                category = "kitchen"

        results.append({"text": original, "category": category})

    return results
