"""
collect_sequence_data.py — Collect ASL sequence training data via webcam

Records video snippets (sequences of frames) for sequence-based ASL signs
like "I love you" and "thank you" using an LSTM model.

This script collects data for WORDS mode (sequence-based signs).
For LETTERS mode (static A-Z signs), use collect_data.py instead.

Usage:
    python collect_sequence_data.py

Controls:
    - Press 1 to select "I love you"
    - Press 2 to select "Thank you"
    - Press S to select "6 7"
    - Press T to select "Thank you"
    - Press O to select "OK"
    - Press H to select "Hello"
    - Press G to select "Goodbye"
    - Press SPACE to start/stop recording a sequence
    - Press TAB to save dataset and continue
    - Press ESC to save and quit

The script records sequences of hand landmarks over time and stores them
for training an LSTM model.
"""

import cv2
import numpy as np
import os
import time
from collections import deque
from landmarks import (
    init_mediapipe_hands,
    extract_from_frame,
    draw_landmarks_on_frame,
    NUM_FEATURES,
)

# ------- Configuration -------
DATASET_PATH = "asl_sequence_dataset.npz"
SEQUENCE_LENGTH = 30  # Number of frames per sequence (~1 second at 30fps)
WEBCAM_INDEX = 0
WINDOW_NAME = "ASL Sequence Data Collector"
FPS = 30

# Sequence-based ASL signs
SEQUENCE_LABELS = ["I_LOVE_YOU", "THANK_YOU", "SIGMA", "BADDIE", "RIZZ", "6_7", "OK", "HELLO", "GOODBYE"]
NUM_SEQUENCE_CLASSES = len(SEQUENCE_LABELS)


def load_existing_dataset(path):
    """Load existing dataset if available."""
    if os.path.exists(path):
        data = np.load(path)
        sequences = data["sequences"].tolist()
        labels = data["labels"].tolist()
        return sequences, labels
    return [], []


def save_dataset(sequences, labels, path):
    """Save dataset to compressed numpy file."""
    # Convert to numpy arrays
    # Pad or truncate sequences to SEQUENCE_LENGTH
    processed_sequences = []
    for seq in sequences:
        if len(seq) < SEQUENCE_LENGTH:
            # Pad with last frame
            padded = list(seq) + [seq[-1]] * (SEQUENCE_LENGTH - len(seq))
        elif len(seq) > SEQUENCE_LENGTH:
            # Truncate to SEQUENCE_LENGTH
            padded = seq[:SEQUENCE_LENGTH]
        else:
            padded = seq
        processed_sequences.append(padded)
    
    np.savez_compressed(
        path,
        sequences=np.array(processed_sequences, dtype=np.float32),
        labels=np.array(labels, dtype=np.int32),
    )
    print(f"💾 Saved {len(sequences)} sequences to {path}")


def get_class_counts(labels):
    """Get per-class sample counts."""
    counts = {}
    for label_idx in set(labels):
        sign_name = SEQUENCE_LABELS[label_idx]
        counts[sign_name] = labels.count(label_idx)
    return counts


def draw_ui(frame, current_label, sequences_data, labels_data, recording, hand_detected, frame_buffer_size):
    """Draw the collection UI overlay on the frame."""
    h, w = frame.shape[:2]

    # Semi-transparent header bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Title
    cv2.putText(frame, "ASL Sequence Data Collector", (15, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 128), 2)

    # Current sign being captured
    if current_label is not None:
        label_text = f"Current Sign: {SEQUENCE_LABELS[current_label]}"
        color = (0, 255, 255)
    else:
        label_text = "Press 1, 2, S, T, O, H, or G to select a sign"
        color = (128, 128, 128)
    cv2.putText(frame, label_text, (15, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # Sequence count
    cv2.putText(frame, f"Total Sequences: {len(sequences_data)}", (15, 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Recording status
    if recording:
        status_text = f"RECORDING... ({frame_buffer_size}/{SEQUENCE_LENGTH} frames)"
        status_color = (0, 0, 255)
    else:
        status_text = "Ready to record"
        status_color = (0, 255, 0)
    cv2.putText(frame, status_text, (15, 110),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

    # Hand detection status
    hand_status = "Hand Detected" if hand_detected else "No Hand - Show your hand!"
    hand_color = (0, 255, 0) if hand_detected else (0, 0, 255)
    cv2.putText(frame, hand_status, (w - 280, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, hand_color, 2)

    # Recording indicator
    if recording:
        cv2.circle(frame, (w - 30, 70), 12, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (w - 70, 76),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # Bottom bar with class counts
    counts = get_class_counts(labels_data)
    if counts:
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 60), (w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)

        count_text = "  ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
        cv2.putText(frame, count_text, (10, h - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

    # Controls help
    cv2.putText(frame, "[1] ILY [2] ThankU [3/X] Sigma [4/B] Baddie [5/R] Rizz [S] 67 [O] OK [H] Hi [G] Bye",
                (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
    cv2.putText(frame, "[SPACE] Record  [TAB] Save  [ESC] Quit",
                (10, h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

    return frame


def main():
    print("=" * 50)
    print("  🤟 ASL Sequence Data Collector")
    print("=" * 50)
    print("\nControls:")
    print("  [1]     → Select 'I love you'")
    print("  [2]     → Select 'Thank you'")
    print("  [3/X]   → Select 'Sigma'")
    print("  [4/B]   → Select 'Baddie'")
    print("  [5/R]   → Select 'Rizz'")
    print("  [S]     → Select '6 7'")
    print("  [O]     → Select 'OK'")
    print("  [H]     → Select 'Hello'")
    print("  [G]     → Select 'Goodbye'")
    print("  [SPACE] → Start/Stop recording sequence")
    print("  [TAB]   → Save dataset")
    print("  [ESC]   → Save and quit\n")
    print(f"Recording {SEQUENCE_LENGTH} frames per sequence (~{SEQUENCE_LENGTH/FPS:.1f} seconds)\n")

    # Load existing data
    sequences_data, labels_data = load_existing_dataset(DATASET_PATH)
    if sequences_data:
        print(f"📂 Loaded {len(sequences_data)} existing sequences")

    # Initialize
    hands = init_mediapipe_hands(static_mode=False, max_hands=1, min_detection_conf=0.7)
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, FPS)

    if not cap.isOpened():
        print("❌ Could not open webcam!")
        return

    current_label = None
    recording = False
    frame_buffer = deque(maxlen=SEQUENCE_LENGTH)

    print("📷 Webcam ready. Show your hand and start recording!\n")

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

        # Record sequence
        if recording:
            if hand_detected:
                frame_buffer.append(landmarks)
            else:
                # If hand lost during recording, pad with last valid frame
                if len(frame_buffer) > 0:
                    frame_buffer.append(frame_buffer[-1])
                else:
                    # No valid frames yet, skip this recording
                    pass

        # Draw UI
        frame = draw_ui(frame, current_label, sequences_data, labels_data, 
                       recording, hand_detected, len(frame_buffer))
        cv2.imshow(WINDOW_NAME, frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC key
            break
        elif key == 9:  # TAB key
            save_dataset(sequences_data, labels_data, DATASET_PATH)
        elif key == ord(' '):  # SPACE key
            if recording:
                # Stop recording
                if len(frame_buffer) >= SEQUENCE_LENGTH // 2:  # At least half the sequence
                    # Pad or truncate to SEQUENCE_LENGTH
                    sequence = list(frame_buffer)
                    if len(sequence) < SEQUENCE_LENGTH:
                        # Pad with last frame
                        sequence.extend([sequence[-1]] * (SEQUENCE_LENGTH - len(sequence)))
                    elif len(sequence) > SEQUENCE_LENGTH:
                        # Truncate
                        sequence = sequence[:SEQUENCE_LENGTH]
                    
                    sequences_data.append(sequence)
                    labels_data.append(current_label)
                    print(f"  ✅ Recorded sequence for '{SEQUENCE_LABELS[current_label]}' "
                          f"({len(sequence)} frames, total: {len(sequences_data)})")
                else:
                    print(f"  ⚠️  Sequence too short ({len(frame_buffer)} frames). Discarding.")
                
                recording = False
                frame_buffer.clear()
            else:
                # Start recording
                if current_label is not None:
                    if hand_detected:
                        recording = True
                        frame_buffer.clear()
                        print(f"  📸 Recording '{SEQUENCE_LABELS[current_label]}'...")
                    else:
                        print("  ⚠️  No hand detected - show your hand!")
                else:
                    print("  ⚠️  Select a sign first (press 1, 2, S, T, O, H, or G)")
        elif key == ord('1'):
            current_label = 0  # I_LOVE_YOU
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('2'):
            current_label = 1  # THANK_YOU
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('s') or key == ord('S'):
            current_label = 5  # 6_7 (index 5, since 0-indexed)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('t') or key == ord('T'):
            current_label = 1  # THANK_YOU (same as key 2)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('o') or key == ord('O'):
            current_label = 6  # OK (index 6)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('h') or key == ord('H'):
            current_label = 7  # HELLO (index 7)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('g') or key == ord('G'):
            current_label = 8  # GOODBYE (index 8)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('3') or key == ord('x') or key == ord('X'):
            current_label = 2  # SIGMA (index 2)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('4') or key == ord('b') or key == ord('B'):
            current_label = 3  # BADDIE (index 3)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")
        elif key == ord('5') or key == ord('r') or key == ord('R'):
            current_label = 4  # RIZZ (index 4)
            print(f"  🔤 Selected: {SEQUENCE_LABELS[current_label]}")

    # Save on exit
    if sequences_data:
        save_dataset(sequences_data, labels_data, DATASET_PATH)

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("\n👋 Done! Run 'python train_lstm_model.py' to train your LSTM model.")


if __name__ == "__main__":
    main()

