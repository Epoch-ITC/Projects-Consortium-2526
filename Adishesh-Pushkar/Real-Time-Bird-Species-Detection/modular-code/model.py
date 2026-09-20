"""
Model Module
This module handles YOLO bird detection and species classification model loading and inference.
"""

import torch
import torch.nn as nn
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_b3
from ultralytics import YOLO


class BirdDetectionModel:
    """Handles YOLO model for bird detection."""
    
    def __init__(self, model_path="yolo11n.pt", device=None):
        """
        Initialize YOLO bird detection model.
        
        Args:
            model_path: Path to YOLO model weights
            device: Computation device ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Loading YOLO model on device: {self.device}")
        self.model = YOLO(model_path)
        print(f"YOLO model loaded from: {model_path}")
    
    def detect(self, frame, conf_threshold=0.25, verbose=False):
        """
        Detect birds in a frame.
        
        Args:
            frame: Input image (numpy array)
            conf_threshold: Confidence threshold for detections
            verbose: Whether to print detection info
            
        Returns:
            YOLO results object containing detections
        """
        results = self.model(frame, conf=conf_threshold, verbose=verbose)
        return results
    
    def get_detections(self, results):
        """
        Extract detection boxes from YOLO results.
        
        Args:
            results: YOLO results object
            
        Returns:
            list: List of detections [(x1, y1, x2, y2, conf), ...]
        """
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = box.conf.item()
                    detections.append((x1, y1, x2, y2, conf))
        return detections


class SpeciesClassifier:
    """Handles EfficientNet model for bird species classification."""
    
    def __init__(self, model_path, num_classes=500, device=None):
        """
        Initialize species classification model.
        
        Args:
            model_path: Path to trained species classifier weights
            num_classes: Number of bird species classes
            device: Computation device ('cuda', 'cpu', or None for auto-detect)
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.num_classes = num_classes
        
        print(f"Loading species classifier on device: {self.device}")
        
        # Load EfficientNet-B3 architecture
        self.model = efficientnet_b3(weights=None)
        
        # Modify classifier head for bird species
        in_features = self.model.classifier[1].in_features
        self.model.classifier[1] = nn.Linear(in_features, num_classes)
        
        # Load trained weights
        self.model.load_state_dict(
            torch.load(model_path, map_location=self.device)
        )
        
        # Move to device and set to evaluation mode
        self.model.to(self.device)
        self.model.eval()
        
        # Define preprocessing transforms
        self.preprocess = transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
        print(f"Species classifier loaded successfully!")
        print(f"Model: EfficientNet-B3")
        print(f"Classes: {num_classes}")
    
    def classify(self, image):
        """
        Classify a bird crop into species.
        
        Args:
            image: PIL Image or numpy array (H, W, C) of bird crop
            
        Returns:
            tuple: (class_id, confidence) - Predicted species class and confidence
        """
        # Convert numpy to PIL if needed
        if isinstance(image, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Preprocess
        input_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            outputs = self.model(input_tensor)
            probabilities = torch.softmax(outputs, dim=1)
            confidence, predicted_class = torch.max(probabilities, 1)
        
        return predicted_class.item(), confidence.item()
    
        # ========================================================
        # OPTIONAL: TOP-10 REFINED INFERENCE (COMMENTED OUT)
        # ========================================================
        #
        # with torch.no_grad():
        #     outputs = self.model(input_tensor)
        #
        #     predicted_class, confidence, top10_classes = \
        #         self.refined_topk_prediction(outputs, k=10)
        #
        # return predicted_class, confidence

    
    # ============================================================
    # OPTIONAL: TOP-K REFINED INFERENCE (COMMENTED OUT)
    # ============================================================
    #
    # def refined_topk_prediction(self, logits, k=10):
    #     """
    #     Refined inference strategy:
    #     1. Select Top-K classes
    #     2. Re-normalize probabilities within Top-K
    #     3. Select final Top-1 from refined distribution
    #
    #     This is useful when Top-K accuracy is much higher than Top-1,
    #     indicating class ambiguity rather than feature failure.
    #
    #     Args:
    #         logits (torch.Tensor): Raw model outputs (1 x num_classes)
    #         k (int): Number of top classes to consider
    #
    #     Returns:
    #         final_class (int)
    #         final_conf (float)
    #         topk_classes (list[int])
    #     """
    #
    #     probs = torch.softmax(logits, dim=1)
    #
    #     topk_vals, topk_idx = torch.topk(probs, k=k, dim=1)
    #
    #     # Re-normalize within Top-K
    #     refined_probs = topk_vals / topk_vals.sum(dim=1, keepdim=True)
    #
    #     best_idx = torch.argmax(refined_probs, dim=1)
    #
    #     final_class = topk_idx[0, best_idx].item()
    #     final_conf = refined_probs[0, best_idx].item()
    #
    #     return final_class, final_conf, topk_idx.squeeze(0).tolist()



class BirdDetectionPipeline:
    """Combined pipeline for bird detection and species classification."""
    
    def __init__(self, yolo_model_path, species_model_path, num_classes=500, device=None):
        """
        Initialize the complete bird detection and classification pipeline.
        
        Args:
            yolo_model_path: Path to YOLO model weights
            species_model_path: Path to species classifier weights
            num_classes: Number of bird species classes
            device: Computation device
        """
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Initialize models
        self.detector = BirdDetectionModel(yolo_model_path, device=self.device)
        self.classifier = SpeciesClassifier(species_model_path, num_classes, device=self.device)
        
        print("\n" + "="*60)
        print("BIRD DETECTION PIPELINE INITIALIZED")
        print("="*60)
    
    def process_frame(self, frame, detect_conf=0.25, classify_threshold=0.0):
        """
        Process a single frame: detect birds and classify species.
        
        Args:
            frame: Input frame (numpy array)
            detect_conf: Confidence threshold for bird detection
            classify_threshold: Minimum confidence threshold for species classification
            
        Returns:
            list: List of detections with species info [(x1, y1, x2, y2, det_conf, species_id, species_conf), ...]
        """
        # Step 1: Detect birds
        yolo_results = self.detector.detect(frame, conf_threshold=detect_conf, verbose=False)
        
        # Step 2: Classify each detected bird
        detections_with_species = []
        
        for result in yolo_results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    det_conf = box.conf.item()
                    
                    # Crop bird region
                    bird_crop = frame[y1:y2, x1:x2]
                    
                    if bird_crop.size > 0:
                        # Classify species
                        species_id, species_conf = self.classifier.classify(bird_crop)
                        
                        if species_conf >= classify_threshold:
                            detections_with_species.append(
                                (x1, y1, x2, y2, det_conf, species_id, species_conf)
                            )
        
        return detections_with_species
    
    def annotate_frame(self, frame, detections, show_species=True, show_detection_conf=False):
        """
        Draw bounding boxes and labels on frame.
        
        Args:
            frame: Input frame to annotate
            detections: List of detections from process_frame()
            show_species: Whether to show species classification
            show_detection_conf: Whether to show detection confidence
            
        Returns:
            numpy.ndarray: Annotated frame
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            if len(detection) == 7:  # With species classification
                x1, y1, x2, y2, det_conf, species_id, species_conf = detection
                
                # Draw bounding box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Create label
                if show_species:
                    label = f"Species {species_id}: {species_conf:.2%}"
                    if show_detection_conf:
                        label += f" (Det: {det_conf:.2%})"
                else:
                    label = f"Bird: {det_conf:.2%}"
                
                # Draw label background
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                )
                cv2.rectangle(
                    annotated_frame, 
                    (x1, y1 - label_h - 10), 
                    (x1 + label_w, y1), 
                    (0, 255, 0), 
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    annotated_frame, 
                    label, 
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (0, 0, 0), 
                    2
                )
            else:  # Detection only (backward compatibility)
                x1, y1, x2, y2, conf = detection
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"Bird: {conf:.2%}"
                cv2.putText(
                    annotated_frame, 
                    label, 
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (0, 255, 0), 
                    2
                )
        
        return annotated_frame


# Example usage
if __name__ == "__main__":
    # Initialize pipeline
    pipeline = BirdDetectionPipeline(
        yolo_model_path="yolo11n.pt",
        species_model_path="models/species_classifier.pth",
        num_classes=500
    )
    
    # Test on a single image
    test_image = cv2.imread("test_image.jpg")
    if test_image is not None:
        detections = pipeline.process_frame(test_image)
        annotated = pipeline.annotate_frame(test_image, detections)
        cv2.imwrite("test_output.jpg", annotated)
        print(f"Detected {len(detections)} birds")
