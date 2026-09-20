import argparse
import os
import cv2
import time
import json
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b3
from ultralytics import YOLO
from PIL import Image
import numpy as np
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
import torch.nn.functional as F
from torchvision.models import efficientnet_b1, EfficientNet_B1_Weights

from yolo_inference import Track


def load_yolo_model(model_path):
    """Load YOLOv8 bird detection model"""
    print(f"Loading YOLO model from {model_path}...")
    model = YOLO(model_path)
    print(" YOLO model loaded successfully")
    return model


def load_sahi_model(model_path, confidence_threshold=0.25, device='cuda'):
    """Load YOLO model wrapped with SAHI for sliced inference"""
    print(f"Loading YOLO model with SAHI from {model_path}...")
    
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='yolov8',
        model_path=model_path,
        confidence_threshold=confidence_threshold,
        device=device
    )
    
    print(" SAHI model loaded successfully")
    return detection_model


def load_species_classifier(model_path, num_classes=500, device='cuda'):
    """Load EfficientNet-B1 species classifier with custom head"""
    print(f"Loading species classifier from {model_path}...")
    
    # Load ImageNet weights for structure
    weights = EfficientNet_B1_Weights.IMAGENET1K_V1
    model = efficientnet_b1(weights=weights)
    
    # Rebuild classifier exactly as in training
    in_features = model.classifier[1].in_features  # 1280 for B1
    
    model.classifier = nn.Sequential(
        nn.Linear(in_features, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(inplace=True),
        nn.Dropout(0.2),
        nn.Linear(512, num_classes)
    )
    
    # Load trained weights
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    
    model.to(device)
    model.eval()
    
    print(f" Species classifier loaded successfully (Device: {device})")
    return model


def load_idx_to_class(json_path):
    """Load index to class name mapping from JSON file"""
    with open(json_path, 'r') as f:
        idx_to_class = json.load(f)
    # Convert string keys to integers
    return {int(k): v for k, v in idx_to_class.items()}


def get_preprocess_transforms():
    """Get preprocessing transforms for species classifier"""
    return transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])


def classify_bird_species(bird_crop, species_model, preprocess, device):
    """
    Classify a bird crop into species
    
    Args:
        bird_crop: numpy array (H, W, C) in BGR format
        species_model: EfficientNet classifier
        preprocess: torchvision transforms
        device: torch device
    
    Returns:
        species_id: Predicted species class ID
        confidence: Prediction confidence
    """
    # Convert BGR to RGB and to PIL Image
    bird_rgb = cv2.cvtColor(bird_crop, cv2.COLOR_BGR2RGB)
    bird_pil = Image.fromarray(bird_rgb)
    
    # Preprocess and run inference
    input_tensor = preprocess(bird_pil).unsqueeze(0).to(device)
    
    with torch.no_grad():
        outputs = species_model(input_tensor)
        probabilities = torch.softmax(outputs, dim=1)
        confidence, species_id = torch.max(probabilities, 1)
    
    return species_id.item(), confidence.item()


def process_video(input_path, output_path, sahi_model, species_model, preprocess, device, idx_to_class, 
                  slice_height=640, slice_width=640, overlap_ratio=0.2):
    """
    Process video with bird detection and species classification using SAHI and Kalman tracking
    
    Args:
        input_path: Path to input video
        output_path: Path to save output video
        sahi_model: SAHI-wrapped YOLO model
        species_model: EfficientNet species classifier
        preprocess: Preprocessing transforms
        device: torch device
        idx_to_class: Dictionary mapping species ID to class name
        slice_height: Height of each slice for SAHI
        slice_width: Width of each slice for SAHI
        overlap_ratio: Overlap ratio between slices
    """
    # Open video
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {input_path}")
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\nVideo Properties:")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Total Frames: {total_frames}")
    print(f"  Duration: {total_frames/fps:.2f} seconds")
    print(f"  Using SAHI: slice_size={slice_height}x{slice_width}, overlap={overlap_ratio}")
    print(f"  Using Kalman-based tracking")
    print("\nProcessing video...")
    print("-" * 60)
    
    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print("Warning: mp4v codec failed, trying XVID...")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        output_path_avi = output_path.rsplit('.', 1)[0] + '.avi'
        out = cv2.VideoWriter(output_path_avi, fourcc, fps, (width, height))
        output_path = output_path_avi
        
        if not out.isOpened():
            raise RuntimeError("Failed to open video writer with any codec")
    
    frame_count = 0
    total_inference_time = 0
    total_detections = 0
    
    # Dictionary to cache species classifications for each track ID
    track_species_cache = {}
    
    # Kalman tracking variables (using Track class from yolo_inference.py)
    tracks = []
    track_id_counter = 0
    max_age = 60  # Maximum frames to keep track without update
    min_hits = 1  # Minimum hits before displaying track
    dist_threshold = 100  # Distance threshold for track-detection matching
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            start_time = time.time()
                
            # Step 1: SAHI sliced inference for bird detection
            result = get_sliced_prediction(
                frame,
                sahi_model,
                slice_height=slice_height,
                slice_width=slice_width,
                overlap_height_ratio=overlap_ratio,
                overlap_width_ratio=overlap_ratio,
                postprocess_type="NMS",
                postprocess_match_metric="IOS",
                postprocess_match_threshold=0.5,
                verbose=0
            )
            
            # Step 2: Extract detections from SAHI results
            detections = []
            for object_prediction in result.object_prediction_list:
                bbox = object_prediction.bbox
                x1, y1, x2, y2 = int(bbox.minx), int(bbox.miny), int(bbox.maxx), int(bbox.maxy)
                det_conf = object_prediction.score.value
                
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width_box = x2 - x1
                height_box = y2 - y1
                
                detections.append({
                    'center': (center_x, center_y), 
                    'size': (width_box, height_box), 
                    'box': (x1, y1, x2, y2), 
                    'conf': det_conf
                })
            
            total_detections += len(detections)
            
            # Step 3: Kalman Tracking - Predict new locations of existing tracks
            for track in tracks:
                track.predict()
            
            # Step 4: Associate detections to tracks
            assigned_tracks = []
            assigned_detections = []
            
            if len(tracks) > 0 and len(detections) > 0:
                # Calculate distance matrix between tracks and detections
                dists = np.zeros((len(tracks), len(detections)))
                for i, track in enumerate(tracks):
                    for j, det in enumerate(detections):
                        # Euclidean distance between predicted track position and detection center
                        d = np.linalg.norm(track.prediction - np.array(det['center']))
                        dists[i, j] = d
                
                # Simple greedy matching (you can use Hungarian algorithm for better results)
                indices = np.argsort(dists, axis=None)
                for idx in indices:
                    r, c = np.unravel_index(idx, dists.shape)
                    dist = dists[r, c]
                    
                    # Match if distance is below threshold and not already assigned
                    if r not in assigned_tracks and c not in assigned_detections and dist < dist_threshold:
                        assigned_tracks.append(r)
                        assigned_detections.append(c)
                        # Update track with new detection
                        tracks[r].update(detections[c]['center'], detections[c]['size'])
            
            # Step 5: Create new tracks for unmatched detections
            for i, det in enumerate(detections):
                if i not in assigned_detections:
                    new_track = Track(track_id_counter, det['center'])
                    new_track.box_size = det['size']
                    tracks.append(new_track)
                    track_id_counter += 1
            
            # Step 6: Remove old tracks that haven't been updated
            tracks = [t for t in tracks if t.time_since_update < max_age]
            
            # Step 7: Draw tracks and classify species
            active_tracks = 0
            for track in tracks:
                # Only display tracks that are recently updated and have minimum hits
                if track.time_since_update < 5 and track.hits >= min_hits:
                    active_tracks += 1
                    
                    # Get predicted position and size
                    cx, cy = map(int, track.prediction)
                    w, h = map(int, track.box_size)
                    x1 = max(0, int(cx - w/2))
                    y1 = max(0, int(cy - h/2))
                    x2 = min(width, int(cx + w/2))
                    y2 = min(height, int(cy + h/2))
                    
                    # Ensure valid crop dimensions
                    if x2 <= x1 or y2 <= y1:
                        continue
                    
                    # Crop bird region for classification
                    bird_crop = frame[y1:y2, x1:x2]
                    
                    if bird_crop.size > 0:
                        # Step 8: Classify species (use cache to avoid re-classifying same track)
                        if track.track_id in track_species_cache:
                            species_id, species_conf = track_species_cache[track.track_id]
                        else:
                            species_id, species_conf = classify_bird_species(
                                bird_crop, species_model, preprocess, device
                            )
                            track_species_cache[track.track_id] = (species_id, species_conf)
                        
                        # Draw bounding box (blue for tracked birds)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                        
                        # Create label with track ID and species
                        species_name = idx_to_class.get(species_id, f"Unknown_{species_id}")
                        label = f"ID:{track.track_id} {species_name}: {species_conf:.2%}"
                        
                        # Draw label background
                        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                        cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                                    (x1 + label_size[0], y1), (255, 0, 0), -1)
                        
                        # Draw label text
                        cv2.putText(frame, label, (x1, y1 - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
            inference_time = time.time() - start_time
            total_inference_time += inference_time
            
            # Write processed frame
            out.write(frame)
            frame_count += 1
                
            # Print progress every 30 frames
            if frame_count % 30 == 0:
                avg_fps = frame_count / total_inference_time
                progress = (frame_count / total_frames) * 100
                print(f"Frame {frame_count}/{total_frames} ({progress:.1f}%) | "
                      f"Time: {inference_time*1000:.2f}ms | "
                      f"Avg FPS: {avg_fps:.2f} | "
                      f"Detections: {len(detections)} | "
                      f"Active Tracks: {active_tracks}")
    
    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
    
    # Print final statistics
    avg_inference_time = total_inference_time / frame_count if frame_count > 0 else 0
    avg_fps = frame_count / total_inference_time if total_inference_time > 0 else 0
    
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total frames processed: {frame_count}")
    print(f"Total detections: {total_detections}")
    print(f"Unique tracks created: {track_id_counter}")
    print(f"Average inference time: {avg_inference_time*1000:.2f} ms/frame")
    print(f"Average processing FPS: {avg_fps:.2f}")
    print(f"\nOutput saved to: {output_path}")


def find_video_files(root_folder):
    """
    Find all video files in the folder structure
    
    Args:
        root_folder: Root directory containing species subfolders
    
    Returns:
        List of tuples (video_path, species_name, video_filename)
    """
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []
    
    # Iterate through each subfolder (species folder)
    for species_name in os.listdir(root_folder):
        species_path = os.path.join(root_folder, species_name)
        
        # Skip if not a directory
        if not os.path.isdir(species_path):
            continue
        
        # Find all video files in this species folder
        for filename in os.listdir(species_path):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in video_extensions:
                video_path = os.path.join(species_path, filename)
                video_files.append((video_path, species_name, filename))
    
    return video_files



def main():
    parser = argparse.ArgumentParser(
        description="Bird Detection and Species Classification Pipeline (SAHI + Kalman Tracking)"
    )

    # parser.add_argument(
    #     "--prototypes",
    #     type=str,
    #     default="../../class_prototypes.pt",
    #     help="Path to class prototypes"
    # )

    # parser.add_argument(
    #     "--rerank-k",
    #     type=int,
    #     default=5,
    #     help="Number of top-k candidates for prototype reranking"
    # )

    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input folder containing species subfolders with videos"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to output directory to save processed videos"
    )
    parser.add_argument(
        "--yolo-model",
        type=str,
        default="../runs/bird_yolov8n_combined5/weights/best.pt",
        help="Path to YOLO model weights"
    )
    parser.add_argument(
        "--species-model",
        type=str,
        default="../../species_classification-2.0.pth",
        help="Path to species classifier weights"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device to run inference on (cuda/cpu)"
    )
    parser.add_argument(
        "--idx-to-class",
        type=str,
        default="../../idx_to_class.json",
        help="Path to idx_to_class.json mapping file"
    )
    parser.add_argument(
        "--slice-height",
        type=int,
        default=640,
        help="Height of each slice for SAHI (default: 640)"
    )
    parser.add_argument(
        "--slice-width",
        type=int,
        default=640,
        help="Width of each slice for SAHI (default: 640)"
    )
    parser.add_argument(
        "--overlap-ratio",
        type=float,
        default=0.2,
        help="Overlap ratio between slices for SAHI (default: 0.2)"
    )
    parser.add_argument(
        "--conf-threshold",
        type=float,
        default=0.25,
        help="Confidence threshold for detections (default: 0.25)"
    )
    
    args = parser.parse_args()
    
    # Validate input folder exists
    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input folder not found: {args.input}")
    
    if not os.path.isdir(args.input):
        raise ValueError(f"Input path must be a directory: {args.input}")
    
    # Find all video files
    print("=" * 60)
    print("BIRD DETECTION & SPECIES CLASSIFICATION PIPELINE")
    print("Using SAHI + Kalman Tracking by Default")
    print("=" * 60)
    print(f"Scanning for videos in: {args.input}")
    print("-" * 60)
    
    video_files = find_video_files(args.input)
    
    if not video_files:
        print("No video files found!")
        return
    
    print(f"Found {len(video_files)} videos across {len(set(v[1] for v in video_files))} species")
    print("=" * 60)
    
    # Load models and class mapping once for all videos
    device = torch.device(args.device)
    print(f"Device: {args.device}")
    
    # Load idx to class mapping
    if not os.path.exists(args.idx_to_class):
        raise FileNotFoundError(f"idx_to_class.json not found: {args.idx_to_class}")
    idx_to_class = load_idx_to_class(args.idx_to_class)
    print(f"Loaded {len(idx_to_class)} species classes")
    
    # Load SAHI model
    sahi_model = load_sahi_model(
        args.yolo_model, 
        confidence_threshold=args.conf_threshold, 
        device=args.device
    )
    print(f"SAHI parameters: slice_size={args.slice_height}x{args.slice_width}, overlap={args.overlap_ratio}")
    
    # Load species classifier
    species_model = load_species_classifier(
        args.species_model, 
        num_classes=len(idx_to_class), 
        device=args.device
    )
    preprocess = get_preprocess_transforms()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Process each video
    for idx, (video_path, species_name, video_filename) in enumerate(video_files, 1):
        print(f"\n{'='*60}")
        print(f"Processing video {idx}/{len(video_files)}")
        print(f"Species: {species_name}")
        print(f"File: {video_filename}")
        print(f"{'='*60}")
        
        # Create species subfolder in output
        species_output_dir = os.path.join(args.output, species_name)
        os.makedirs(species_output_dir, exist_ok=True)
        
        # Generate output path
        output_filename = f"{os.path.splitext(video_filename)[0]}_processed.mp4"
        output_path = os.path.join(species_output_dir, output_filename)
        
        try:
            # Call process_video with correct arguments (no use_sahi, etc.)
            process_video(
                input_path=video_path,
                output_path=output_path,
                sahi_model=sahi_model,
                species_model=species_model,
                preprocess=preprocess,
                device=device,
                idx_to_class=idx_to_class,
                slice_height=args.slice_height,
                slice_width=args.slice_width,
                overlap_ratio=args.overlap_ratio
            )
        except Exception as e:
            print(f"\nERROR processing {video_filename}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Processed {len(video_files)} videos")
    print(f"Output directory: {args.output}")


if __name__ == "__main__":
    main()
