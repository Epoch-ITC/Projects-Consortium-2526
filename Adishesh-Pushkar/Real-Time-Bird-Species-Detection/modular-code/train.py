<<<<<<< Updated upstream
"""
Training Module
This module handles training YOLO bird detection models and evaluating their performance.
"""

import os
import yaml
import torch
import cv2
import time
import numpy as np
import argparse
from ultralytics import YOLO


class YOLOTrainer:
    """Handles YOLO model training and evaluation."""
    
    def __init__(self, data_path="combined-birds", output_dir="runs"):
        """
        Initialize YOLO trainer.
        
        Args:
            data_path: Path to the dataset directory
            output_dir: Directory to save training outputs
        """
        self.data_path = data_path
        self.output_dir = output_dir
        self.data_yaml_path = os.path.join(data_path, "data.yaml")
        self.model = None
    
    def create_data_yaml(self):
        """
        Create data.yaml configuration file for YOLO training.
        Automatically detects number of classes from labels.
        
        Returns:
            int: Number of classes detected
        """
        # Get all unique class IDs from training labels
        class_ids = set()
        labels_dir = os.path.join(self.data_path, "train", "labels")
        
        if not os.path.exists(labels_dir):
            raise FileNotFoundError(f"Labels directory not found: {labels_dir}")
        
        print(f"Scanning labels in: {labels_dir}")
        
        for label_file in os.listdir(labels_dir):
            if not label_file.endswith('.txt'):
                continue
            
            with open(os.path.join(labels_dir, label_file), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        class_ids.add(class_id)
        
        num_classes = max(class_ids) + 1 if class_ids else 1
        
        # Create data.yaml configuration
        data_config = {
            'path': os.path.abspath(self.data_path),
            'train': 'train/images',
            'val': 'valid/images',
            'nc': num_classes,
            'names': list(range(num_classes))  # Simple numeric class names
        }
        
        # Write YAML file
        with open(self.data_yaml_path, 'w') as f:
            yaml.dump(data_config, f, default_flow_style=False)
        
        print(f"✓ data.yaml created with {num_classes} classes")
        print(f"  Path: {self.data_yaml_path}")
        
        return num_classes
    
    def train(
        self,
        model_name="yolov8n.pt",
        epochs=20,
        batch=16,
        imgsz=640,
        patience=20,
        lr0=0.001,
        name="bird_detection",
        device=0,
        cache=True,
        workers=4,
        **kwargs
    ):
        """
        Train YOLO model for bird detection.
        
        Args:
            model_name: Pretrained model to start from (e.g., 'yolov8n.pt', 'yolo11n.pt')
            epochs: Number of training epochs
            batch: Batch size
            imgsz: Input image size
            patience: Early stopping patience
            lr0: Initial learning rate
            name: Training run name
            device: Device to use (0 for GPU, 'cpu' for CPU)
            cache: Cache images for faster training
            workers: Number of data loader workers
            **kwargs: Additional YOLO training arguments
        
        Returns:
            YOLO: Trained model
        """
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("\n" + "="*60)
        print("STARTING YOLO TRAINING")
        print("="*60)
        print(f"Model: {model_name}")
        print(f"Dataset: {self.data_yaml_path}")
        print(f"Epochs: {epochs}")
        print(f"Batch size: {batch}")
        print(f"Image size: {imgsz}")
        
        # Load pretrained model
        self.model = YOLO(model_name)
        
        # Train the model
        results = self.model.train(
            data=self.data_yaml_path,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            project=self.output_dir,
            name=name,
            patience=patience,
            lr0=lr0,
            workers=workers,
            cache=cache,
            device=device,
            amp=True,  # Automatic Mixed Precision
            optimizer='AdamW',
            **kwargs
        )
        
        print("\n" + "="*60)
        print("TRAINING COMPLETED")
        print("="*60)
        
        # Get the path to best weights
        best_weights = os.path.join(self.output_dir, name, "weights", "best.pt")
        print(f"Best weights saved to: {best_weights}")
        
        return results
    
    def load_model(self, model_path):
        """
        Load a trained YOLO model.
        
        Args:
            model_path: Path to model weights (.pt file)
        """
        print(f"Loading model from: {model_path}")
        self.model = YOLO(model_path)
        print("✓ Model loaded successfully")
    
    def validate(self, split="val"):
        """
        Validate model on validation set.
        
        Args:
            split: Dataset split to validate on ('val' or 'test')
            
        Returns:
            dict: Validation metrics
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        print("\n" + "="*60)
        print("VALIDATING MODEL")
        print("="*60)
        
        metrics = self.model.val(
            data=self.data_yaml_path,
            split=split
        )
        
        # Extract key metrics
        precision = metrics.box.mp
        recall = metrics.box.mr
        map50 = metrics.box.map50
        map5095 = metrics.box.map
        
        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        print(f"Precision     : {precision:.3f}")
        print(f"Recall        : {recall:.3f}")
        print(f"mAP@50        : {map50:.3f}")
        print(f"mAP@50-95     : {map5095:.3f}")
        print("="*60)
        
        return {
            'precision': precision,
            'recall': recall,
            'map50': map50,
            'map5095': map5095
        }
    
    def benchmark_fps(self, test_dir, num_images=None, warmup=10):
        """
        Benchmark model inference speed.
        
        Args:
            test_dir: Directory containing test images
            num_images: Number of images to test (None for all)
            warmup: Number of warmup iterations
            
        Returns:
            dict: Performance metrics
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        print("\n" + "="*60)
        print("BENCHMARKING INFERENCE SPEED")
        print("="*60)
        
        # Get test images
        images = [
            f for f in os.listdir(test_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        
        if not images:
            raise ValueError(f"No images found in {test_dir}")
        
        if num_images:
            images = images[:num_images]
        
        # Warm-up GPU
        print(f"Warming up GPU with {warmup} iterations...")
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(warmup):
            _ = self.model(dummy, verbose=False)
        
        # Benchmark
        times = []
        print(f"Testing on {len(images)} images...")
        
        for img_name in images:
            img_path = os.path.join(test_dir, img_name)
            img = cv2.imread(img_path)
            
            start = time.time()
            _ = self.model(img, verbose=False)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        fps = 1 / avg_time
        
        print(f"\nAverage inference time: {avg_time*1000:.2f} ms")
        print(f"FPS ceiling: {fps:.2f}")
        print("="*60)
        
        return {
            'avg_time': avg_time,
            'fps': fps,
            'times': times
        }
    
    def test_and_save(
        self,
        test_dir,
        output_dir,
        max_images=None,
        conf=0.25,
        iou=0.45,
        max_det=300,
        save_labels=True
    ):
        """
        Run inference on test images and save results.
        
        Args:
            test_dir: Directory containing test images
            output_dir: Directory to save detection results
            max_images: Maximum number of images to process
            conf: Confidence threshold
            iou: IoU threshold for NMS
            max_det: Maximum detections per image
            save_labels: Whether to save label files
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        os.makedirs(output_dir, exist_ok=True)
        
        if save_labels:
            label_dir = os.path.join(output_dir, "labels")
            os.makedirs(label_dir, exist_ok=True)
        
        # Get test images
        images = sorted([
            f for f in os.listdir(test_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if max_images:
            images = images[:max_images]
        
        print(f"\nProcessing {len(images)} test images...")
        
        for i, img_name in enumerate(images, 1):
            img_path = os.path.join(test_dir, img_name)
            
            # Run inference
            results = self.model(
                img_path,
                conf=conf,
                iou=iou,
                max_det=max_det,
                verbose=False
            )
            
            r = results[0]
            
            # Save annotated image
            r.save(filename=os.path.join(output_dir, img_name))
            
            # Save labels if requested
            if save_labels and r.boxes is not None:
                txt_path = os.path.join(
                    label_dir,
                    img_name.rsplit('.', 1)[0] + '.txt'
                )
                
                h, w = r.orig_shape
                
                with open(txt_path, 'w') as f:
                    for box in r.boxes:
                        cls = int(box.cls.item())
                        conf_score = float(box.conf.item())
                        
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        # Convert to YOLO format (normalized center coords)
                        xc = ((x1 + x2) / 2) / w
                        yc = ((y1 + y2) / 2) / h
                        bw = (x2 - x1) / w
                        bh = (y2 - y1) / h
                        
                        f.write(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f} {conf_score:.4f}\n")
            
            if i % 10 == 0:
                print(f"  Processed {i}/{len(images)} images")
        
        print(f"\n✓ Results saved to: {output_dir}")


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate YOLO bird detection models"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create data.yaml command
    yaml_parser = subparsers.add_parser('create-yaml', help='Create data.yaml file')
    yaml_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train YOLO model')
    train_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    train_parser.add_argument('--model', default='yolov8n.pt', help='Base model')
    train_parser.add_argument('--epochs', type=int, default=20, help='Training epochs')
    train_parser.add_argument('--batch', type=int, default=16, help='Batch size')
    train_parser.add_argument('--imgsz', type=int, default=640, help='Image size')
    train_parser.add_argument('--name', default='bird_detection', help='Run name')
    train_parser.add_argument('--device', default=0, help='Device (0 for GPU, cpu for CPU)')
    
    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate trained model')
    val_parser.add_argument('model_path', help='Path to trained model weights')
    val_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    val_parser.add_argument('--split', default='val', help='Split to validate on')
    
    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark inference speed')
    bench_parser.add_argument('model_path', help='Path to trained model weights')
    bench_parser.add_argument('test_dir', help='Test images directory')
    bench_parser.add_argument('--num-images', type=int, help='Number of images to test')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run inference on test images')
    test_parser.add_argument('model_path', help='Path to trained model weights')
    test_parser.add_argument('test_dir', help='Test images directory')
    test_parser.add_argument('output_dir', help='Output directory')
    test_parser.add_argument('--max-images', type=int, help='Max images to process')
    test_parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    test_parser.add_argument('--iou', type=float, default=0.45, help='IoU threshold')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'create-yaml':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.create_data_yaml()
    
    elif args.command == 'train':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.create_data_yaml()  # Auto-create data.yaml
        trainer.train(
            model_name=args.model,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            name=args.name,
            device=args.device
        )
    
    elif args.command == 'validate':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.load_model(args.model_path)
        trainer.validate(split=args.split)
    
    elif args.command == 'benchmark':
        trainer = YOLOTrainer()
        trainer.load_model(args.model_path)
        trainer.benchmark_fps(args.test_dir, num_images=args.num_images)
    
    elif args.command == 'test':
        trainer = YOLOTrainer()
        trainer.load_model(args.model_path)
        trainer.test_and_save(
            test_dir=args.test_dir,
            output_dir=args.output_dir,
            max_images=args.max_images,
            conf=args.conf,
            iou=args.iou
        )


if __name__ == "__main__":
    main()
=======
"""
Training Module
This module handles training YOLO bird detection models and evaluating their performance.
"""

import os
import yaml
import torch
import cv2
import time
import numpy as np
import argparse
from ultralytics import YOLO


class YOLOTrainer:
    """Handles YOLO model training and evaluation."""
    
    def __init__(self, data_path="combined-birds", output_dir="runs"):
        """
        Initialize YOLO trainer.
        
        Args:
            data_path: Path to the dataset directory
            output_dir: Directory to save training outputs
        """
        self.data_path = data_path
        self.output_dir = output_dir
        self.data_yaml_path = os.path.join(data_path, "data.yaml")
        self.model = None
    
    def create_data_yaml(self):
        """
        Create data.yaml configuration file for YOLO training.
        Automatically detects number of classes from labels.
        
        Returns:
            int: Number of classes detected
        """
        # Get all unique class IDs from training labels
        class_ids = set()
        labels_dir = os.path.join(self.data_path, "train", "labels")
        
        if not os.path.exists(labels_dir):
            raise FileNotFoundError(f"Labels directory not found: {labels_dir}")
        
        print(f"Scanning labels in: {labels_dir}")
        
        for label_file in os.listdir(labels_dir):
            if not label_file.endswith('.txt'):
                continue
            
            with open(os.path.join(labels_dir, label_file), 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        class_ids.add(class_id)
        
        num_classes = max(class_ids) + 1 if class_ids else 1
        
        # Create data.yaml configuration
        data_config = {
            'path': os.path.abspath(self.data_path),
            'train': 'train/images',
            'val': 'valid/images',
            'nc': num_classes,
            'names': list(range(num_classes))  # Simple numeric class names
        }
        
        # Write YAML file
        with open(self.data_yaml_path, 'w') as f:
            yaml.dump(data_config, f, default_flow_style=False)
        
        print(f"✓ data.yaml created with {num_classes} classes")
        print(f"  Path: {self.data_yaml_path}")
        
        return num_classes
    
    def train(
        self,
        model_name="yolov8n.pt",
        epochs=20,
        batch=16,
        imgsz=640,
        patience=20,
        lr0=0.001,
        name="bird_detection",
        device=0,
        cache=True,
        workers=4,
        **kwargs
    ):
        """
        Train YOLO model for bird detection.
        
        Args:
            model_name: Pretrained model to start from (e.g., 'yolov8n.pt', 'yolo11n.pt')
            epochs: Number of training epochs
            batch: Batch size
            imgsz: Input image size
            patience: Early stopping patience
            lr0: Initial learning rate
            name: Training run name
            device: Device to use (0 for GPU, 'cpu' for CPU)
            cache: Cache images for faster training
            workers: Number of data loader workers
            **kwargs: Additional YOLO training arguments
        
        Returns:
            YOLO: Trained model
        """
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("\n" + "="*60)
        print("STARTING YOLO TRAINING")
        print("="*60)
        print(f"Model: {model_name}")
        print(f"Dataset: {self.data_yaml_path}")
        print(f"Epochs: {epochs}")
        print(f"Batch size: {batch}")
        print(f"Image size: {imgsz}")
        
        # Load pretrained model
        self.model = YOLO(model_name)
        
        # Train the model
        results = self.model.train(
            data=self.data_yaml_path,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            project=self.output_dir,
            name=name,
            patience=patience,
            lr0=lr0,
            workers=workers,
            cache=cache,
            device=device,
            amp=True,  # Automatic Mixed Precision
            optimizer='AdamW',
            **kwargs
        )
        
        print("\n" + "="*60)
        print("TRAINING COMPLETED")
        print("="*60)
        
        # Get the path to best weights
        best_weights = os.path.join(self.output_dir, name, "weights", "best.pt")
        print(f"Best weights saved to: {best_weights}")
        
        return results
    
    def load_model(self, model_path):
        """
        Load a trained YOLO model.
        
        Args:
            model_path: Path to model weights (.pt file)
        """
        print(f"Loading model from: {model_path}")
        self.model = YOLO(model_path)
        print("✓ Model loaded successfully")
    
    def validate(self, split="val"):
        """
        Validate model on validation set.
        
        Args:
            split: Dataset split to validate on ('val' or 'test')
            
        Returns:
            dict: Validation metrics
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        print("\n" + "="*60)
        print("VALIDATING MODEL")
        print("="*60)
        
        metrics = self.model.val(
            data=self.data_yaml_path,
            split=split
        )
        
        # Extract key metrics
        precision = metrics.box.mp
        recall = metrics.box.mr
        map50 = metrics.box.map50
        map5095 = metrics.box.map
        
        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        print(f"Precision     : {precision:.3f}")
        print(f"Recall        : {recall:.3f}")
        print(f"mAP@50        : {map50:.3f}")
        print(f"mAP@50-95     : {map5095:.3f}")
        print("="*60)
        
        return {
            'precision': precision,
            'recall': recall,
            'map50': map50,
            'map5095': map5095
        }
    
    def benchmark_fps(self, test_dir, num_images=None, warmup=10):
        """
        Benchmark model inference speed.
        
        Args:
            test_dir: Directory containing test images
            num_images: Number of images to test (None for all)
            warmup: Number of warmup iterations
            
        Returns:
            dict: Performance metrics
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        print("\n" + "="*60)
        print("BENCHMARKING INFERENCE SPEED")
        print("="*60)
        
        # Get test images
        images = [
            f for f in os.listdir(test_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]
        
        if not images:
            raise ValueError(f"No images found in {test_dir}")
        
        if num_images:
            images = images[:num_images]
        
        # Warm-up GPU
        print(f"Warming up GPU with {warmup} iterations...")
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        for _ in range(warmup):
            _ = self.model(dummy, verbose=False)
        
        # Benchmark
        times = []
        print(f"Testing on {len(images)} images...")
        
        for img_name in images:
            img_path = os.path.join(test_dir, img_name)
            img = cv2.imread(img_path)
            
            start = time.time()
            _ = self.model(img, verbose=False)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        fps = 1 / avg_time
        
        print(f"\nAverage inference time: {avg_time*1000:.2f} ms")
        print(f"FPS ceiling: {fps:.2f}")
        print("="*60)
        
        return {
            'avg_time': avg_time,
            'fps': fps,
            'times': times
        }
    
    def test_and_save(
        self,
        test_dir,
        output_dir,
        max_images=None,
        conf=0.25,
        iou=0.45,
        max_det=300,
        save_labels=True
    ):
        """
        Run inference on test images and save results.
        
        Args:
            test_dir: Directory containing test images
            output_dir: Directory to save detection results
            max_images: Maximum number of images to process
            conf: Confidence threshold
            iou: IoU threshold for NMS
            max_det: Maximum detections per image
            save_labels: Whether to save label files
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        os.makedirs(output_dir, exist_ok=True)
        
        if save_labels:
            label_dir = os.path.join(output_dir, "labels")
            os.makedirs(label_dir, exist_ok=True)
        
        # Get test images
        images = sorted([
            f for f in os.listdir(test_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ])
        
        if max_images:
            images = images[:max_images]
        
        print(f"\nProcessing {len(images)} test images...")
        
        for i, img_name in enumerate(images, 1):
            img_path = os.path.join(test_dir, img_name)
            
            # Run inference
            results = self.model(
                img_path,
                conf=conf,
                iou=iou,
                max_det=max_det,
                verbose=False
            )
            
            r = results[0]
            
            # Save annotated image
            r.save(filename=os.path.join(output_dir, img_name))
            
            # Save labels if requested
            if save_labels and r.boxes is not None:
                txt_path = os.path.join(
                    label_dir,
                    img_name.rsplit('.', 1)[0] + '.txt'
                )
                
                h, w = r.orig_shape
                
                with open(txt_path, 'w') as f:
                    for box in r.boxes:
                        cls = int(box.cls.item())
                        conf_score = float(box.conf.item())
                        
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        
                        # Convert to YOLO format (normalized center coords)
                        xc = ((x1 + x2) / 2) / w
                        yc = ((y1 + y2) / 2) / h
                        bw = (x2 - x1) / w
                        bh = (y2 - y1) / h
                        
                        f.write(f"{cls} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f} {conf_score:.4f}\n")
            
            if i % 10 == 0:
                print(f"  Processed {i}/{len(images)} images")
        
        print(f"\n✓ Results saved to: {output_dir}")


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Train and evaluate YOLO bird detection models"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Create data.yaml command
    yaml_parser = subparsers.add_parser('create-yaml', help='Create data.yaml file')
    yaml_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train YOLO model')
    train_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    train_parser.add_argument('--model', default='yolov8n.pt', help='Base model')
    train_parser.add_argument('--epochs', type=int, default=20, help='Training epochs')
    train_parser.add_argument('--batch', type=int, default=16, help='Batch size')
    train_parser.add_argument('--imgsz', type=int, default=640, help='Image size')
    train_parser.add_argument('--name', default='bird_detection', help='Run name')
    train_parser.add_argument('--device', default=0, help='Device (0 for GPU, cpu for CPU)')
    
    # Validate command
    val_parser = subparsers.add_parser('validate', help='Validate trained model')
    val_parser.add_argument('model_path', help='Path to trained model weights')
    val_parser.add_argument('--data-path', default='combined-birds', help='Dataset path')
    val_parser.add_argument('--split', default='val', help='Split to validate on')
    
    # Benchmark command
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark inference speed')
    bench_parser.add_argument('model_path', help='Path to trained model weights')
    bench_parser.add_argument('test_dir', help='Test images directory')
    bench_parser.add_argument('--num-images', type=int, help='Number of images to test')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run inference on test images')
    test_parser.add_argument('model_path', help='Path to trained model weights')
    test_parser.add_argument('test_dir', help='Test images directory')
    test_parser.add_argument('output_dir', help='Output directory')
    test_parser.add_argument('--max-images', type=int, help='Max images to process')
    test_parser.add_argument('--conf', type=float, default=0.25, help='Confidence threshold')
    test_parser.add_argument('--iou', type=float, default=0.45, help='IoU threshold')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'create-yaml':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.create_data_yaml()
    
    elif args.command == 'train':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.create_data_yaml()  # Auto-create data.yaml
        trainer.train(
            model_name=args.model,
            epochs=args.epochs,
            batch=args.batch,
            imgsz=args.imgsz,
            name=args.name,
            device=args.device
        )
    
    elif args.command == 'validate':
        trainer = YOLOTrainer(data_path=args.data_path)
        trainer.load_model(args.model_path)
        trainer.validate(split=args.split)
    
    elif args.command == 'benchmark':
        trainer = YOLOTrainer()
        trainer.load_model(args.model_path)
        trainer.benchmark_fps(args.test_dir, num_images=args.num_images)
    
    elif args.command == 'test':
        trainer = YOLOTrainer()
        trainer.load_model(args.model_path)
        trainer.test_and_save(
            test_dir=args.test_dir,
            output_dir=args.output_dir,
            max_images=args.max_images,
            conf=args.conf,
            iou=args.iou
        )


if __name__ == "__main__":
    main()
>>>>>>> Stashed changes
