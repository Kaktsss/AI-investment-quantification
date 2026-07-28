"""
Tier 2: semantic hype-filter.

Scores 10-K text chunks by cosine similarity against a baseline corpus of
genuinely technical AI-research sentences (arXiv-abstract register), as a
proxy for "does this firm's AI language resemble real technical AI content
or generic corporate hype." The baseline corpus below is a first-pass
placeholder (per project instructions) - swap in a real arXiv abstract
sample later without changing any of the scoring logic.
"""

import logging

import numpy as np
from sentence_transformers import SentenceTransformer, util

import config

logger = logging.getLogger("pillar_c.semantic_tier2")

BASELINE_SENTENCES = [
    # Transformer / attention architectures
    "We propose a transformer architecture that relies entirely on self-attention "
    "mechanisms, dispensing with recurrence and convolutions.",
    "Multi-head attention allows the model to jointly attend to information from "
    "different representation subspaces at different positions.",
    # Training objectives & optimization
    "The model is pretrained on a masked language modeling objective and fine-tuned "
    "on downstream tasks with a cross-entropy loss.",
    "We optimize the network parameters using stochastic gradient descent with a "
    "cosine learning rate schedule and gradient clipping.",
    "Our training procedure uses contrastive learning to align image and text "
    "embeddings in a shared latent space.",
    # Benchmarks & evaluation
    "We evaluate our model on the GLUE and SuperGLUE benchmarks, reporting accuracy "
    "and F1 score across all tasks.",
    "Ablation studies show that removing the positional encoding degrades "
    "performance by several points on the held-out test set.",
    "We report perplexity on the WikiText-103 corpus and compare against prior "
    "state-of-the-art language models.",
    # Model families
    "BERT is a bidirectional encoder representation trained via masked language "
    "modeling and next sentence prediction.",
    "GPT-style autoregressive language models generate text by predicting the next "
    "token conditioned on all previous tokens.",
    "We use a ResNet-50 backbone pretrained on ImageNet as the feature extractor "
    "for our object detection pipeline.",
    "Diffusion models learn to reverse a gradual noising process to generate "
    "high-fidelity samples from random noise.",
    # Reinforcement learning
    "The agent is trained using proximal policy optimization to maximize expected "
    "cumulative reward in the environment.",
    "We apply reinforcement learning from human feedback to align the model's "
    "outputs with human preferences.",
    # Computer vision tasks
    "Our convolutional neural network achieves state-of-the-art accuracy on "
    "large-scale image classification benchmarks.",
    "The semantic segmentation model predicts a per-pixel class label using an "
    "encoder-decoder architecture with skip connections.",
    # NLP tasks
    "The named entity recognition model uses a bidirectional LSTM with a "
    "conditional random field layer for sequence labeling.",
    "We fine-tune a pretrained language model for extractive question answering "
    "by predicting start and end token spans.",
    # Data / methodology
    "We construct a large-scale labeled dataset and split it into training, "
    "validation, and test sets using stratified sampling.",
    "Hyperparameters were selected via grid search on a held-out validation set, "
    "and results are averaged over five random seeds.",
]

_model = None
_baseline_embeddings = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model: %s", config.EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def get_baseline_embeddings():
    global _baseline_embeddings
    if _baseline_embeddings is None:
        _baseline_embeddings = get_model().encode(BASELINE_SENTENCES, convert_to_tensor=True)
    return _baseline_embeddings


def _select_chunk_texts(chunks: list, keyword_hit_mask: list | None) -> list:
    texts = [c["text"] for c in chunks]

    if config.TIER1_GATES_TIER2 and keyword_hit_mask is not None:
        gated = [t for t, hit in zip(texts, keyword_hit_mask) if hit]
        if gated:
            texts = gated
        else:
            logger.debug("Tier1 gate left zero chunks; falling back to all chunks for this filing")

    if len(texts) > config.MAX_CHUNKS_PER_FILING:
        rng = np.random.default_rng(config.RANDOM_STATE)
        keep_idx = np.sort(
            rng.choice(len(texts), size=config.MAX_CHUNKS_PER_FILING, replace=False)
        )
        texts = [texts[i] for i in keep_idx]

    return texts


def score_filing(chunks: list, keyword_hit_mask: list = None) -> dict:
    """
    Scores a filing's chunks against the baseline corpus.

    Per-chunk score = max cosine similarity vs. any baseline sentence.
    Per-filing score = mean of the top-k per-chunk scores (k capped by
    both TOP_K_CHUNKS_FOR_TIER2 and the number of chunks actually available).

    Returns {"tier2_semantic_score": float | None, "n_chunks_scored": int}.
    """
    texts = _select_chunk_texts(chunks, keyword_hit_mask)
    if not texts:
        return {"tier2_semantic_score": None, "n_chunks_scored": 0}

    model = get_model()
    baseline_embeddings = get_baseline_embeddings()
    chunk_embeddings = model.encode(texts, convert_to_tensor=True)

    sims = util.cos_sim(chunk_embeddings, baseline_embeddings)  # (n_chunks, n_baseline)
    per_chunk_max = sims.max(dim=1).values.cpu().numpy()

    k = min(config.TOP_K_CHUNKS_FOR_TIER2, len(per_chunk_max))
    top_k = np.sort(per_chunk_max)[::-1][:k]
    score = float(np.mean(top_k))

    return {"tier2_semantic_score": score, "n_chunks_scored": len(texts)}
