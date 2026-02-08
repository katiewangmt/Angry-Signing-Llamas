
"""
detect.py — Real-time ASL sign language detection

Usage:
    python detect.py

Opens your webcam and detects ASL hand signs in real-time using
MediaPipe for hand tracking and a trained TensorFlow model for classification.

Controls:
    - SPACE → Add a space to the sentence
    - BACKSPACE → Delete last character
    - C → Clear the sentence
    - Q → Quit
"""

import cv2
import numpy as np
import time
from collections import deque

from landmarks import (
    init_mediapipe_hands,
    extract_from_frame,
    draw_landmarks_on_frame,
    ASL_LABELS,
)
from model import load_trained_model

# ------- Configuration -------
MODEL_PATH = "asl_model.keras"
WEBCAM_INDEX = 0
CONFIDENCE_THRESHOLD = 0.65   # Minimum confidence to accept a prediction
STABLE_FRAMES = 8             # Frames a letter must be stable before accepting
COOLDOWN_FRAMES = 15          # Frames to wait between letter acceptances
WINDOW_NAME = "ASL Detector"


class PredictionSmoother:
    """
    Smooths predictions over time to avoid flickering.

    Uses a sliding window of recent predictions and only accepts
    a letter when it's been consistently predicted for STABLE_FRAMES.
    """

    def __init__(self, window_size=12, stable_count=8, cooldown=15):
        self.window = deque(maxlen=window_size)
        self.stable_count = stable_count
        self.cooldown = cooldown
        self.cooldown_counter = 0
        self.last_accepted = None

    def update(self, prediction, confidence):
        """
        Add a prediction and return the accepted letter if stable.

        Returns:
            (letter, confidence) if accepted, (None, 0) otherwise
        """
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if confidence < CONFIDENCE_THRESHOLD:
            self.window.append(None)
            return None, 0

        self.window.append(prediction)

        # Check if the most common recent prediction is stable enough
        if len(self.window) >= self.stable_count:
            recent = [p for p in self.window if p is not None]
            if len(recent) >= self.stable_count:
                # Most common prediction
                from collections import Counter
                counter = Counter(recent)
                most_common, count = counter.most_common(1)[0]

                if count >= self.stable_count and self.cooldown_counter == 0:
                    if most_common != self.last_accepted:
                        self.last_accepted = most_common
                        self.cooldown_counter = self.cooldown
                        self.window.clear()
                        return most_common, confidence

        return None, 0

    def reset(self):
        self.window.clear()
        self.cooldown_counter = 0
        self.last_accepted = None


def draw_detection_ui(frame, current_pred, confidence, sentence, fps, hand_detected):
    """Draw the detection UI overlay."""
    h, w = frame.shape[:2]

    # --- Top bar: prediction display ---
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 100), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    # Big predicted letter
    if current_pred is not None and confidence > CONFIDENCE_THRESHOLD:
        letter = ASL_LABELS[current_pred]

        # Letter with confidence bar
        cv2.putText(frame, letter, (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 2.8, (0, 255, 128), 4)

        # Confidence bar
        bar_x = 110
        bar_w = 200
        bar_h = 20
        bar_y = 65
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h),
                       (60, 60, 60), -1)
        fill_w = int(bar_w * confidence)
        color = (0, 255, 128) if confidence > 0.8 else (0, 255, 255) if confidence > 0.6 else (0, 128, 255)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h),
                       color, -1)
        cv2.putText(frame, f"{confidence:.0%}", (bar_x + bar_w + 10, bar_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Top 1 label
        cv2.putText(frame, "Detected Sign", (bar_x, bar_y - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    else:
        status = "Show ASL sign..." if hand_detected else "No hand detected"
        cv2.putText(frame, status, (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)

    # FPS counter
    cv2.putText(frame, f"{fps:.0f} FPS", (w - 100, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

    # --- Bottom bar: sentence builder ---
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - 70), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay2, 0.8, frame, 0.2, 0, frame)

    # Sentence text
    display_sentence = sentence if sentence else "Signs will appear here..."
    sent_color = (255, 255, 255) if sentence else (80, 80, 80)
    cv2.putText(frame, display_sentence[-50:], (15, h - 35),  # Last 50 chars
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, sent_color, 2)

    # Controls hint
    cv2.putText(frame, "[SPACE] Space  [BKSP] Delete  [C] Clear  [Q] Quit",
                (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 100, 100), 1)

    return frame


def main():
    print("=" * 50)
    print("  🤟 ASL Real-Time Detector")
    print("=" * 50)

    # Load model
    print("\n📦 Loading model...")
    try:
        model = load_trained_model(MODEL_PATH)
        print("  ✅ Model loaded successfully")
    except Exception as e:
        print(f"  ❌ Could not load model from '{MODEL_PATH}': {e}")
        print("  Run 'python train_model.py' first!")
        return

    # Initialize MediaPipe
    hands = init_mediapipe_hands(
        static_mode=False,
        max_hands=1,
        min_detection_conf=0.7,
        min_tracking_conf=0.5,
    )

    # Initialize webcam
    cap = cv2.VideoCapture(WEBCAM_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ Could not open webcam!")
        return

    smoother = PredictionSmoother(
        window_size=12,
        stable_count=STABLE_FRAMES,
        cooldown=COOLDOWN_FRAMES,
    )

    sentence = ""
    fps = 0
    frame_times = deque(maxlen=30)

    print("\n🎥 Detection running! Show ASL signs to your webcam.\n")

    while True:
        frame_start = time.time()

        ret, frame = cap.read()
        if not ret:
            break

        # Mirror
        frame = cv2.flip(frame, 1)

        # Extract landmarks
        landmarks, results = extract_from_frame(frame, hands)
        hand_detected = landmarks is not None

        # Draw hand skeleton
        if results.hand_landmarks:
            frame = draw_landmarks_on_frame(frame, results)

        # Predict
        current_pred = None
        confidence = 0.0

        if hand_detected:
            # Model inference
            input_data = landmarks.reshape(1, -1)
            prediction = model.predict(input_data, verbose=0)[0]
            current_pred = np.argmax(prediction)
            confidence = prediction[current_pred]

            # Smooth prediction
            accepted_letter, accepted_conf = smoother.update(current_pred, confidence)
            if accepted_letter is not None:
                letter = ASL_LABELS[accepted_letter]
                sentence += letter
                print(f"  ✅ Detected: {letter}  |  Sentence: {sentence}")
        else:
            smoother.update(None, 0)

        # Calculate FPS
        frame_times.append(time.time() - frame_start)
        if len(frame_times) > 0:
            fps = 1.0 / (sum(frame_times) / len(frame_times))

        # Draw UI
        frame = draw_detection_ui(frame, current_pred, confidence, sentence, fps, hand_detected)

        cv2.imshow(WINDOW_NAME, frame)

        # Handle keys
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            sentence += " "
            smoother.reset()
            print(f"  [space]  |  Sentence: {sentence}")
        elif key == 8 or key == 127:  # Backspace
            sentence = sentence[:-1]
            print(f"  [delete] |  Sentence: {sentence}")
        elif key == ord('c'):
            sentence = ""
            smoother.reset()
            print("  [clear]")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()

    if sentence:
        print(f"\n📝 Final sentence: {sentence}")
    print("👋 Goodbye!")


if __name__ == "__main__":
    main()
