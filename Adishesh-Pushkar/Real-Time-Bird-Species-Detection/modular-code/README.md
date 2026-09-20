# Bird Detection and Species Classification

This project provides a modular pipeline for detecting birds in videos and classifying their species using YOLO for detection and EfficientNet for species classification.

## Project Structure

```
.
├── dataset_preparation.py  # Dataset downloading and merging
├── train.py               # YOLO model training and evaluation
├── model.py               # Model loading and inference
├── run_inference.py       # Main video processing script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Module Descriptions

### 1. `dataset_preparation.py`
Handles dataset downloading, splitting, and merging operations.

**Key Classes:**
- `DatasetPreparation`: Main class for dataset operations

**Key Methods:**
- `download_birdies_dataset()`: Downloads Birdies dataset from Kaggle
- `split_birdies_dataset()`: Splits dataset into train/val/test
- `merge_datasets()`: Merges two datasets into combined format

**Example Usage:**
```python
from dataset_preparation import DatasetPreparation

# Initialize
dataset_prep = DatasetPreparation(train_ratio=0.8, val_ratio=0.1, test_ratio=0.1)

# Download and split Birdies dataset
birdies_path = dataset_prep.download_birdies_dataset(destination_path="birdies")
dataset_prep.split_birdies_dataset(root_path="birdies")

# Merge with another dataset
dataset_prep.merge_datasets(
    dataset_1_path="birdies",
    dataset_2_path="another-bird-dataset",
    output_path="combined-birds"
)
```

### 2. `train.py`
Contains YOLO model training, validation, and testing functionality.

**Key Classes:**
- `YOLOTrainer`: Main class for training and evaluating YOLO models

**Key Methods:**
- `create_data_yaml()`: Generates YOLO data configuration
- `train()`: Trains YOLO model
- `validate()`: Validates model performance
- `benchmark_fps()`: Measures inference speed
- `test_and_save()`: Runs inference on test images

**Command-Line Interface:**
```bash
# Create data.yaml configuration
python train.py create-yaml --data-path combined-birds

# Train a model
python train.py train --model yolov8n.pt --epochs 20 --batch 16

# Validate trained model
python train.py validate runs/bird_detection/weights/best.pt

# Benchmark inference speed
python train.py benchmark runs/bird_detection/weights/best.pt test_images/

# Test on images
python train.py test runs/bird_detection/weights/best.pt test_images/ output/
```

**Example Usage:**
```python
from train import YOLOTrainer

# Initialize trainer
trainer = YOLOTrainer(data_path="combined-birds")

# Create data configuration
trainer.create_data_yaml()

# Train model
trainer.train(
    model_name="yolov8n.pt",
    epochs=20,
    batch=16,
    name="bird_detection"
)

# Validate
trainer.load_model("runs/bird_detection/weights/best.pt")
metrics = trainer.validate()

# Benchmark
trainer.benchmark_fps("test_images/")
```

### 3. `model.py`
Contains model classes for bird detection and species classification.

**Key Classes:**
- `BirdDetectionModel`: YOLO-based bird detector
- `SpeciesClassifier`: EfficientNet-based species classifier
- `BirdDetectionPipeline`: Combined pipeline for detection and classification

**Example Usage:**
```python
from model import BirdDetectionPipeline
import cv2

# Initialize pipeline
pipeline = BirdDetectionPipeline(
    yolo_model_path="yolo11n.pt",
    species_model_path="models/species_classifier.pth",
    num_classes=500
)

# Process a single frame
frame = cv2.imread("test_image.jpg")
detections = pipeline.process_frame(frame, detect_conf=0.25)
annotated = pipeline.annotate_frame(frame, detections)

# Save result
cv2.imwrite("output.jpg", annotated)
```

### 4. `run_inference.py`
Main script for processing videos with bird detection and species classification.

## Installation

### Requirements
```bash
pip install torch torchvision opencv-python numpy pillow ultralytics kagglehub
```

### Model Files
1. **YOLO Model**: Download or train a YOLO model (e.g., `yolo11n.pt`)
2. **Species Classifier**: Train EfficientNet-B3 model and save weights to `models/species_classifier.pth`

## Usage

### Basic Usage
Process a video with default settings:
```bash
python run_inference.py path/to/video.mp4
```

### Specify Output Path
```bash
python run_inference.py path/to/video.mp4 --output results/output.mp4
```

### Custom Model Paths
```bash
python run_inference.py path/to/video.mp4 \
    --yolo-model path/to/yolo.pt \
    --species-model path/to/species_classifier.pth \
    --num-classes 500
```

### Adjust Detection Parameters
```bash
python run_inference.py path/to/video.mp4 \
    --detect-conf 0.5 \
    --classify-threshold 0.3
```

### Display Options
```bash
# Don't show species classification
python run_inference.py path/to/video.mp4 --no-species

# Show detection confidence
python run_inference.py path/to/video.mp4 --show-detection-conf

# Change progress display interval
python run_inference.py path/to/video.mp4 --display-interval 60
```

## Command-Line Arguments

### Required Arguments
- `video_path`: Path to input video file

### Optional Arguments

**Output:**
- `--output`, `-o`: Path to output video file (default: `output.mp4`)

**Model Paths:**
- `--yolo-model`: Path to YOLO model weights (default: `yolo11n.pt`)
- `--species-model`: Path to species classifier weights (default: `models/species_classifier.pth`)
- `--num-classes`: Number of bird species classes (default: `500`)

**Detection Parameters:**
- `--detect-conf`: Confidence threshold for bird detection (default: `0.25`)
- `--classify-threshold`: Minimum confidence for species classification (default: `0.0`)

**Display Options:**
- `--no-species`: Don't show species classification labels
- `--show-detection-conf`: Show detection confidence in labels
- `--display-interval`: Print progress every N frames (default: `30`)

## Example Workflow

### 1. Prepare Dataset
```python
from dataset_preparation import DatasetPreparation

dataset_prep = DatasetPreparation()
dataset_prep.download_birdies_dataset()
dataset_prep.split_birdies_dataset()
```

### 2. Train YOLO Detection Model
```bash
# Create data.yaml and train
python train.py train \
    --data-path combined-birds \
    --model yolov8n.pt \
    --epochs 20 \
    --batch 16 \
    --name bird_yolo

# Validate the trained model
python train.py validate runs/bird_yolo/weights/best.pt
```

### 3. Train Species Classifier
(Use your preferred training scripts for EfficientNet)

### 4. Run Inference
```bash
python run_inference.py sample_video.mp4 \
    --yolo-model runs/bird_yolo/weights/best.pt \
    --species-model models/species_classifier.pth \
    --output results/annotated_video.mp4 \
    --detect-conf 0.3 \
    --classify-threshold 0.2 \
    --show-detection-conf
```

## Output Format

The pipeline outputs:
- **Annotated Video**: Video with bounding boxes and species labels
- **Console Statistics**: 
  - Processing FPS
  - Inference time per frame
  - Total detections
  - Average detections per frame

## Performance Notes

- **GPU Acceleration**: Automatically uses CUDA if available
- **Processing Speed**: Depends on:
  - Hardware (GPU/CPU)
  - Video resolution
  - Model size
  - Number of detections per frame
<<<<<<< Updated upstream
=======

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Use smaller YOLO model (e.g., `yolo11n.pt` instead of `yolo11x.pt`)
   - Process at lower resolution
   - Reduce batch size

2. **Slow Processing**
   - Ensure GPU is being used (`Using device: cuda` should appear)
   - Increase `--detect-conf` to reduce detections
   - Use lighter models

3. **Model Not Found**
   - Check model file paths
   - Ensure models are downloaded/trained
   - Verify file permissions

## License

This project structure is designed for educational and research purposes.
>>>>>>> Stashed changes
