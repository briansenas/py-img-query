from __future__ import annotations

import json
import os
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
from PIL import Image
from skimage.feature import local_binary_pattern


# --- Image attribute functions ---
def compute_contrast(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return float(gray.std())


def compute_edge_density(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return float(np.mean(edges > 0))


def compute_variance(img):
    return float(np.var(img))


def compute_entropy(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
    hist = hist / hist.sum()
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist)))


def line_count(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=100,
        minLineLength=50,
        maxLineGap=10,
    )
    return 0 if lines is None else len(lines)


def compute_sift(img):
    # Unstructured images will have low keypoints and descriptors
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create()
    keypoints, _ = sift.detectAndCompute(gray, None)
    return len(keypoints)


def compute_lbp(img):
    # Uniform images have no variance thus lack patterns
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    radius = 3
    n_points = 8 * radius
    lbp = local_binary_pattern(gray, n_points, radius, method="uniform")
    return np.var(lbp)


def laplacian_var(img):
    # Blurry images have low Laplacian var
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


# Map attribute names to functions
ATTRIBUTE_FUNCTIONS = {
    "contrast": compute_contrast,
    "edge_density": compute_edge_density,
    "variance": compute_variance,
    "entropy": compute_entropy,
    "line_count": line_count,
    "sift_keypoints": compute_sift,
    "lpb_var": compute_lbp,
    "laplacian_var": laplacian_var,
}

# --- Streamlit UI ---
st.title("Image Attribute Processor")

# Select folder
folder_path = st.text_input(
    "Enter path to image folder (recursively)",
    value="/home/briansenas/Documents/py-img-query/data/SUN360/train_crops_dataset_cvpr_myDistWider",
)

# Select attributes to compute
selected_attributes = st.multiselect(
    "Select attributes to compute",
    options=list(ATTRIBUTE_FUNCTIONS.keys()),
    default=list(ATTRIBUTE_FUNCTIONS.keys()),
)

process_button = st.button("Process Images")

if process_button:
    if not folder_path or not selected_attributes:
        st.error("Please enter a valid folder path and select at least one attribute.")
    else:
        folder = Path(folder_path)
        if not folder.exists():
            st.error("Folder does not exist.")
        else:
            st.info("Processing images... This may take a while.")
            image_paths = list(folder.rglob("*.[jp][pn]g"))  # jpg and png recursively
            result = {}
            stqdm = st.progress(0, text="Progress")
            for img_path in image_paths:
                try:
                    img = np.array(Image.open(img_path).convert("RGB"))
                    img_data = {}
                    for attr in selected_attributes:
                        func = ATTRIBUTE_FUNCTIONS[attr]
                        img_data[attr] = func(img)
                    img_data["image_path"] = str(img_path)
                    img_data["image_basename"] = os.path.basename(img_path)
                    result[str(img_path)] = img_data
                except Exception as e:
                    st.warning(f"Failed to process {img_path}: {e}")
                stqdm.progress(min(len(result) / len(image_paths), 1.0))

            st.success(f"Processed {len(result)} images.")

            # Save JSON locally
            save_path = folder / "image_attributes.json"
            with open(save_path, "w") as f:
                json.dump(result, f, indent=2)
            st.success(f"JSON saved locally at: {save_path}")

            # Allow download
            json_bytes = json.dumps(result, indent=2).encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_bytes,
                file_name="image_attributes.json",
                mime="application/json",
            )
