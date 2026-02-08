"""
detect_sequence.py — Real-time ASL sequence detection using LSTM model

Usage:
    python detect_sequence.py

Uses the trained LSTM model to detect sequence-based ASL signs like
"I love you" and "Thank you" in real-time from webcam.
"""

import os
import cv2
import numpy as np
from collections import deque
from landmarks import (
    init_mediapipe_hands,
    extract_from_frame,
    draw_landmarks_on_frame,
    NUM_FEATURES,
)
from model_lstm import load_trained_model, SEQUENCE_LENGTH, SEQUENCE_LABELS

# ------- Configuration -------
MODEL_PATH = "asl_lstm_model.keras"
WEBCAM_INDEX = 0
WINDOW_NAME = "ASL Sequence Detector"
CONFIDENCE_THRESHOLD = 0.3  # Minimum confidence to display prediction (lowered for small datasets)
PREDICTION_INTERVAL = 5  # Make prediction every N frames when buffer is full


def main():
    print("=" * 50)
    print("  🤟 ASL Sequence Detector")
    print("=" * 50)
    print("\nLoading model...")

    # Load model
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Model not found at '{MODEL_PATH}'")
        print("   Run 'python train_lstm_model.py' first to train the model.")
        return

    model = load_trained_model(MODEL_PATH)
    print("✅ Model loaded")

    # Initialize
    hands = init_mediapipe_hands(static_mode=False, max_hands=1, min_detection_conf=0.7)
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Could not open webcam!")
        return

    # Frame buffer for sequence
    frame_buffer = deque(maxlen=SEQUENCE_LENGTH)
    current_prediction = None  # (pred_class, confidence)
    frame_count = 0

    print("\n📷 Webcam ready. Show your hand and perform a sign!\n")
    print("Press ESC to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Mirror the frame
        frame = cv2.flip(frame, 1)

        # Extract landmarks
        landmarks, results = extract_from_frame(frame, hands)
        hand_detected = landmarks is not None

        # Draw hand skeleton
        if results.hand_landmarks:
            frame = draw_landmarks_on_frame(frame, results)

        # Update frame buffer
        if hand_detected:
            frame_buffer.append(landmarks)
        elif len(frame_buffer) > 0:
            # Pad with last frame if hand lost
            frame_buffer.append(frame_buffer[-1])

        # Make prediction continuously when buffer is full
        if len(frame_buffer) == SEQUENCE_LENGTH:
            # Predict every PREDICTION_INTERVAL frames for smoother updates
            if frame_count % PREDICTION_INTERVAL == 0:
                try:
                    # Prepare sequence
                    sequence = np.array([list(frame_buffer)], dtype=np.float32)
                    
                    # Predict
                    predictions = model.predict(sequence, verbose=0)[0]
                    pred_class = np.argmax(predictions)
                    confidence = predictions[pred_class]
                    
                    current_prediction = (pred_class, confidence)
                except Exception as e:
                    print(f"Prediction error: {e}")
                    current_prediction = None

        # Display prediction
        h, w = frame.shape[:2]
        
        # Always show header bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        if current_prediction:
            pred_class, confidence = current_prediction
            sign_name = SEQUENCE_LABELS[pred_class]
            
            # Color based on confidence
            if confidence >= 0.7:
                text_color = (0, 255, 128)  # Green - high confidence
            elif confidence >= 0.5:
                text_color = (0, 255, 255)  # Yellow - medium confidence
            else:
                text_color = (128, 128, 128)  # Gray - low confidence
            
            # Always display, regardless of threshold
            cv2.putText(frame, f"Sign: {sign_name}", (15, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, text_color, 2)
            cv2.putText(frame, f"Confidence: {confidence:.1%}", (15, 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            
            # Draw confidence bar
            bar_width = int(confidence * (w - 30))
            bar_color = (0, 255, 0) if confidence >= 0.7 else (0, 255, 255) if confidence >= 0.5 else (128, 128, 128)
            cv2.rectangle(frame, (15, 90), (15 + bar_width, 100), bar_color, -1)
            
            # Show threshold indicator
            threshold_x = int(CONFIDENCE_THRESHOLD * (w - 30)) + 15
            cv2.line(frame, (threshold_x, 85), (threshold_x, 105), (255, 255, 255), 2)
        else:
            # No prediction yet
            if len(frame_buffer) < SEQUENCE_LENGTH:
                cv2.putText(frame, "Collecting frames...", (15, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)
                cv2.putText(frame, f"Buffer: {len(frame_buffer)}/{SEQUENCE_LENGTH}", (15, 75),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            else:
                cv2.putText(frame, "Processing...", (15, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (128, 128, 128), 2)

        # Draw bottom status bar
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 60), (w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)
        
        status_text = f"Buffer: {len(frame_buffer)}/{SEQUENCE_LENGTH}"
        status_color = (0, 255, 0) if len(frame_buffer) == SEQUENCE_LENGTH else (128, 128, 128)
        cv2.putText(frame, status_text, (15, h - 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        hand_status = "✓ Hand Detected" if hand_detected else "✗ No Hand"
        hand_color = (0, 255, 0) if hand_detected else (0, 0, 255)
        cv2.putText(frame, hand_status, (15, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, hand_color, 2)
        
        # Instructions
        cv2.putText(frame, "Press ESC to quit", (w - 180, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        cv2.imshow(WINDOW_NAME, frame)

        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("\n👋 Done!")


if __name__ == "__main__":
    main()

