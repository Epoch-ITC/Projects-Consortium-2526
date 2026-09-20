import streamlit as st
import cv2
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b3
from ultralytics import YOLO
from PIL import Image
import numpy as np
import tempfile
import os
import time

# Page config
st.set_page_config(
    page_title="Bird Species Detection",
    page_icon="🐦",
    layout="wide"
)

@st.cache_resource
def load_models():
    """Load YOLO and EfficientNet models"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Load YOLO model
    yolo_model = YOLO("runs/bird_yolov8n_combined5/weights/best.pt")
    
    # Load EfficientNet species classifier
    num_classes = 500
    species_model = efficientnet_b3(weights=None)
    in_features = species_model.classifier[1].in_features
    species_model.classifier[1] = nn.Linear(in_features, num_classes)
    species_model.load_state_dict(
        torch.load("models/species_classifier.pth", map_location=device)
    )
    species_model.to(device)
    species_model.eval()
    
    # Preprocessing transforms
    preprocess = transforms.Compose([
        transforms.Resize((300, 300)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    return yolo_model, species_model, preprocess, device

def process_video(video_path, yolo_model, species_model, preprocess, device, progress_bar, status_text):
    """Process video with YOLO detection and species classification"""
    
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create temporary output file
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
    out = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )
    
    frame_count = 0
    total_time = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        start_time = time.time()
        
        # Step 1: YOLO Detection
        yolo_results = yolo_model(frame, verbose=False)
        
        # Step 2: For each detected bird, classify species
        for result in yolo_results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    conf = box.conf.item()
                    
                    # Crop bird region
                    bird_crop = frame[y1:y2, x1:x2]
                    
                    if bird_crop.size > 0:
                        # Classify species
                        bird_pil = Image.fromarray(cv2.cvtColor(bird_crop, cv2.COLOR_BGR2RGB))
                        input_tensor = preprocess(bird_pil).unsqueeze(0).to(device)
                        
                        with torch.no_grad():
                            outputs = species_model(input_tensor)
                            probs = torch.softmax(outputs, dim=1)
                            species_conf, species_id = torch.max(probs, 1)
                        
                        # Draw box and species label
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = f"Species {species_id.item()}: {species_conf.item():.2%}"
                        cv2.putText(frame, label, (x1, y1-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        inference_time = time.time() - start_time
        total_time += inference_time
        
        out.write(frame)
        frame_count += 1
        
        # Update progress
        progress = frame_count / total_frames
        progress_bar.progress(progress)
        
        if frame_count % 10 == 0:
            avg_fps = frame_count / total_time
            status_text.text(f"Processing frame {frame_count}/{total_frames} | "
                           f"FPS: {avg_fps:.2f} | Time: {inference_time*1000:.2f}ms")
    
    cap.release()
    out.release()
    
    avg_fps = frame_count / total_time if total_time > 0 else 0
    
    return output_path, frame_count, avg_fps

def main():
    st.title(" Real-Time Bird Species Detection")
    st.markdown("An Computer Vision Project for the 2025-26 tenure by Epoch cores Adishesh and Pushkar")
    
    # # Sidebar
    # with st.sidebar:
    #     st.header("About")
    #     st.info("""
    #     This app uses:
    #     - **YOLOv8n** for bird detection
    #     - **EfficientNet-B3** for species classification (500 classes)
        
    #     Upload a video and wait for processing to complete.
    #     """)
        
    #     st.header("Model Info")
    #     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    #     st.write(f"**Device:** {device}")
    
    # Load models
    with st.spinner("Loading models..."):
        try:
            yolo_model, species_model, preprocess, device = load_models()
            st.success(" Models loaded successfully!")
        except Exception as e:
            st.error(f"Error loading models: {e}")
            st.stop()
    
    # File upload
    uploaded_file = st.file_uploader("Choose a video file", type=["mp4", "avi", "mov", "mkv"])
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        tfile.close()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Input Video")
            st.video(tfile.name)
        
        # Process button
        if st.button(" Process Video", type="primary"):
            st.subheader("Processing...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Process video
                output_path, frame_count, avg_fps = process_video(
                    tfile.name, 
                    yolo_model, 
                    species_model, 
                    preprocess, 
                    device,
                    progress_bar,
                    status_text
                )
                
                status_text.text(f" Processing complete! Processed {frame_count} frames at {avg_fps:.2f} FPS")
                
                # Display output video in col2
                with col2:
                    st.subheader("Output Video")
                    st.video(output_path)
                
                # Optional: Keep download button if desired
                with col2:
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            label=" Download Processed Video",
                            data=f,
                            file_name="bird_detection_output.mp4",
                            mime="video/mp4"
                        )
                
            except Exception as e:
                st.error(f"Error processing video: {e}")
                import traceback
                st.code(traceback.format_exc())

        
        # Cleanup uploaded file on session end
        if st.session_state.get('cleanup_file'):
            try:
                os.unlink(tfile.name)
            except:
                pass

if __name__ == "__main__":
    main()