"""
Feature Contract for Quantum-Bio-Mashup (Week 2)

This module defines the frozen feature specification used for
similarity computation and graph construction.

IMPORTANT:
- This contract MUST NOT be changed after Week 2.
- Any modification invalidates reproducibility and comparisons.
"""

# ================================
# Global Feature Specification
# ================================

FEATURE_TYPE = "mel_spectrogram_mean"
FEATURE_DIM = 40
SAMPLING_RATE = 22050

# STFT parameters (inherited from Week 1, frozen)
N_FFT = 2048
HOP_LENGTH = 512

# Mel parameters
N_MELS = 40

# ================================
# Mathematical Definition
# ================================

FEATURE_DEFINITION = r"""
Given a beat-aligned audio segment with magnitude STFT |X(f, t)|,
we compute the power spectrogram:

    P(f, t) = |X(f, t)|^2

A mel filterbank is applied to P(f, t) to obtain a mel-spectrogram
M(m, t) with m = 1..40 mel bands.

The final feature vector v ∈ ℝ^40 is obtained by temporal averaging:

    v[m] = mean_t M(m, t)

All feature vectors are non-negative and subsequently ℓ2-normalized.
"""

# ================================
# Constraints (Must Hold)
# ================================

FEATURE_CONSTRAINTS = {
    "dimension": FEATURE_DIM,
    "non_negative": True,
    "fixed_sampling_rate": SAMPLING_RATE,
    "derived_from_power_spectrogram": True,
    "one_vector_per_segment": True,
}

# ================================
# Penalties / Constants (Defined Later)
# ================================

SAME_SONG_PENALTY = 0.7  # discourages trivial self-loops without forbidding them
