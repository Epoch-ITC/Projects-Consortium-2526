import cv2
import numpy as np
from scipy.ndimage import gaussian_filter


def generate_heatmap_from_detections(detections_list, frame_shape):
    """
    Generate a heatmap from a list of bounding box detections
    
    Args:
        detections_list: List of bounding boxes, each as (x1, y1, x2, y2)
        frame_shape: Tuple of (height, width) for the video frame
    
    Returns:
        heatmap: 2D numpy array with detection density
    """
    height, width = frame_shape
    heatmap = np.zeros((height, width), dtype=np.float32)
    
    for detection in detections_list:
        x1, y1, x2, y2 = detection
        
        # Ensure coordinates are within bounds
        x1 = max(0, min(int(x1), width - 1))
        x2 = max(0, min(int(x2), width - 1))
        y1 = max(0, min(int(y1), height - 1))
        y2 = max(0, min(int(y2), height - 1))
        
        # Increment heatmap in the bounding box region
        if x2 > x1 and y2 > y1:
            heatmap[y1:y2+1, x1:x2+1] += 1
    
    return heatmap


def normalize_and_smooth_heatmap(heatmap, sigma=5):
    """
    Normalize and apply Gaussian smoothing to heatmap
    
    Args:
        heatmap: 2D numpy array with detection counts
        sigma: Standard deviation for Gaussian filter
    
    Returns:
        smoothed_heatmap: Normalized and smoothed heatmap (0-1 range)
    """
    # Normalize to 0-1 range
    if heatmap.max() > 0:
        normalized = heatmap / heatmap.max()
    else:
        normalized = heatmap
    
    # Apply Gaussian smoothing
    smoothed = gaussian_filter(normalized, sigma=sigma)
    
    return smoothed


def apply_heatmap_colormap(heatmap, colormap=cv2.COLORMAP_JET):
    """
    Apply color mapping to heatmap for visualization
    
    Args:
        heatmap: 2D numpy array (normalized 0-1)
        colormap: OpenCV colormap (default: COLORMAP_JET)
    
    Returns:
        colored_heatmap: BGR image with color-coded heatmap
    """
    # Convert to 0-255 range
    heatmap_uint8 = (heatmap * 255).astype(np.uint8)
    
    # Apply colormap
    colored = cv2.applyColorMap(heatmap_uint8, colormap)
    
    return colored


def overlay_heatmap_on_frame(frame, heatmap, alpha=0.4):
    """
    Overlay heatmap on a video frame
    
    Args:
        frame: BGR video frame
        heatmap: 2D numpy array (normalized 0-1)
        alpha: Transparency of heatmap overlay (0-1)
    
    Returns:
        overlay: Frame with heatmap overlay
    """
    # Ensure heatmap matches frame size
    if heatmap.shape[:2] != frame.shape[:2]:
        heatmap = cv2.resize(heatmap, (frame.shape[1], frame.shape[0]))
    
    # Apply colormap to heatmap
    heatmap_colored = apply_heatmap_colormap(heatmap)
    
    # Blend with original frame
    overlay = cv2.addWeighted(frame, 1 - alpha, heatmap_colored, alpha, 0)
    
    return overlay


def compute_video_heatmap(video_path, yolo_model, sample_rate=1):
    """
    Compute average detection heatmap for a single video
    
    Args:
        video_path: Path to video file
        yolo_model: YOLO detection model
        sample_rate: Process every Nth frame (default: 1 = all frames)
    
    Returns:
        heatmap: 2D numpy array with detection density
        frame_shape: Tuple of (height, width) of video
        total_detections: Number of detections found
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_shape = (height, width)
    
    # Initialize heatmap
    heatmap = np.zeros(frame_shape, dtype=np.float32)
    
    frame_count = 0
    total_detections = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Sample frames
        if frame_count % sample_rate != 0:
            frame_count += 1
            continue
        
        # Run YOLO detection
        results = yolo_model(frame, verbose=False)
        
        # Accumulate detections
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    
                    # Ensure coordinates are within bounds
                    x1 = max(0, min(x1, width - 1))
                    x2 = max(0, min(x2, width - 1))
                    y1 = max(0, min(y1, height - 1))
                    y2 = max(0, min(y2, height - 1))
                    
                    # Add to heatmap
                    if x2 > x1 and y2 > y1:
                        heatmap[y1:y2+1, x1:x2+1] += 1
                        total_detections += 1
        
        frame_count += 1
    
    cap.release()
    
    return heatmap, frame_shape, total_detections
