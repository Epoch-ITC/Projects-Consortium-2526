"""
Dataset Preparation Module
This module handles downloading, splitting, and merging bird detection datasets.
"""

import os
import shutil
import random
import kagglehub


class DatasetPreparation:
    """Handles dataset downloading, splitting, and merging operations."""
    
    def __init__(self, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1):
        """
        Initialize dataset preparation with split ratios.
        
        Args:
            train_ratio: Proportion of data for training (default: 0.8)
            val_ratio: Proportion of data for validation (default: 0.1)
            test_ratio: Proportion of data for testing (default: 0.1)
        """
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
    
    def download_birdies_dataset(self, destination_path="birdies"):
        """
        Download the Birdies dataset from Kaggle.
        
        Args:
            destination_path: Path where dataset should be saved
            
        Returns:
            str: Path to the downloaded dataset
        """
        # Download dataset from Kaggle (goes to kagglehub cache)
        src_path = kagglehub.dataset_download("gpiosenka/birdies")
        
        # Destination: specified directory
        dst_path = os.path.join(os.getcwd(), destination_path)
        
        # Copy dataset to destination directory
        if not os.path.exists(dst_path):
            shutil.copytree(src_path, dst_path)
            print(f"Dataset copied to: {dst_path}")
        else:
            print(f"Dataset already exists at: {dst_path}")
        
        return dst_path
    
    def split_birdies_dataset(self, root_path="birdies"):
        """
        Split the Birdies dataset into train/val/test splits.
        
        Args:
            root_path: Root path of the Birdies dataset
        """
        images_dir = os.path.join(root_path, "images")
        labels_dir = os.path.join(root_path, "labels")
        test_images_dir = os.path.join(root_path, "test images")
        
        # Create split folders
        for split in ["train", "val", "test"]:
            os.makedirs(os.path.join(images_dir, split), exist_ok=True)
            os.makedirs(os.path.join(labels_dir, split), exist_ok=True)
        
        # Collect all image files (excluding folders)
        images = [
            f for f in os.listdir(images_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        
        random.shuffle(images)
        
        n = len(images)
        n_train = int(n * self.train_ratio)
        n_val = int(n * self.val_ratio)
        
        train_imgs = images[:n_train]
        val_imgs = images[n_train:n_train + n_val]
        test_imgs = images[n_train + n_val:]
        
        def move_pair(img, split):
            img_src = os.path.join(images_dir, img)
            lbl_src = os.path.join(labels_dir, img.rsplit(".", 1)[0] + ".txt")
            
            img_dst = os.path.join(images_dir, split, img)
            lbl_dst = os.path.join(labels_dir, split, os.path.basename(lbl_src))
            
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
        if os.path.exists(test_images_dir):
            for img in os.listdir(test_images_dir):
                if img.lower().endswith((".jpg", ".jpeg", ".png")):
                    shutil.move(
                        os.path.join(test_images_dir, img),
                        os.path.join(images_dir, "test", img)
                    )
        
        print(f"Birdies dataset successfully split!")
        print(f"Train: {len(train_imgs)}, Val: {len(val_imgs)}, Test: {len(test_imgs)}")
    
    def merge_datasets(self, dataset_1_path, dataset_2_path, output_path="combined-birds"):
        """
        Merge two bird datasets into a single combined dataset.
        
        Args:
            dataset_1_path: Path to first dataset (Birdies format)
            dataset_2_path: Path to second dataset
            output_path: Output path for merged dataset
        """
        # Create output directory structure
        for split in ["train", "valid"]:
            os.makedirs(f"{output_path}/{split}/images", exist_ok=True)
            os.makedirs(f"{output_path}/{split}/labels", exist_ok=True)
        
        splits_map = {
            "train": "train",
            "val": "valid"
        }
        
        # Copy from first dataset (Birdies)
        for split, out_split in splits_map.items():
            self._copy_from_birdies(dataset_1_path, split, output_path, out_split)
        
        # Copy from second dataset
        for split, out_split in splits_map.items():
            self._copy_from_another_dataset(dataset_2_path, split, output_path, out_split)
        
        print(f"Successfully merged datasets into: {output_path}")
    
    def _copy_from_birdies(self, dataset_path, split, output_path, out_split):
        """Copy files from Birdies dataset format."""
        src_images = os.path.join(dataset_path, "images", split)
        src_labels = os.path.join(dataset_path, "labels", split)
        
        dst_images = os.path.join(output_path, out_split, "images")
        dst_labels = os.path.join(output_path, out_split, "labels")
        
        if not os.path.exists(src_images):
            print(f"Warning: {src_images} does not exist, skipping...")
            return
        
        for img in os.listdir(src_images):
            if not img.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            
            label = img.rsplit(".", 1)[0] + ".txt"
            
            shutil.copy(
                os.path.join(src_images, img),
                os.path.join(dst_images, f"b1_{img}")
            )
            
            label_path = os.path.join(src_labels, label)
            if os.path.exists(label_path):
                shutil.copy(
                    label_path,
                    os.path.join(dst_labels, f"b1_{label}")
                )
    
    def _copy_from_another_dataset(self, dataset_path, split, output_path, out_split):
        """Copy files from another dataset format."""
        src_images = os.path.join(dataset_path, split, "images")
        src_labels = os.path.join(dataset_path, split, "labels")
        
        dst_images = os.path.join(output_path, out_split, "images")
        dst_labels = os.path.join(output_path, out_split, "labels")
        
        if not os.path.exists(src_images):
            print(f"Warning: {src_images} does not exist, skipping...")
            return
        
        for img in os.listdir(src_images):
            if not img.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            
            label = img.rsplit(".", 1)[0] + ".txt"
            
            shutil.copy(
                os.path.join(src_images, img),
                os.path.join(dst_images, f"b2_{img}")
            )
            
            label_path = os.path.join(src_labels, label)
            if os.path.exists(label_path):
                shutil.copy(
                    label_path,
                    os.path.join(dst_labels, f"b2_{label}")
                )


# Example usage
if __name__ == "__main__":
    # Initialize dataset preparation
    dataset_prep = DatasetPreparation(train_ratio=0.8, val_ratio=0.1, test_ratio=0.1)
    
    # Download and split Birdies dataset
    birdies_path = dataset_prep.download_birdies_dataset(destination_path="birdies")
    dataset_prep.split_birdies_dataset(root_path="birdies")
    
    # Optional: Merge with another dataset
    # dataset_prep.merge_datasets(
    #     dataset_1_path="birdies",
    #     dataset_2_path="another-bird-dataset",
    #     output_path="combined-birds"
    # )
