import cv2
import os
from ultralytics import YOLO
from compute_detection_heatmap import (
    compute_video_heatmap,
    normalize_and_smooth_heatmap,
    apply_heatmap_colormap,
    overlay_heatmap_on_frame
)


def test_heatmap_generation():
    """Test heatmap generation on a single video"""
    
    # Configuration
    video_path = "../../datasets/vb100_video/American_Avocet/American_Avocet_00003.mp4"
    
    yolo_model_path = "../runs/bird_yolov8n_combined5/weights/best.pt"
    output_dir = "../sample_outputs/heatmap_test"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 70)
    print("HEATMAP GENERATION TEST")
    print("=" * 70)
    print(f"Video: {video_path}")
    print(f"YOLO model: {yolo_model_path}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    # Load YOLO model
    print("\nLoading YOLO model...")
    yolo_model = YOLO(yolo_model_path)
    print("✓ Model loaded successfully")
    
    # Compute heatmap
    print("\nProcessing video to generate heatmap...")
    print("(This may take a moment...)")
    heatmap, frame_shape, total_detections = compute_video_heatmap(
        video_path, 
        yolo_model, 
        sample_rate=5  # Process every 5th frame for speed
    )
    
    print(f"\n✓ Heatmap generated!")
    print(f"  Frame shape: {frame_shape}")
    print(f"  Total detections: {total_detections}")
    print(f"  Max detection density: {heatmap.max():.0f}")
    print(f"  Mean detection density: {heatmap.mean():.2f}")
    
    # Normalize and smooth heatmap
    print("\nNormalizing and smoothing heatmap...")
    heatmap_smooth = normalize_and_smooth_heatmap(heatmap, sigma=5)
    print("✓ Heatmap processed")
    
    # Save raw heatmap visualization
    print("\nSaving heatmap visualizations...")
    heatmap_colored = apply_heatmap_colormap(heatmap_smooth)
    heatmap_output_path = os.path.join(output_dir, "heatmap.jpg")
    cv2.imwrite(heatmap_output_path, heatmap_colored)
    print(f"✓ Heatmap saved: {heatmap_output_path}")
    
    # Get a sample frame from the video
    print("\nCreating overlay visualization...")
    cap = cv2.VideoCapture(video_path)
    ret, sample_frame = cap.read()
    cap.release()
    
    if ret:
        # Create overlay
        overlay = overlay_heatmap_on_frame(sample_frame, heatmap_smooth, alpha=0.5)
        overlay_output_path = os.path.join(output_dir, "heatmap_overlay.jpg")
        cv2.imwrite(overlay_output_path, overlay)
        print(f"✓ Overlay saved: {overlay_output_path}")
        
        # Also save the original frame for comparison
        original_output_path = os.path.join(output_dir, "original_frame.jpg")
        cv2.imwrite(original_output_path, sample_frame)
        print(f"✓ Original frame saved: {original_output_path}")
    else:
        print("Warning: Could not read sample frame for overlay")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"All outputs saved to: {output_dir}")
    print("\nFiles created:")
    print(f"  - heatmap.jpg (color-coded heatmap)")
    print(f"  - heatmap_overlay.jpg (heatmap overlaid on video frame)")
    print(f"  - original_frame.jpg (sample frame for comparison)")
    print("=" * 70)


if __name__ == "__main__":
    test_heatmap_generation()
