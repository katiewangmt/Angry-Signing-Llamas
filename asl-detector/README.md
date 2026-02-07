# 🤟 ASL Sign Language Detector

**Real-time American Sign Language recognition using MediaPipe + TensorFlow**

A hackathon-ready project that uses your webcam to detect ASL hand signs in real time. It extracts hand landmarks via MediaPipe and classifies them with a TensorFlow neural network.

---

## Architecture

```
Webcam → OpenCV → MediaPipe Hands → 21 Hand Landmarks (x,y,z) → TensorFlow Model → ASL Letter
```

### How It Works

1. **MediaPipe Hands** detects 21 3D hand landmarks from each video frame
2. Landmarks are normalized relative to the wrist (position-invariant)
3. A trained **TensorFlow/Keras** neural network classifies the landmark pattern
4. The predicted ASL letter is overlaid on the video feed in real time

---

## Quick Start

### 1. Install Dependencies

```bash
pip install tensorflow mediapipe opencv-python numpy scikit-learn
```

### 2. Collect Training Data

Run the data collector to capture hand landmark samples for each ASL letter:

```bash
python collect_data.py
```

- Press the letter key (a-z) to set which sign you're recording
- Hold up the sign and press SPACE to capture samples
- Press Q to quit — data saves to `asl_dataset.npz`

### 3. Train the Model

```bash
python train_model.py
```

This trains a neural network on your collected landmarks and saves `asl_model.keras`.

### 4. Run Real-Time Detection

```bash
python detect.py
```

Point your webcam at ASL hand signs and see predictions live!

---

## Project Structure

```
asl-detector/
├── collect_data.py     # Webcam data collection with MediaPipe
├── train_model.py      # TensorFlow model training
├── detect.py           # Real-time ASL detection
├── model.py            # Neural network architecture
├── landmarks.py        # MediaPipe hand landmark utilities
├── asl_dataset.npz     # (generated) Collected training data
├── asl_model.keras     # (generated) Trained model
└── README.md
```

## ASL Alphabet Reference

The model recognizes static ASL alphabet signs (A-Z). Note that J and Z involve motion and are harder to detect with static frames — consider using multiple frames for these.

---

## Tips for the Hackathon

- **Start small**: Train on 5-10 letters first, then expand
- **Collect diverse data**: Vary hand position, angle, and distance
- **Lighting matters**: Consistent lighting improves MediaPipe detection
- **Augmentation**: The training script includes landmark augmentation for robustness
- **Sentence building**: The detector accumulates letters into words — press SPACE to add a space, BACKSPACE to delete

---

## Tech Stack

- **TensorFlow 2.x** — Neural network training & inference
- **MediaPipe** — Hand landmark detection (21 points × 3 coords)
- **OpenCV** — Webcam capture & display
- **NumPy / scikit-learn** — Data processing & splitting
