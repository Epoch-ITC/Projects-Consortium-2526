"""
Week 2 — Day 4
Frozen Compatibility Scoring Rule

This module defines the FINAL similarity score used
to construct the segment compatibility graph.
"""

import numpy as np

# =========================
# FROZEN CONSTANTS
# =========================
SAME_SONG_PENALTY = 0.7


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """
    Compute cosine similarity between two ℓ2-normalized vectors.
    Assumes ||v1|| = ||v2|| = 1.
    """
    return float(np.dot(v1, v2))


def compatibility_score(seg_a, seg_b) -> float:
    """
    Final, frozen compatibility score between two segments.
    """

    score = cosine_similarity(seg_a.features, seg_b.features)

    # Penalize same-song transitions
    if seg_a.parent_song == seg_b.parent_song:
        score *= SAME_SONG_PENALTY

    return score
