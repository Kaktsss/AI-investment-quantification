"""
AI Keyword Search Engine
========================
This module does one thing: it counts AI-related keywords in a text,
properly handling the "AI" abbreviation problem (word boundaries + case sensitivity).
"""

import re

# ---------------------------------------------------------------------------
# 1) "Safe" keywords: these clearly refer to AI.
#    We search for these case-insensitively because the phrase itself
#    is unambiguous (e.g., "machine learning" regardless of capitalization).
# ---------------------------------------------------------------------------
SAFE_KEYWORDS = [
    r"artificial intelligence",
    r"machine learning",
    r"deep learning",
    r"neural network",
    r"large language model",
    r"generative AI",          # AI is part of the phrase here, so it is safe
    r"generative artificial intelligence",
    r"natural language processing",
    r"computer vision",
    r"foundation model",
]

# ---------------------------------------------------------------------------
# 2) The separately handled, "noisy" abbreviation: AI
#    - \b ... \b  = word boundary, so it does NOT match the "ai" substring
#      in words like "said", "email", "chair".
#    - CASE-SENSITIVE: we only accept uppercase "AI". A lowercase "ai"
#      mid-sentence almost never means Artificial Intelligence.
# ---------------------------------------------------------------------------
# Negative lookbehind (?<!:) excludes ticker contexts like "(NYSE:AI)" or
# "(ENXTPA:AI)" where AI is a stock ticker, not artificial intelligence.
AI_ABBREV_PATTERN = re.compile(r"(?<!:)\bAI\b")         # uppercase AI only, with word boundaries

# We build a large, case-insensitive pattern for the safe keywords.
SAFE_PATTERN = re.compile(
    r"|".join(SAFE_KEYWORDS),
    flags=re.IGNORECASE,
)


def count_ai_terms(text: str) -> dict:
    """
    Returns a dictionary:
      - safe_hits:   the number of safe keyword matches
      - ai_hits:     the number of standalone, uppercase "AI" matches (kept separate!)
      - total_words: the number of words in the document (for normalization)
    The ai_hits is intentionally kept SEPARATE so you can see its impact and
    verify it if necessary.
    """
    safe_hits = len(SAFE_PATTERN.findall(text))
    ai_hits = len(AI_ABBREV_PATTERN.findall(text))
    total_words = len(text.split())
    return {
        "safe_hits": safe_hits,
        "ai_hits": ai_hits,
        "total_hits": safe_hits + ai_hits,
        "total_words": total_words,
    }


# ---------------------------------------------------------------------------
# TEST: synthetic text, full of traps.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_text = (
        "The company said it will maintain its email and retail chair. "        # traps: said, maintain, email, retail, chair -> CANNOT be AI
        "Our AI strategy focuses on artificial intelligence and machine learning. "  # AI (1) + safe (2)
        "We also invested in Generative AI and a large language model. "          # generative AI (safe) + AI? + large language model
        "Campaign and aircraft contain the letters a-i but are not AI. "          # campaign, aircraft: trap; a real AI at the end
        "ai in lowercase mid-sentence should NOT count."                          # lowercase ai -> DOES NOT count
    )

    result = count_ai_terms(test_text)
    print("=== TEST RESULT ===")
    print(f"Safe keyword matches (safe_hits): {result['safe_hits']}")
    print(f"Standalone uppercase 'AI' matches (ai_hits): {result['ai_hits']}")
    print(f"Total words: {result['total_words']}")
    print()

    # Let's show EXACTLY what was found so it can be verified:
    print("Found 'AI' occurrences (uppercase, standalone):")
    print("  ", AI_ABBREV_PATTERN.findall(test_text))
    print("Found safe keywords:")
    print("  ", SAFE_PATTERN.findall(test_text))