import os
import cv2
import time
import numpy as np
import torch
from ultralytics import YOLO

def train_yolo_model():
    """Train YOLOv8 model on bird dataset"""
    print("Starting YOLO training...")
    
    # Clear GPU cache first
    torch.cuda.empty_cache()
    
    # Load pretrained YOLOv8 nano model
    model = YOLO("yolov8n.pt")
    
    # Train with metrics
    model.train(
        data="combined-birds/data.yaml",
        epochs=20,
        imgsz=640,
        batch=16,
        project="runs",
        name="bird_yolov8n_combined",
        workers=4,
        cache=True,              # Cache images for faster training
        device=0,
        amp=True,                # mixed precision training
        patience=20,             # Early stopping
        optimizer='AdamW',       # AdamW optimization
        lr0=0.001,               # Initial learning rate
        lrf=0.01,                # Final learning rate factor
        momentum=0.937,          # Momentum for SGD-like behavior
        weight_decay=0.0005,     # L2 regularization
        warmup_epochs=3,         # Gradual warmup
        warmup_momentum=0.8,     # Starting momentum during warmup
        box=7.5,                 # Box loss gain
        cls=0.5,                 # Class loss gain
        dfl=1.5,                 # Distribution focal loss gain
        hsv_h=0.015,             # HSV-Hue augmentation
        hsv_s=0.7,               # HSV-Saturation augmentation
        hsv_v=0.4,               # HSV-Value augmentation
        degrees=10.0,            # Rotation augmentation
        translate=0.1,           # Translation augmentation
        scale=0.5,               # Scale augmentation
        shear=0.0,               # Shear augmentation
        perspective=0.0,         # Perspective augmentation
        flipud=0.0,              # Vertical flip probability
        fliplr=0.5,              # Horizontal flip probability
        mosaic=1.0,              # Mosaic augmentation probability
        mixup=0.1,               # Mixup augmentation probability
        copy_paste=0.1,          # Copy-paste augmentation probability
        close_mosaic=10          # Disable mosaic in last N epochs
    )
    
    print("Training complete!")
    return model

def evaluate_model(model_path, data_yaml):
    """Evaluate trained YOLO model"""
    print(f"Evaluating model: {model_path}")
    
    model = YOLO(model_path)
    
    metrics = model.val(
        data=data_yaml,
        split="val"
    )
    
    precision = metrics.box.mp
    recall = metrics.box.mr
    map50 = metrics.box.map50
    map5095 = metrics.box.map
    
    print(f"""
            YOLOv8 Bird Detection Results
                
            ===============================
                
            Precision     : {precision:.3f}
            Recall        : {recall:.3f}
            mAP@50        : {map50:.3f}
            mAP@50-95     : {map5095:.3f}
            """)
    
    return metrics

def measure_inference_speed(model, test_dir):
    """Measure inference speed on test images"""
    print("Measuring inference speed...")
    
    times = []
    
    # Warm-up GPU
    for _ in range(10):
        dummy = np.zeros((224, 224, 3), dtype=np.uint8)
        _ = model(dummy, verbose=False)
    
    for img_name in os.listdir(test_dir):
        img = cv2.imread(os.path.join(test_dir, img_name))
        
        start = time.time()
        _ = model(img, verbose=False)
        times.append(time.time() - start)
    
    avg_time = sum(times) / len(times)
    fps = 1 / avg_time
    
    print(f"Avg inference time: {avg_time:.6f}s")
    print(f"FPS ceiling: {fps:.2f}")

def run_and_save(
    model,
    input_dir,
    output_dir,
    max_images=10,
    conf=0.25,
    iou=0.45,
    max_det=300
):
    """Run inference and save results"""
    os.makedirs(output_dir, exist_ok=True)
    label_dir = os.path.join(output_dir, "labels")
    os.makedirs(label_dir, exist_ok=True)
    
    images = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    
    for img_name in images[:max_images]:
        img_path = os.path.join(input_dir, img_name)
        
        results = model(
            img_path,
            conf=conf,
            iou=iou,
            max_det=max_det,
            verbose=False
        )
        
        r = results[0]
        
        # Save image with bounding boxes
        r.save(filename=os.path.join(output_dir, img_name))
        
        # Save predicted boxes to TXT
        txt_path = os.path.join(
            label_dir, img_name.rsplit(".", 1)[0] + ".txt"
        )
        
        h, w = r.orig_shape
        
        with open(txt_path, "w") as f:
            if r.boxes is None:
                continue
            
            for box in r.boxes:
                cls = int(box.cls.item())
                conf_score = float(box.conf.item())
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                xc = ((x1 + x2) / 2) / w
                yc = ((y1 + y2) / 2) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                
                f.write(
                    f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f} {conf_score:.4f}\n"
                )

def test_on_images(model_path, test_dir, output_dir):
    """Run predictions on test dataset"""
    print("Running predictions on test images...")
    
    model = YOLO(model_path)
    
    os.makedirs(output_dir, exist_ok=True)
    
    run_and_save(
        model=model,
        input_dir=test_dir,
        output_dir=output_dir,
        max_images=20,
        conf=0.30,     # detection confidence threshold
        iou=0.6,       # NMS IoU threshold
        max_det=20     # allow many birds per image
    )
    
    print("Saved detection images to:", output_dir)

if __name__ == "__main__":
    # Train model
    model = train_yolo_model()
    
    # Evaluate model
    best_model_path = "runs/bird_yolov8n_combined/weights/best.pt"
    evaluate_model(best_model_path, "../combined-birds/data.yaml")
    
    # Measure inference speed
    test_dir = "../another-bird-dataset/test/images"
    model = YOLO(best_model_path)
    measure_inference_speed(model, test_dir)
    
    # Test on images
    output_dir = "yolo_test_detections"
    test_on_images(best_model_path, test_dir, output_dir)
    
    print("\nYOLO training and evaluation complete!")