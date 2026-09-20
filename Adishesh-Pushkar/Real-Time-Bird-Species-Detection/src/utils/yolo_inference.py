import argparse
import os
import cv2
import time
from ultralytics import YOLO
import numpy as np
import sys

# Add current directory to path so we can import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)


from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
from kalman_filter import KalmanFilter

class Track:
    def __init__(self, track_id, initial_pos):
        self.track_id = track_id
        # Increase u_x, u_y for faster convergence on initial velocity
        # Decrease measurement noise (x_std_meas, y_std_meas) to trust the measurement more (responsive to random motion)
        self.kf = KalmanFilter(dt=1.0/30.0, u_x=1.0, u_y=1.0, std_acc=5.0, x_std_meas=0.1, y_std_meas=0.1) 
        self.kf.x[0] = initial_pos[0]
        self.kf.x[1] = initial_pos[1]
        self.prediction = np.array(initial_pos)
        self.age = 0
        self.hits = 1
        self.hit_streak = 1
        self.time_since_update = 0
        self.box_size = (0, 0) # width, height

    def update(self, pos, size):
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1
        self.kf.update(np.array(pos).reshape(2, 1))
        self.box_size = size

    def predict(self):
        self.kf.predict()
        self.age += 1
        if(self.time_since_update > 0):
            self.hit_streak = 0
        self.time_since_update += 1
        self.prediction = self.kf.x[:2].flatten()
        return self.prediction


def process_video(input_path, output_path, model, conf_threshold=0.25, iou_threshold=0.9):
    """
    Process video with YOLO bird detection
    
    Args:
        input_path: Path to input video
        output_path: Path to save output video
        model: YOLO detection model
        conf_threshold: Confidence threshold for detections
        iou_threshold: IOU threshold for NMS
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
    print("\nProcessing video...")
    print("-" * 60)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"Created output directory: {output_dir}")
    
    # Try multiple codec options
    # mp4v works on most systems, XVID is a fallback
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Check if video writer opened successfully
    if not out.isOpened():
        print("Warning: mp4v codec failed, trying XVID...")
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        # Change extension to .avi for XVID
        output_path_avi = output_path.rsplit('.', 1)[0] + '.avi'
        out = cv2.VideoWriter(output_path_avi, fourcc, fps, (width, height))
        output_path = output_path_avi
        
        if not out.isOpened():
            raise RuntimeError("Failed to open video writer with any codec")
    
    print(f"Video writer initialized: {output_path}")
    
    frame_count = 0
    total_inference_time = 0
    total_detections = 0
    
    # Tracking variables
    tracks = []
    track_id_counter = 0
    max_age = 60  # Increased to keep tracks longer
    min_hits = 1  # Show tracks sooner
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            start_time = time.time()
            
            # Run SAHI sliced inference
            result = get_sliced_prediction(
                frame,
                model,
                slice_height=640,
                slice_width=640,
                overlap_height_ratio=0.2,
                overlap_width_ratio=0.2,
                postprocess_type="NMS",
                postprocess_match_metric="IOS",
                postprocess_match_threshold=0.5,
                verbose=0
            )
            
            # Get detections
            detections = []
            for object_prediction in result.object_prediction_list:
                bbox = object_prediction.bbox
                x1, y1, x2, y2 = int(bbox.minx), int(bbox.miny), int(bbox.maxx), int(bbox.maxy)
                conf = object_prediction.score.value
                
                # Check confidence again if needed (AutoDetectionModel handles it mostly)
                if conf < conf_threshold:
                    continue

                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width = x2 - x1
                height = y2 - y1
                detections.append({'center': (center_x, center_y), 'size': (width, height), 'box': (x1, y1, x2, y2), 'conf': conf})
            
            # Predict new locations of existing tracks
            for track in tracks:
                track.predict()
            
            # Match detections to tracks
            # Simple Euclidean distance matching
            assigned_saved = []  # Indices of matched tracks
            assigned_detections = []  # Indices of matched detections
            
            if len(tracks) > 0 and len(detections) > 0:
                dists = np.zeros((len(tracks), len(detections)))
                for i, track in enumerate(tracks):
                    for j, det in enumerate(detections):
                        d = np.linalg.norm(track.prediction - np.array(det['center']))
                        dists[i, j] = d
                
                # Assign tracks to detections
                # Simple greedy assignment
                rows, cols = dists.shape
                # Set a pixel threshold distance for matching
                dist_threshold = 100  
                
                # Indices with smallest distances
                
                # Very simple greedy matching
                
                matched_indices = []
                if rows > 0 and cols > 0:
                     # Flatten and sort
                     indices = np.argsort(dists, axis=None)
                     
                     for idx in indices:
                         r, c = np.unravel_index(idx, dists.shape)
                         dist = dists[r, c]
                         
                         if r not in assigned_saved and c not in assigned_detections and dist < dist_threshold:
                             assigned_saved.append(r)
                             assigned_detections.append(c)
                             tracks[r].update(detections[c]['center'], detections[c]['size'])
            
            # Create new tracks for unmatched detections
            for i, det in enumerate(detections):
                if i not in assigned_detections:
                    new_track = Track(track_id_counter, det['center'])
                    new_track.box_size = det['size']
                    tracks.append(new_track)
                    track_id_counter += 1
            
            # Remove old tracks
            tracks = [t for t in tracks if t.time_since_update < max_age]
            
            # Draw YOLO detections
            for det in detections:
                x1, y1, x2, y2 = det['box']
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"YOLO: {det['conf']:.2f}"
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                total_detections += 1

            # Draw Kalman tracks
            for track in tracks:
                if track.time_since_update < 5 and track.hits >= min_hits: 
                    # Only draw active tracks
                    cx, cy = map(int, track.prediction)
                    w, h = map(int, track.box_size)
                    x1 = int(cx - w/2)
                    y1 = int(cy - h/2)
                    x2 = int(cx + w/2)
                    y2 = int(cy + h/2)
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    
                    label = f"ID: {track.track_id}"
                    cv2.putText(frame, label, (x1, y1 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                    # # Draw velocity vector
                    # vx, vy = track.kf.x[2], track.kf.x[3]
                    # end_point = (int(cx + vx*10), int(cy + vy*10))
                    # cv2.arrowedLine(frame, (cx, cy), end_point, (255, 0, 0), 2)
            
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
                      f"Avg FPS: {avg_fps:.2f}")
    
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
    print(f"Average inference time: {avg_inference_time*1000:.2f} ms/frame")
    print(f"Average processing FPS: {avg_fps:.2f}")
    print(f"\nOutput saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="YOLO Bird Detection on Single Video"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input video file"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to save output video"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="../runs/bird_yolov8n_combined5/weights/best.pt",
        help="Path to YOLO model weights"
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Confidence threshold (default: 0.25)"
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.9,
        help="IOU threshold for NMS (default: 0.9)"
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input video not found: {args.input}")
    
    # Validate model file exists
    if not os.path.exists(args.model):
        raise FileNotFoundError(f"Model file not found: {args.model}")
    
    print("=" * 60)
    print("YOLO BIRD DETECTION")
    print("=" * 60)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Model: {args.model}")
    print(f"Confidence threshold: {args.conf}")
    print(f"IOU threshold: {args.iou}")
    
    # Initialize SAHI model
    print("Initializing SAHI model...")
    detection_model = AutoDetectionModel.from_pretrained(
        model_type='yolov8',
        model_path=args.model,
        confidence_threshold=args.conf,
        device="cuda:0"
    )
    
    # Process video
    process_video(args.input, args.output, detection_model, args.conf, args.iou)


if __name__ == "__main__":
    main()