#!/bin/bash

set -e  # stop immediately on error

echo "==========================================="
echo "Quantum-Bio Mashup: FULL PIPELINE START"
echo "==========================================="

echo ""
echo "STEP 1: WAV -> NPY (Normalization)"
python -m src.audio_io

echo ""
echo "STEP 2: Beat Tracking + Bar Slicing"
python -m src.slicing

echo ""
echo "STEP 3: Build Segment Objects (master_db.pkl)"
python -m src.build_segments

echo ""
echo "STEP 4: Feature Extraction"
python -m src.w2d1

echo ""
echo "STEP 5: Validate Raw Features"
python -m src.w2d2_validate_features

echo ""
echo "STEP 6: Normalize Features"
python -m src.w2d3_normalize_features

echo ""
echo "STEP 7: Similarity Matrix"
python -m src.w2d4_similarity

echo ""
echo "STEP 8: Build KNN Graph"
python -m src.w2d5_build_knn_graph

echo ""
echo "STEP 9: Symmetrize + Validate Graph"
python -m src.w2d5_symmetrize_and_validate

echo ""
echo "STEP 10: Hamiltonian Construction + Spectrum"
python -m src.w3d1_hamiltonian_analysis

echo ""
echo "STEP 11: Core CTQW Evolution"
python -m src.w3_core_quantum_evolution

echo ""
echo "STEP 12: Decoherence (ENAQT)"
python -m src.w3d4_ctqw_decoherence

echo ""
echo "STEP 13: Bio-Modulated Quantum Walk"
python -m src.w3d5_bio_ctqw

echo ""
echo "STEP 14: Extract Quantum Path"
python -m src.w3d3_quantum_path

echo ""
echo "STEP 15: Build Final Mashup Audio"
python -m src.w3d6_final_mashup

echo ""
echo "==========================================="
echo "PIPELINE COMPLETE SUCCESSFULLY"
echo "==========================================="