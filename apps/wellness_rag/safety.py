"""
Post-generation safety net: after Groq produces an answer, scan its text
for allergen-related keywords matching this mother's known allergies. This
is layered ON TOP of the prompt-level instruction (which already tells Groq
her allergies and asks it not to recommend around them) -- it doesn't
replace that instruction, it catches cases where the model mentions an
allergen anyway.

Deliberately scoped to the fixed HealthProfile.ALLERGY_CHOICES list only.
Condition-based keyword matching (e.g. "sugar" for gestational diabetes)
was left out on purpose -- it produces too many false positives to be
reliable ("blood sugar level" would trigger constantly). Conditions are
still passed into the prompt itself (see groq_client.build_prompt), just
not double-checked with keywords here.
"""

ALLERGEN_KEYWORDS = {
    "nuts": ["nut", "peanut", "almond", "cashew", "walnut", "pistachio", "hazelnut"],
    "dairy": ["dairy", "milk", "cheese", "yogurt", "yoghurt", "butter", "ghee", "paneer", "cream"],
    "gluten": ["gluten", "wheat", "barley", "rye", "roti", "chapati"],
    "shellfish": ["shellfish", "shrimp", "prawn", "crab", "lobster"],
    "eggs": ["egg"],
    "soy": ["soy", "soya", "tofu"],
}


def check_allergen_mentions(response_text, allergies):
    """
    allergies: list of allergen codes from HealthProfile.allergies. Returns
    a list of {"allergen", "matched_word"} for any allergen on her profile
    whose keywords appear in the response text.
    """
    if not allergies or not response_text:
        return []

    lowered = response_text.lower()
    hits = []
    for allergen in allergies:
        for kw in ALLERGEN_KEYWORDS.get(allergen, []):
            if kw in lowered:
                hits.append({"allergen": allergen, "matched_word": kw})
                break
    return hits