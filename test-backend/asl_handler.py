"""
asl_handler.py — ASL detection session for WebSocket connections.

Each WebSocket connection gets its own ASLDetectionSession with:
- Its own MediaPipe Hands instance (avoids global timestamp bug)
- Reference to shared models (loaded once at startup)
- PredictionSmoother for letter stability
- Word buffer + cooldown for LSTM sequence detection
"""

import numpy as np
import cv2
from collections import deque, Counter

# These will be importable after sys.path is set up in server.py
from landmarks import (
    init_mediapipe_hands,
    extract_landmarks_new,
    ASL_LABELS,
    NUM_FEATURES,
)
from model_lstm import SEQUENCE_LENGTH, SEQUENCE_LABELS

# ── Detection thresholds (matching detect_unified.py) ──────────
STATIC_CONFIDENCE_THRESHOLD = 0.65
STABLE_FRAMES = 8
COOLDOWN_FRAMES = 15

LSTM_CONFIDENCE_THRESHOLD = 0.3
PREDICTION_INTERVAL = 5

WORD_TO_LETTER = {
    "THANK_YOU": "T",
    "OK": "O",
    "HELLO": "H",
    "GOODBYE": "G",
    "I_LOVE_YOU": "I",
    "6_7": "6",
}


class PredictionSmoother:
    """Smooths static letter predictions over time."""

    def __init__(self, window_size=12, stable_count=8, cooldown=15):
        self.window = deque(maxlen=window_size)
        self.stable_count = stable_count
        self.cooldown = cooldown
        self.cooldown_counter = 0
        self.last_accepted = None

    def update(self, prediction, confidence):
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if confidence < STATIC_CONFIDENCE_THRESHOLD:
            self.window.append(None)
            return None, 0

        self.window.append(prediction)

        if len(self.window) >= self.stable_count:
            recent = [p for p in self.window if p is not None]
            if len(recent) >= self.stable_count:
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


class ASLDetectionSession:
    """Per-WebSocket-connection ASL detection state."""

    def __init__(self, static_model, lstm_model):
        self.static_model = static_model
        self.lstm_model = lstm_model
        self.mode = "letters"

        # Per-session MediaPipe + timestamp (avoids global _frame_timestamp_ms bug)
        self.hands = init_mediapipe_hands(
            static_mode=False,
            max_hands=1,
            min_detection_conf=0.7,
            min_tracking_conf=0.5,
        )
        self._frame_timestamp_ms = 0

        # Letter smoothing
        self.smoother = PredictionSmoother(
            window_size=12,
            stable_count=STABLE_FRAMES,
            cooldown=COOLDOWN_FRAMES,
        )

        # Word detection state
        self.word_buffer = deque(maxlen=SEQUENCE_LENGTH)
        self.frame_count = 0
        self.current_word_pred = None
        self.current_word_conf = 0.0
        self.last_word_accepted = None
        self.word_cooldown = 0

    def set_mode(self, mode):
        if mode in ("letters", "words"):
            self.mode = mode
            self.smoother.reset()
            self.word_buffer.clear()
            self.current_word_pred = None
            self.current_word_conf = 0.0
            self.last_word_accepted = None
            self.word_cooldown = 0

    def process_frame(self, jpeg_bytes):
        """
        Decode a JPEG frame and run detection.

        Returns a list of result dicts to send to the client.
        Each dict has a "type" key ("detection" or "status").
        """
        import mediapipe as mp

        # Decode JPEG
        img_array = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is None:
            return [{"type": "status", "hand_detected": False}]

        # Mirror the frame — model was trained on mirrored (selfie-view) frames
        frame = cv2.flip(frame, 1)

        self.frame_count += 1
        results_out = []

        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._frame_timestamp_ms += 33  # ~30fps stepping
        mp_results = self.hands.detect_for_video(mp_image, self._frame_timestamp_ms)

        hand_detected = bool(
            mp_results.hand_landmarks and len(mp_results.hand_landmarks) > 0
        )

        if hand_detected:
            hand = mp_results.hand_landmarks[0]
            landmarks = extract_landmarks_new(hand)
        else:
            landmarks = None

        # Always send hand status
        results_out.append({"type": "status", "hand_detected": hand_detected})

        # ── Letter detection ──
        if self.mode == "letters" and self.static_model is not None:
            if hand_detected and landmarks is not None:
                input_data = landmarks.reshape(1, -1)
                prediction = self.static_model.predict(input_data, verbose=0)[0]
                letter_pred = int(np.argmax(prediction))
                letter_conf = float(prediction[letter_pred])

                accepted, conf = self.smoother.update(letter_pred, letter_conf)
                if accepted is not None:
                    letter = ASL_LABELS[accepted]
                    results_out.append(
                        {
                            "type": "detection",
                            "kind": "letter",
                            "value": letter,
                            "confidence": round(conf, 3),
                        }
                    )
            else:
                self.smoother.update(None, 0)

        # ── Word detection ──
        elif self.mode == "words" and self.lstm_model is not None:
            if hand_detected and landmarks is not None:
                self.word_buffer.append(landmarks)
            elif len(self.word_buffer) > 0:
                self.word_buffer.append(self.word_buffer[-1])

            if len(self.word_buffer) == SEQUENCE_LENGTH:
                if self.frame_count % PREDICTION_INTERVAL == 0:
                    try:
                        sequence = np.array(
                            [list(self.word_buffer)], dtype=np.float32
                        )
                        predictions = self.lstm_model.predict(
                            sequence, verbose=0
                        )[0]
                        self.current_word_pred = int(np.argmax(predictions))
                        self.current_word_conf = float(
                            predictions[self.current_word_pred]
                        )
                    except Exception:
                        pass

            if self.word_cooldown > 0:
                self.word_cooldown -= 1

            if (
                self.current_word_pred is not None
                and self.current_word_conf >= LSTM_CONFIDENCE_THRESHOLD
                and self.current_word_pred != self.last_word_accepted
                and self.word_cooldown == 0
            ):
                word_name = SEQUENCE_LABELS[self.current_word_pred]
                display = WORD_TO_LETTER.get(word_name, word_name)
                self.last_word_accepted = self.current_word_pred
                self.word_cooldown = 30
                results_out.append(
                    {
                        "type": "detection",
                        "kind": "word",
                        "value": display,
                        "word": word_name,
                        "confidence": round(self.current_word_conf, 3),
                    }
                )

        return results_out

    def cleanup(self):
        """Release MediaPipe resources."""
        try:
            self.hands.close()
        except Exception:
            pass
