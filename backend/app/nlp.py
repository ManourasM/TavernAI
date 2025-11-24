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

def _greek_stem(word: str) -> str:
    """
    Simple Greek stemming for common plural patterns.
    Examples:
    - "αρνια" -> "αρνι"
    - "κατσικια" -> "κατσικι"
    - "παιδακια" -> "παιδακι"
    """
    if not word:
        return word

    # Common Greek plural endings
    # -ια -> -ι (neuter plural)
    if word.endswith("ια") and len(word) > 3:
        return word[:-1]  # αρνια -> αρνι
    # -ες -> -α or -η (feminine/masculine plural)
    if word.endswith("ες") and len(word) > 3:
        return word[:-2]  # Could be -α or -η, but we'll just remove -ες
    # -οι -> -ος (masculine plural)
    if word.endswith("οι") and len(word) > 3:
        return word[:-2] + "ος"
    # -α -> keep as is (could be plural or singular)

    return word

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
                """Return one of 'grill', 'drinks', 'kitchen', or None based on a raw category string."""
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
                # check for kitchen category
                if "kitchen" in s or "κουζιν" in s or "special" in s or "φουρν" in s:
                    return "kitchen"
                # Default to kitchen for anything else (salads, appetizers, etc.)
                return "kitchen"

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

# Helper: check if any normalized stem appears in text (substring) or vice versa
def _contains_stem(norm_text: str, stem_set: set) -> bool:
    if not norm_text:
        return False
    for s in stem_set:
        if not s:
            continue
        # Check both directions: stem in text OR text in stem
        # This handles cases like "μυθος" matching "μυθος 500ml"
        if s in norm_text or norm_text in s:
            return True
    return False

def _extract_parentheses(text: str) -> tuple:
    """
    Extract text in parentheses and return (base_text, parentheses_content).

    Examples:
    - "2 μυθος (χωρίς σάλτσα)" -> ("2 μυθος", "(χωρίς σάλτσα)")
    - "2 μυθος" -> ("2 μυθος", "")
    - "2 κατσικι (χωρις αλατι)" -> ("2 κατσικι", "(χωρις αλατι)")
    """
    import re

    if not text:
        return ("", "")

    # Find all parentheses content
    parentheses_pattern = r'\s*(\([^)]*\))\s*'
    matches = list(re.finditer(parentheses_pattern, text))

    if not matches:
        return (text.strip(), "")

    # Extract all parentheses content
    parentheses_parts = []
    for match in matches:
        parentheses_parts.append(match.group(1))

    # Remove parentheses from base text
    base_text = re.sub(parentheses_pattern, ' ', text)
    base_text = re.sub(r'\s+', ' ', base_text).strip()

    # Join all parentheses content
    parentheses_content = " ".join(parentheses_parts)

    return (base_text, parentheses_content)

def _parse_quantity_and_units(user_input: str) -> tuple:
    """
    Parse quantity, units, and item text from user input.

    IMPORTANT: Units must be directly after quantity with NO SPACE (e.g., "2kg" not "2 κ")

    Examples:
    - "2 μυθος" -> (2, None, None, "μυθος")
    - "2λ κρασι λευκο" -> (2, "λ", None, "κρασι λευκο")
    - "2.5kg παιδακια" -> (2.5, "kg", None, "παιδακια")
    - "500ml ρακι" -> (500, "ml", None, "ρακι")
    - "μυθος" -> (None, None, None, "μυθος")

    Returns: (quantity, unit, unit_multiplier, item_text)
    - quantity: numeric quantity (can be float)
    - unit: the unit string (λ, kg, ml, etc.) or None
    - unit_multiplier: calculated multiplier for pricing (e.g., 2λ = 2x, 500ml = 2x for 250ml items)
    - item_text: the item description
    """
    import re

    # Pattern: number (int or decimal) + optional unit (NO SPACE) + item text
    # Units: λ, λτ, lt, l (liters), kg, κ, κιλα, κιλο (kilos), ml (milliliters)
    # IMPORTANT: No \s* between number and unit - they must be adjacent
    pattern = r'^(\d+(?:\.\d+)?)(λτ|λ|lt|l|kg|κιλα|κιλο|κ|ml)?\s+(.+)$'
    match = re.match(pattern, user_input.strip(), re.IGNORECASE)

    if match:
        quantity = float(match.group(1))
        unit = match.group(2).lower() if match.group(2) else None
        item_text = match.group(3).strip()

        # Calculate unit multiplier for pricing
        unit_multiplier = None
        if unit:
            if unit in ['λ', 'λτ', 'lt', 'l']:
                # Liters: 1λ = 1x, 2λ = 2x
                unit_multiplier = quantity
            elif unit in ['kg', 'κ', 'κιλα', 'κιλο']:
                # Kilos: 1kg = 1x, 2.5kg = 2.5x
                unit_multiplier = quantity
            elif unit == 'ml':
                # Milliliters: 500ml = 2x for 250ml items, 250ml = 1x
                unit_multiplier = quantity / 250.0

        return (quantity, unit, unit_multiplier, item_text)

    # Try pattern without unit (just quantity + space + item)
    pattern_no_unit = r'^(\d+(?:\.\d+)?)\s+(.+)$'
    match_no_unit = re.match(pattern_no_unit, user_input.strip())

    if match_no_unit:
        quantity = float(match_no_unit.group(1))
        item_text = match_no_unit.group(2).strip()
        return (quantity, None, None, item_text)

    # No quantity found
    return (None, None, None, user_input.strip())


def _format_with_quantity_and_units(quantity, unit, item_text):
    """
    Format the item text with quantity and units.

    Examples:
    - (2, None, "μυθος") -> "2 μυθος"
    - (2, "λ", "κρασι λευκο") -> "2x λ κρασι λευκο"
    - (2, "kg", "παιδακια") -> "2x κ παιδακια"
    """
    if quantity is None:
        return item_text

    if unit is None:
        return f"{quantity} {item_text}"

    # Normalize unit display
    # Liters: λ, λτ, lt, l -> "λ"
    # Kilos: kg, κ, κιλα, κιλο -> "κ"
    if unit in ['λ', 'λτ', 'lt', 'l']:
        normalized_unit = 'λ'
    elif unit in ['kg', 'κ', 'κιλα', 'κιλο']:
        normalized_unit = 'κ'
    else:
        normalized_unit = unit

    return f"{quantity}x {normalized_unit} {item_text}"


def _find_menu_match_with_units(item_text: str, unit: str, quantity: float) -> dict:
    """
    Find the best menu match considering units.

    Examples:
    - ("κρασι λευκο", "λ", 2) -> matches "Κρασί λευκό (1lt)" with multiplier 2
    - ("κρασι λευκο", None, 2) -> matches "Κρασί λευκό (0.5)" with multiplier 2
    - ("ρακι", "ml", 500) -> matches "Ρακί (250)" with multiplier 2
    - ("παιδακια", "kg", 2.5) -> matches "κ Αρνίσια παϊδάκια" with multiplier 2.5
    - ("παιδακια", None, 2) -> matches "Αρνίσια παϊδάκια" (portion) with multiplier 2

    Returns: {
        "menu_id": str or None,
        "menu_name": str or None,
        "price": float or None,
        "category": str or None,  # "grill"|"kitchen"|"drinks"
        "multiplier": float (for calculating total price)
    }
    """
    norm_input = _normalize_text_basic(item_text)
    if not norm_input:
        return {"menu_id": None, "menu_name": None, "price": None, "category": None, "multiplier": quantity or 1}

    # Apply Greek stemming to input words for better matching
    input_words = norm_input.split()
    stemmed_input_words = [_greek_stem(w) for w in input_words]
    stemmed_input = " ".join(stemmed_input_words)

    best_match = None
    best_score = 0

    for norm_menu_name, menu_data in MENU_ITEMS.items():
        menu_name = menu_data["name"]

        # Check if this is a unit-based item (has "κ " prefix or size in parentheses)
        is_kg_item = menu_name.startswith("κ ")
        has_size_spec = "(" in menu_name and ")" in menu_name

        # Extract the base item name (without "κ " prefix and size specs)
        base_menu_name = menu_name
        if is_kg_item:
            base_menu_name = menu_name[2:]  # Remove "κ " prefix
        if has_size_spec:
            base_menu_name = base_menu_name.split("(")[0].strip()

        norm_base_menu = _normalize_text_basic(base_menu_name)

        # Apply Greek stemming to menu words for better matching
        menu_words = norm_base_menu.split()
        stemmed_menu_words = [_greek_stem(w) for w in menu_words]
        stemmed_menu = " ".join(stemmed_menu_words)

        # Calculate match score using both original and stemmed versions
        match_found = False
        if norm_input in norm_base_menu or norm_base_menu in norm_input:
            match_found = True
        elif stemmed_input in stemmed_menu or stemmed_menu in stemmed_input:
            match_found = True

        if match_found:
            score = min(len(norm_input), len(norm_base_menu)) / max(len(norm_input), len(norm_base_menu))

            # Apply unit-based matching rules
            if unit in ['kg', 'κ', 'κιλα', 'κιλο']:
                # User wants kg - prefer "κ " items
                if is_kg_item:
                    score += 1.0  # Strong preference
                else:
                    score -= 0.5  # Penalize non-kg items
            elif unit in ['λ', 'λτ', 'lt', 'l']:
                # User wants liters - prefer (1lt) items
                if "(1lt)" in menu_name or "(1)" in menu_name:
                    score += 1.0
                elif "(0.5)" in menu_name:
                    score -= 0.3  # Slight penalty for 0.5 items
            elif unit == 'ml':
                # User wants ml - match to appropriate size
                if "(250)" in menu_name and quantity >= 250:
                    score += 1.0
                elif "(500)" in menu_name and quantity >= 500:
                    score += 1.0
            else:
                # No unit specified - prefer portion items (non-kg, non-liter)
                if is_kg_item:
                    score -= 0.5  # Penalize kg items when no unit specified
                elif "(1lt)" in menu_name:
                    score -= 0.3  # Slight penalty for liter items

            if score > best_score:
                best_score = score
                best_match = menu_data

    if best_match and best_score >= 0.3:
        # Calculate multiplier based on unit
        multiplier = quantity or 1
        if unit in ['kg', 'κ', 'κιλα', 'κιλο', 'λ', 'λτ', 'lt', 'l']:
            multiplier = quantity
        elif unit == 'ml':
            # For ml, calculate based on menu item size
            if "(250)" in best_match["name"]:
                multiplier = quantity / 250.0
            elif "(500)" in best_match["name"]:
                multiplier = quantity / 500.0
            else:
                multiplier = quantity / 1000.0  # Default to liters

        return {
            "menu_id": best_match["id"],
            "menu_name": best_match["name"],
            "price": best_match["price"],
            "category": best_match["category"],  # Include category from menu
            "multiplier": multiplier
        }

    return {"menu_id": None, "menu_name": None, "price": None, "category": None, "multiplier": quantity or 1}


def classify_order(order_text: str) -> List[Dict]:
    """
    Input: multi-line Greek order text (one dish per line)
    Output: list of {
        "text": original_user_text,  # Preserved as user wrote it
        "category": "grill"|"kitchen"|"drinks",
        "menu_id": str or None,  # Matched menu item ID
        "menu_name": str or None,  # Matched menu item name (for pricing display)
        "price": float or None,  # Unit price from menu
        "multiplier": float  # Quantity multiplier for total price calculation
    }

    The original text is preserved exactly as the user wrote it.
    Menu matching is done separately for pricing purposes.

    Examples:
    - "2 μυθος" -> text="2 μυθος", menu_name="Μύθος", price=4.0, multiplier=2
    - "2λ κρασι λευκο" -> text="2λ κρασι λευκο", menu_name="Κρασί λευκό (1lt)", price=10.0, multiplier=2
    - "2kg παιδακια" -> text="2kg παιδακια", menu_name="κ Αρνίσια παϊδάκια", price=40.0, multiplier=2
    - "2 παιδακια" -> text="2 παιδακια", menu_name="Αρνίσια παϊδάκια", price=15.0, multiplier=2
    """
    results = []
    if not order_text:
        return results

    lines = [ln for ln in order_text.splitlines() if ln.strip()]
    for ln in lines:
        original = ln.strip()

        # Extract parentheses content (e.g., "(χωρίς σάλτσα)")
        # This should be preserved for display but not used for matching
        base_text, parentheses_content = _extract_parentheses(original)

        # Parse quantity and units from base text (without parentheses)
        quantity, unit, unit_multiplier, item_text = _parse_quantity_and_units(base_text)

        # Normalize for classification (without quantity/units and parentheses)
        norm = _normalize_text_basic(item_text)

        # use spaCy lemmas if available to improve matching
        lemmas = norm
        if nlp_model:
            try:
                doc = nlp_model(norm)
                lemmas = " ".join([tok.lemma_ for tok in doc if tok.lemma_])
                lemmas = _strip_accents(lemmas.lower())
            except Exception:
                lemmas = norm

        # Find menu match with unit awareness (using text without parentheses)
        menu_match = _find_menu_match_with_units(item_text, unit, quantity or 1)

        # Decide category - use menu match category if available, otherwise classify
        if menu_match["menu_id"] and menu_match["category"]:
            # Use category from matched menu item
            category = menu_match["category"]
        else:
            # No menu match or no category - classify by keywords
            if _contains_stem(lemmas, GRILL_SET) or _contains_stem(norm, GRILL_SET):
                category = "grill"
            elif _contains_stem(lemmas, DRINK_SET) or _contains_stem(norm, DRINK_SET):
                category = "drinks"
            else:
                if _contains_stem(lemmas, KITCHEN_SET) or _contains_stem(norm, KITCHEN_SET):
                    category = "kitchen"
                else:
                    category = "kitchen"

        results.append({
            "text": original,  # Preserve original user text exactly
            "category": category,
            "menu_id": menu_match["menu_id"],
            "menu_name": menu_match["menu_name"],
            "price": menu_match["price"],
            "multiplier": menu_match["multiplier"]
        })

    return results
