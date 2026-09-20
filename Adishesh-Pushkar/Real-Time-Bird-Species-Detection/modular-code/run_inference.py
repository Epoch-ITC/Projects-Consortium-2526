"""
Video Inference Script
Main script for running bird detection and species classification on video files.
"""

import os
import cv2
import time
import argparse
from model import BirdDetectionPipeline


def process_video(
    video_path,
    output_path,
    yolo_model_path="yolo11n.pt",
    species_model_path="models/species_classifier.pth",
    num_classes=500,
    detect_conf=0.25,
    classify_threshold=0.0,
    show_species=True,
    show_detection_conf=False,
    display_interval=30
):
    """
    Process a video file with bird detection and species classification.
    
    Args:
        video_path: Path to input video file
        output_path: Path to save output video
        yolo_model_path: Path to YOLO model weights
        species_model_path: Path to species classifier weights
        num_classes: Number of bird species classes
        detect_conf: Confidence threshold for bird detection
        classify_threshold: Minimum confidence for species classification
        show_species: Whether to display species labels
        show_detection_conf: Whether to display detection confidence
        display_interval: Print progress every N frames
    """
    # Initialize pipeline
    print("\n" + "="*60)
    print("INITIALIZING BIRD DETECTION PIPELINE")
    print("="*60)
    
    pipeline = BirdDetectionPipeline(
        yolo_model_path=yolo_model_path,
        species_model_path=species_model_path,
        num_classes=num_classes
    )
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print("\n" + "="*60)
    print("VIDEO INFORMATION")
    print("="*60)
    print(f"Input: {video_path}")
    print(f"Output: {output_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total Frames: {total_frames}")
    print(f"Duration: {total_frames/fps:.2f} seconds")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Processing loop
    print("\n" + "="*60)
    print("PROCESSING VIDEO")
    print("="*60)
    
    frame_count = 0
    total_time = 0
    total_detections = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        start_time = time.time()
        
        # Process frame
        detections = pipeline.process_frame(
            frame,
            detect_conf=detect_conf,
            classify_threshold=classify_threshold
        )
        
        # Annotate frame
        annotated_frame = pipeline.annotate_frame(
            frame,
            detections,
            show_species=show_species,
            show_detection_conf=show_detection_conf
        )
        
        inference_time = time.time() - start_time
        total_time += inference_time
        frame_count += 1
        total_detections += len(detections)
        
        # Write frame
        out.write(annotated_frame)
        
        # Print progress
        if frame_count % display_interval == 0:
            avg_fps = frame_count / total_time
            progress_pct = (frame_count / total_frames) * 100
            print(f"Frame {frame_count}/{total_frames} ({progress_pct:.1f}%) | "
                  f"Time: {inference_time*1000:.2f}ms | "
                  f"FPS: {avg_fps:.2f} | "
                  f"Detections: {len(detections)}")
    
    # Cleanup
    cap.release()
    out.release()
    
    # Print final statistics
    avg_inference_time = total_time / frame_count
    avg_fps = frame_count / total_time
    avg_detections_per_frame = total_detections / frame_count
    
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    print(f"Total frames processed: {frame_count}")
    print(f"Total processing time: {total_time:.2f} seconds")
    print(f"Video FPS: {fps}")
    print(f"Average inference time: {avg_inference_time*1000:.2f} ms")
    print(f"Average processing FPS: {avg_fps:.2f}")
    print(f"Total detections: {total_detections}")
    print(f"Average detections per frame: {avg_detections_per_frame:.2f}")
    print(f"\nOutput saved to: {output_path}")
    print("="*60)


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Bird Detection and Species Classification on Video"
    )
    
    # Required arguments
    parser.add_argument(
        "video_path",
        type=str,
        help="Path to input video file"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output.mp4",
        help="Path to output video file (default: output.mp4)"
    )
    
    # Model paths
    parser.add_argument(
        "--yolo-model",
        type=str,
        default="yolo11n.pt",
        help="Path to YOLO model weights (default: yolo11n.pt)"
    )
    
    parser.add_argument(
        "--species-model",
        type=str,
        default="models/species_classifier.pth",
        help="Path to species classifier weights (default: models/species_classifier.pth)"
    )
    
    parser.add_argument(
        "--num-classes",
        type=int,
        default=500,
        help="Number of bird species classes (default: 500)"
    )
    
    # Detection parameters
    parser.add_argument(
        "--detect-conf",
        type=float,
        default=0.25,
        help="Confidence threshold for bird detection (default: 0.25)"
    )
    
    parser.add_argument(
        "--classify-threshold",
        type=float,
        default=0.0,
        help="Minimum confidence threshold for species classification (default: 0.0)"
    )
    
    # Display options
    parser.add_argument(
        "--no-species",
        action="store_true",
        help="Don't show species classification labels"
    )
    
    parser.add_argument(
        "--show-detection-conf",
        action="store_true",
        help="Show detection confidence in labels"
    )
    
    parser.add_argument(
        "--display-interval",
        type=int,
        default=30,
        help="Print progress every N frames (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.video_path):
        raise FileNotFoundError(f"Video file not found: {args.video_path}")
    
    # Process video
    process_video(
        video_path=args.video_path,
        output_path=args.output,
        yolo_model_path=args.yolo_model,
        species_model_path=args.species_model,
        num_classes=args.num_classes,
        detect_conf=args.detect_conf,
        classify_threshold=args.classify_threshold,
        show_species=not args.no_species,
        show_detection_conf=args.show_detection_conf,
        display_interval=args.display_interval
    )


if __name__ == "__main__":
    main()
