"""
Smoke test for the semantic pillar.
Verifies that sentence-transformers loads, downloads a small model,
and computes a cosine similarity. No project data yet - just plumbing.
"""
from sentence_transformers import SentenceTransformer, util

print("Loading model (first run downloads ~90 MB)...")
# all-MiniLM-L6-v2: small, fast, CPU-friendly, 384-dim - the same
# dimensionality Soto reports, and the standard lightweight choice.
model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = [
    "We develop deep neural networks and large language models for our products.",
    "Our machine learning research advances natural language processing.",
    "The company operates a chain of retail grocery stores in the region.",
]
emb = model.encode(sentences, convert_to_tensor=True)

print("\nCosine similarities:")
print(f"  AI-text vs AI-text:     {util.cos_sim(emb[0], emb[1]).item():.3f}")
print(f"  AI-text vs grocery-text:{util.cos_sim(emb[0], emb[2]).item():.3f}")
print("\nIf the first score is clearly higher than the second, C2 is viable.")