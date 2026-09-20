import os
import cv2
import time
import numpy as np
import shutil
import random
import yaml
import kagglehub

# Dataset split ratios
TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1

def download_birdies_dataset():
    """Download and copy birdies dataset from Kaggle"""
    print("Downloading birdies dataset...")
    src_path = kagglehub.dataset_download("gpiosenka/birdies")
    
    dst_path = os.path.join(os.getcwd(), "birdies")
    
    if not os.path.exists(dst_path):
        shutil.copytree(src_path, dst_path)
    
    print("Dataset copied to:", dst_path)
    return dst_path

def split_birdies_dataset():
    """Split birdies dataset into train/val/test"""
    print("Splitting birdies dataset...")
    
    ROOT = "birdies"
    IMAGES_DIR = os.path.join(ROOT, "images")
    LABELS_DIR = os.path.join(ROOT, "labels")
    TEST_IMAGES_DIR = os.path.join(ROOT, "test images")
    
    # Create split folders
    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(IMAGES_DIR, split), exist_ok=True)
        os.makedirs(os.path.join(LABELS_DIR, split), exist_ok=True)
    
    # Collect all image files (excluding folders)
    images = [
        f for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    
    random.shuffle(images)
    
    n = len(images)
    n_train = int(n * TRAIN_RATIO)
    n_val = int(n * VAL_RATIO)
    
    train_imgs = images[:n_train]
    val_imgs = images[n_train:n_train + n_val]
    test_imgs = images[n_train + n_val:]
    
    def move_pair(img, split):
        img_src = os.path.join(IMAGES_DIR, img)
        lbl_src = os.path.join(LABELS_DIR, img.rsplit(".", 1)[0] + ".txt")
        
        img_dst = os.path.join(IMAGES_DIR, split, img)
        lbl_dst = os.path.join(LABELS_DIR, split, os.path.basename(lbl_src))
        
        shutil.move(img_src, img_dst)
        if os.path.exists(lbl_src):
            shutil.move(lbl_src, lbl_dst)
    
    for img in train_imgs:
        move_pair(img, "train")
    
    for img in val_imgs:
        move_pair(img, "val")
    
    for img in test_imgs:
        move_pair(img, "test")
    
    # Handle provided test_images folder (images only)
    if os.path.exists(TEST_IMAGES_DIR):
        for img in os.listdir(TEST_IMAGES_DIR):
            if img.lower().endswith((".jpg", ".jpeg", ".png")):
                shutil.move(
                    os.path.join(TEST_IMAGES_DIR, img),
                    os.path.join(IMAGES_DIR, "test", img)
                )
    
    print("Birdies dataset successfully split!")

def combine_datasets():
    """Combine multiple bird datasets"""
    print("Combining datasets...")
    
    DATASET_1 = "../birdies"
    DATASET_2 = "../another-bird-dataset"
    OUT_ROOT = "combined-birds"
    
    splits_map = {
        "train": "train",
        "val": "valid"
    }
    
    # Create output directories
    for split in ["train", "valid"]:
        os.makedirs(f"{OUT_ROOT}/{split}/images", exist_ok=True)
        os.makedirs(f"{OUT_ROOT}/{split}/labels", exist_ok=True)
    
    def copy_from_birdies(split, out_split):
        src_images = os.path.join(DATASET_1, "images", split)
        src_labels = os.path.join(DATASET_1, "labels", split)
        
        dst_images = os.path.join(OUT_ROOT, out_split, "images")
        dst_labels = os.path.join(OUT_ROOT, out_split, "labels")
        
        for img in os.listdir(src_images):
            if not img.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            
            label = img.rsplit(".", 1)[0] + ".txt"
            
            shutil.copy(
                os.path.join(src_images, img),
                os.path.join(dst_images, f"b1_{img}")
            )
            
            shutil.copy(
                os.path.join(src_labels, label),
                os.path.join(dst_labels, f"b1_{label}")
            )
    
    def copy_from_another_dataset(split, out_split):
        src_images = os.path.join(DATASET_2, split, "images")
        src_labels = os.path.join(DATASET_2, split, "labels")
        
        dst_images = os.path.join(OUT_ROOT, out_split, "images")
        dst_labels = os.path.join(OUT_ROOT, out_split, "labels")
        
        for img in os.listdir(src_images):
            if not img.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            
            label = img.rsplit(".", 1)[0] + ".txt"
            
            shutil.copy(
                os.path.join(src_images, img),
                os.path.join(dst_images, f"b2_{img}")
            )
            
            shutil.copy(
                os.path.join(src_labels, label),
                os.path.join(dst_labels, f"b2_{label}")
            )
    
    copy_from_birdies("train", "train")
    copy_from_birdies("val", "valid")
    
    copy_from_another_dataset("train", "train")
    copy_from_another_dataset("valid", "valid")
    
    print("Successfully merged datasets into:", OUT_ROOT)
    
    return OUT_ROOT

def create_data_yaml(dataset_path):
    """Create data.yaml for YOLO training"""
    print("Creating data.yaml...")
    
    # Get all unique class IDs from labels
    class_ids = set()
    labels_dir = os.path.join(dataset_path, "train/labels")
    
    for label_file in os.listdir(labels_dir):
        with open(os.path.join(labels_dir, label_file), 'r') as f:
            for line in f:
                class_id = int(line.split()[0])
                class_ids.add(class_id)
    
    num_classes = max(class_ids) + 1
    
    # Create data.yaml
    data_config = {
        'path': os.path.abspath(dataset_path),
        'train': 'train/images',
        'val': 'valid/images',
        'nc': num_classes,
        'names': list(range(num_classes))
    }
    
    with open(os.path.join(dataset_path, 'data.yaml'), 'w') as f:
        yaml.dump(data_config, f, default_flow_style=False)
    
    print(f"data.yaml created with {num_classes} classes")

if __name__ == "__main__":
    # Download and split birdies dataset
    download_birdies_dataset()
    split_birdies_dataset()
    
    # Combine with another dataset
    combined_path = combine_datasets()
    
    # Create data.yaml
    create_data_yaml(combined_path)
    
    print("\nDataset preparation complete!")