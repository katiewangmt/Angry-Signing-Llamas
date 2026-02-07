"""
collect_data.py — Collect ASL hand landmark training data via webcam

Usage:
    python collect_data.py

Controls:
    - Press a letter key (a-z) to set which ASL sign you're capturing
    - Press SPACE to capture a sample (captures multiple frames quickly)
    - Press TAB to save dataset and continue
    - Press ESC to save and quit

The script uses MediaPipe to extract hand landmarks in real-time and stores
the normalized landmark vectors along with their labels.
"""

import cv2
import numpy as np
import os
import time
from landmarks import (
    init_mediapipe_hands,
    extract_from_frame,
    draw_landmarks_on_frame,
    augment_landmarks,
    ASL_LABELS,
    NUM_FEATURES,
)

# ------- Configuration -------
DATASET_PATH = "asl_dataset.npz"
CAPTURE_BURST = 10          # Frames to capture per SPACE press
AUGMENT_PER_SAMPLE = 3      # Augmented copies per real sample
WEBCAM_INDEX = 0
WINDOW_NAME = "ASL Data Collector"


def load_existing_dataset(path):
    """Load existing dataset if available."""
    if os.path.exists(path):
        data = np.load(path)
        return data["landmarks"].tolist(), data["labels"].tolist()
    return [], []


def save_dataset(landmarks, labels, path):
    """Save dataset to compressed numpy file."""
    np.savez_compressed(
        path,
        landmarks=np.array(landmarks, dtype=np.float32),
        labels=np.array(labels, dtype=np.int32),
    )
    print(f"💾 Saved {len(landmarks)} samples to {path}")


def get_class_counts(labels):
    """Get per-class sample counts."""
    counts = {}
    for label_idx in set(labels):
        letter = ASL_LABELS[label_idx]
        counts[letter] = labels.count(label_idx)
    return counts


def draw_ui(frame, current_label, landmarks_data, labels_data, capturing, hand_detected):
    """Draw the collection UI overlay on the frame."""
    h, w = frame.shape[:2]

    # Semi-transparent header bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 90), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Title
    cv2.putText(frame, "ASL Data Collector", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2)

    # Current sign being captured
    label_text = f"Current Sign: {ASL_LABELS[current_label]}" if current_label is not None else "Press a letter key (a-z)"
    color = (0, 255, 255) if current_label is not None else (128, 128, 128)
    cv2.putText(frame, label_text, (15, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Sample count
    cv2.putText(frame, f"Total Samples: {len(landmarks_data)}", (15, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Hand detection status
    status = "Hand Detected" if hand_detected else "No Hand - Show your hand!"
    status_color = (0, 255, 0) if hand_detected else (0, 0, 255)
    cv2.putText(frame, status, (w - 280, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    # Capture indicator
    if capturing:
        cv2.circle(frame, (w - 30, 70), 12, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (w - 70, 76),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Bottom bar with class counts
    counts = get_class_counts(labels_data)
    if counts:
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 45), (w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)

        count_text = "  ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        cv2.putText(frame, count_text, (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

    # Controls help
    help_y = h - 60
    cv2.putText(frame, "[A-Z] Select  [SPACE] Capture  [TAB] Save  [ESC] Quit",
                (10, help_y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)

    return frame


def main():
    print("=" * 50)
    print("  🤟 ASL Data Collector")
    print("=" * 50)
    print("\nControls:")
    print("  [A-Z]   → Select which sign to capture")
    print("  [SPACE] → Capture samples (burst of frames)")
    print("  [TAB]   → Save dataset")
    print("  [ESC]   → Save and quit\n")

    # Load existing data
    landmarks_data, labels_data = load_existing_dataset(DATASET_PATH)
    if landmarks_data:
        print(f"📂 Loaded {len(landmarks_data)} existing samples")

    # Initialize
    hands = init_mediapipe_hands(static_mode=False, max_hands=1, min_detection_conf=0.7)
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Could not open webcam!")
        return

    current_label = None
    capturing = False
    capture_count = 0

    print("📷 Webcam ready. Show your hand and start capturing!\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Mirror the frame for more natural interaction
        frame = cv2.flip(frame, 1)

        # Extract landmarks
        landmarks, results = extract_from_frame(frame, hands)
        hand_detected = landmarks is not None

        # Draw hand skeleton
        if results.hand_landmarks:
            frame = draw_landmarks_on_frame(frame, results)

        # Capture burst
        if capturing and hand_detected and current_label is not None:
            landmarks_data.append(landmarks)
            labels_data.append(current_label)

            # Add augmented samples
            augmented = augment_landmarks(landmarks, num_augmented=AUGMENT_PER_SAMPLE)
            for aug in augmented:
                landmarks_data.append(aug)
                labels_data.append(current_label)

            capture_count += 1
            if capture_count >= CAPTURE_BURST:
                capturing = False
                total_added = CAPTURE_BURST * (1 + AUGMENT_PER_SAMPLE)
                print(f"  ✅ Captured {total_added} samples for '{ASL_LABELS[current_label]}' "
                      f"(total: {len(landmarks_data)})")

        # Draw UI
        frame = draw_ui(frame, current_label, landmarks_data, labels_data, capturing, hand_detected)
        cv2.imshow(WINDOW_NAME, frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC key
            break
        elif key == 9:  # TAB key
            save_dataset(landmarks_data, labels_data, DATASET_PATH)
        elif key == ord(' '):
            if current_label is not None and hand_detected:
                capturing = True
                capture_count = 0
                print(f"  📸 Capturing '{ASL_LABELS[current_label]}'...")
            elif current_label is None:
                print("  ⚠️  Select a letter first (press a-z)")
            else:
                print("  ⚠️  No hand detected - show your hand!")
        elif ord('a') <= key <= ord('z'):
            letter = chr(key).upper()
            current_label = ASL_LABELS.index(letter)
            print(f"  🔤 Selected: {letter}")

    # Save on exit
    if landmarks_data:
        save_dataset(landmarks_data, labels_data, DATASET_PATH)

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("\n👋 Done! Run 'python train_model.py' to train your model.")


if __name__ == "__main__":
    main()
