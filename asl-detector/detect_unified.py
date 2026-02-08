"""
detect_unified.py — Unified ASL detection for both letters and words

Usage:
    python detect_unified.py

Detects both:
- Static ASL letters (A-Z) using the static model
- Sequence-based words (I love you, Thank you) using the LSTM model

Controls:
    - SPACE → Add a space to the sentence
    - BACKSPACE → Delete last character/word
    - C → Clear the sentence
    - T → Toggle between letter mode, word mode, or both
    - Q → Quit
"""

import os
import cv2
import numpy as np
import time
from collections import deque

from landmarks import (
    init_mediapipe_hands,
    extract_from_frame,
    draw_landmarks_on_frame,
    ASL_LABELS,
    NUM_FEATURES,
)

# Try to load both models
try:
    from model import load_trained_model as load_static_model
    STATIC_MODEL_AVAILABLE = True
except:
    STATIC_MODEL_AVAILABLE = False

try:
    from model_lstm import load_trained_model as load_lstm_model, SEQUENCE_LENGTH, SEQUENCE_LABELS
    LSTM_MODEL_AVAILABLE = True
except:
    LSTM_MODEL_AVAILABLE = False

# ------- Configuration -------
STATIC_MODEL_PATH = "asl_model.keras"
LSTM_MODEL_PATH = "asl_lstm_model.keras"
WEBCAM_INDEX = 0
WINDOW_NAME = "ASL Unified Detector"

# Static letter detection settings
STATIC_CONFIDENCE_THRESHOLD = 0.65
STABLE_FRAMES = 8
COOLDOWN_FRAMES = 15

# Sequence word detection settings
LSTM_CONFIDENCE_THRESHOLD = 0.3
PREDICTION_INTERVAL = 5

# Detection modes
MODE_LETTERS = "letters"
MODE_WORDS = "words"
MODE_BOTH = "both"


class PredictionSmoother:
    """Smooths static letter predictions over time."""

    def __init__(self, window_size=12, stable_count=8, cooldown=15):
        self.window = deque(maxlen=window_size)
        self.stable_count = stable_count
        self.cooldown = cooldown
        self.cooldown_counter = 0
        self.last_accepted = None

    def update(self, prediction, confidence):
        """Add a prediction and return the accepted letter if stable."""
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if confidence < STATIC_CONFIDENCE_THRESHOLD:
            self.window.append(None)
            return None, 0

        self.window.append(prediction)

        if len(self.window) >= self.stable_count:
            recent = [p for p in self.window if p is not None]
            if len(recent) >= self.stable_count:
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


def draw_unified_ui(frame, mode, letter_pred, letter_conf, word_pred, word_conf,
                    sentence, fps, hand_detected, letter_buffer, word_buffer):
    """Draw the unified detection UI overlay."""
    h, w = frame.shape[:2]

    # --- Top bar: predictions ---
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 140), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

    y_offset = 30

    # Mode indicator
    mode_colors = {
        MODE_LETTERS: (0, 255, 255),
        MODE_WORDS: (255, 0, 255),
        MODE_BOTH: (0, 255, 128)
    }
    mode_text = f"Mode: {mode.upper()}"
    cv2.putText(frame, mode_text, (w - 200, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_colors.get(mode, (255, 255, 255)), 2)

    # Letter prediction
    if mode in [MODE_LETTERS, MODE_BOTH]:
        if letter_pred is not None and letter_conf > STATIC_CONFIDENCE_THRESHOLD:
            letter = ASL_LABELS[letter_pred]
            cv2.putText(frame, f"Letter: {letter}", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)
            cv2.putText(frame, f"{letter_conf:.0%}", (20, y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        else:
            cv2.putText(frame, "Letter: --", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 100, 100), 2)
        y_offset += 60

    # Word prediction
    if mode in [MODE_WORDS, MODE_BOTH]:
        if word_pred is not None:
            word_name = SEQUENCE_LABELS[word_pred] if LSTM_MODEL_AVAILABLE else "Unknown"
            # Color based on confidence
            if word_conf >= 0.7:
                word_color = (0, 255, 128)
            elif word_conf >= 0.5:
                word_color = (0, 255, 255)
            else:
                word_color = (128, 128, 128)
            
            cv2.putText(frame, f"Word: {word_name}", (20, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, word_color, 2)
            cv2.putText(frame, f"{word_conf:.0%}", (20, y_offset + 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            
            # Word buffer status
            buffer_text = f"Buffer: {len(word_buffer)}/{SEQUENCE_LENGTH}"
            buffer_color = (0, 255, 0) if len(word_buffer) == SEQUENCE_LENGTH else (128, 128, 128)
            cv2.putText(frame, buffer_text, (20, y_offset + 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, buffer_color, 1)
        else:
            if len(word_buffer) < SEQUENCE_LENGTH:
                cv2.putText(frame, f"Word: Collecting... ({len(word_buffer)}/{SEQUENCE_LENGTH})", 
                           (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            else:
                cv2.putText(frame, "Word: Processing...", (20, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)

    # FPS counter
    cv2.putText(frame, f"{fps:.0f} FPS", (w - 100, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)

    # Hand detection status
    hand_status = "✓ Hand" if hand_detected else "✗ No Hand"
    hand_color = (0, 255, 0) if hand_detected else (0, 0, 255)
    cv2.putText(frame, hand_status, (w - 200, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, hand_color, 1)

    # --- Bottom bar: sentence builder ---
    overlay2 = frame.copy()
    cv2.rectangle(overlay2, (0, h - 80), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay2, 0.8, frame, 0.2, 0, frame)

    # Sentence text
    display_sentence = sentence if sentence else "Signs will appear here..."
    sent_color = (255, 255, 255) if sentence else (80, 80, 80)
    cv2.putText(frame, display_sentence[-60:], (15, h - 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, sent_color, 2)

    # Controls hint
    controls = "[CTRL]/[L] Letters  [CTRL]/[W] Words  [SPACE] Space  [BKSP] Delete  [C] Clear  [Q] Quit"
    cv2.putText(frame, controls, (15, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 100, 100), 1)

    return frame


def main():
    print("=" * 50)
    print("  🤟 ASL Unified Detector (Letters + Words)")
    print("=" * 50)

    # Check available models
    static_model = None
    lstm_model = None

    if STATIC_MODEL_AVAILABLE:
        print("\n📦 Loading static letter model...")
        if os.path.exists(STATIC_MODEL_PATH):
            try:
                # Try loading with safe_mode=False to handle quantization_config issues
                import tensorflow as tf
                static_model = tf.keras.models.load_model(STATIC_MODEL_PATH, safe_mode=False)
                print("  ✅ Static model loaded")
            except Exception as e:
                try:
                    # Fallback: load without compiling, then recompile
                    import tensorflow as tf
                    static_model = tf.keras.models.load_model(STATIC_MODEL_PATH, compile=False)
                    static_model.compile(
                        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                        loss="sparse_categorical_crossentropy",
                        metrics=["accuracy"],
                    )
                    print("  ✅ Static model loaded (recompiled)")
                except Exception as e2:
                    try:
                        # Another fallback: try loading with custom_objects to ignore quantization_config
                        import tensorflow as tf
                        # Create a custom layer that ignores quantization_config
                        class IgnoreQuantizationLayer(tf.keras.layers.Layer):
                            def __init__(self, **kwargs):
                                kwargs.pop('quantization_config', None)
                                super().__init__(**kwargs)
                        
                        # Try loading with custom objects
                        static_model = tf.keras.models.load_model(
                            STATIC_MODEL_PATH, 
                            compile=False,
                            custom_objects={'Dense': tf.keras.layers.Dense}
                        )
                        static_model.compile(
                            optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                            loss="sparse_categorical_crossentropy",
                            metrics=["accuracy"],
                        )
                        print("  ✅ Static model loaded (with custom objects)")
                    except Exception as e3:
                        print(f"  ⚠️  Could not load static model: {e}")
                        print(f"     All fallback methods failed. Please retrain the model.")
                        print(f"     Run: python train_model.py")
                        static_model = None
        else:
            print(f"  ⚠️  Static model not found at '{STATIC_MODEL_PATH}'")
            print(f"     Run 'python train_model.py' to train the static letter model")
            static_model = None
    else:
        print("\n⚠️  Static model module not available")
        static_model = None

    if LSTM_MODEL_AVAILABLE:
        print("\n📦 Loading LSTM word model...")
        if os.path.exists(LSTM_MODEL_PATH):
            try:
                lstm_model = load_lstm_model(LSTM_MODEL_PATH)
                print("  ✅ LSTM model loaded")
            except Exception as e:
                print(f"  ⚠️  Could not load LSTM model: {e}")
                lstm_model = None
        else:
            print(f"  ⚠️  LSTM model not found at '{LSTM_MODEL_PATH}'")
            print(f"     Run 'python train_lstm_model.py' to train the LSTM word model")
            lstm_model = None
    else:
        print("\n⚠️  LSTM model module not available")
        lstm_model = None

    # Determine initial mode (default to LETTERS if both available, user can toggle)
    if static_model and lstm_model:
        mode = MODE_LETTERS  # Start with LETTERS mode, user can toggle with CTRL
        print("\n✅ Both models available - starting in LETTERS mode")
        print("   Press CTRL or CTRL+M to switch to WORDS mode")
    elif static_model:
        mode = MODE_LETTERS
        print("\n✅ Static model available - using LETTERS mode")
    elif lstm_model:
        mode = MODE_WORDS
        print("\n✅ LSTM model available - using WORDS mode")
    else:
        print("\n❌ No models available! Please train at least one model.")
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
    frame_count = 0

    # Sequence buffers
    word_buffer = deque(maxlen=SEQUENCE_LENGTH if LSTM_MODEL_AVAILABLE else 0)
    current_word_pred = None
    current_word_conf = 0.0
    last_word_accepted = None
    word_cooldown = 0
    
    # Initialize word prediction variables
    word_pred = None
    word_conf = 0.0

    print("\n🎥 Detection running!")
    print(f"   Mode: {mode.upper()}")
    print("   Press [L] for LETTERS mode or [W] for WORDS mode")
    print("   Or press CTRL/CTRL+M to toggle between modes, Q to quit\n")
    print("   Note: Letters mode outputs A-Z only")
    print("         Words mode maps to letters: T (Thank you), O (OK), H (Hello), G (Goodbye), I (I love you), 6 (6 7)\n")

    while True:
        frame_start = time.time()
        frame_count += 1

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

        # Initialize predictions
        letter_pred = None
        letter_conf = 0.0

        # Static letter detection
        if mode in [MODE_LETTERS, MODE_BOTH] and static_model and hand_detected:
            input_data = landmarks.reshape(1, -1)
            prediction = static_model.predict(input_data, verbose=0)[0]
            letter_pred = np.argmax(prediction)
            letter_conf = prediction[letter_pred]

            # Smooth prediction
            accepted_letter, accepted_conf = smoother.update(letter_pred, letter_conf)
            if accepted_letter is not None:
                letter = ASL_LABELS[accepted_letter]
                # Only add letters A-Z (ensure it's a valid letter)
                if letter.isalpha() and len(letter) == 1:
                    sentence += letter
                    print(f"  ✅ Letter: {letter}  |  Sentence: {sentence}")
                else:
                    print(f"  ⚠️  Invalid letter detected: {letter}")
        elif mode in [MODE_LETTERS, MODE_BOTH]:
            smoother.update(None, 0)

        # Sequence word detection
        if mode in [MODE_WORDS, MODE_BOTH] and lstm_model:
            # Update word buffer
            if hand_detected:
                word_buffer.append(landmarks)
            elif len(word_buffer) > 0:
                word_buffer.append(word_buffer[-1])

            # Make prediction when buffer is full
            if len(word_buffer) == SEQUENCE_LENGTH:
                if frame_count % PREDICTION_INTERVAL == 0:
                    try:
                        sequence = np.array([list(word_buffer)], dtype=np.float32)
                        predictions = lstm_model.predict(sequence, verbose=0)[0]
                        current_word_pred = np.argmax(predictions)
                        current_word_conf = predictions[current_word_pred]
                    except Exception as e:
                        print(f"Word prediction error: {e}")

            # Accept word if confidence is high and not in cooldown
            if word_cooldown > 0:
                word_cooldown -= 1

            if current_word_pred is not None and current_word_conf >= LSTM_CONFIDENCE_THRESHOLD:
                if current_word_pred != last_word_accepted and word_cooldown == 0:
                    word_name = SEQUENCE_LABELS[current_word_pred]
                    # Map words to specific letters
                    word_to_letter = {
                        "THANK_YOU": "T",
                        "OK": "O",
                        "HELLO": "H",
                        "GOODBYE": "G",
                        "I_LOVE_YOU": "I",
                        "6_7": "6",
                    }
                    # Use mapped letter if available, otherwise use first letter of word
                    letter = word_to_letter.get(word_name, word_name[0] if word_name else "?")
                    sentence += letter
                    last_word_accepted = current_word_pred
                    word_cooldown = 30  # Cooldown frames
                    print(f"  ✅ Word: {word_name} → '{letter}'  |  Sentence: {sentence}")

        # Calculate FPS
        frame_times.append(time.time() - frame_start)
        if len(frame_times) > 0:
            fps = 1.0 / (sum(frame_times) / len(frame_times))

        # Draw UI
        frame = draw_unified_ui(
            frame, mode, letter_pred, letter_conf, 
            current_word_pred if mode in [MODE_WORDS, MODE_BOTH] else None, 
            current_word_conf if mode in [MODE_WORDS, MODE_BOTH] else 0.0,
            sentence, fps, hand_detected, 
            deque(), word_buffer
        )

        cv2.imshow(WINDOW_NAME, frame)

        # Handle keys
        key = cv2.waitKey(1)
        key_char = key & 0xFF
        
        # Check for Control key - OpenCV doesn't easily detect Control alone
        # We'll use a workaround: check for Control key by looking at the full key value
        # On some systems, Control key alone generates key code 17
        # We'll also support Ctrl+M as an alternative, and simple L/W keys as fallback
        is_control_pressed = False
        
        # Method 1: Check if key is Control key (code 17)
        if key == 17:
            is_control_pressed = True
        
        # Method 2: Check for Ctrl+M combination (key & 0x4000 checks for Ctrl modifier)
        if key_char == ord('m') and (key & 0x4000):
            is_control_pressed = True
        
        # Method 3: Try to detect Control key state (platform-specific)
        # On macOS/Linux, Control key might be detected differently
        try:
            # Check if Control is in the modifier bits
            if (key & 0x4000) or (key & 0x2000):  # Check for Ctrl or other modifier
                # Only trigger if it's a known Control combination
                if key_char == ord('m') or key == 17:
                    is_control_pressed = True
        except:
            pass
        
        # Toggle mode with Control key or simple L/W keys
        if is_control_pressed or key_char == ord('l') or key_char == ord('L'):
            # Switch to LETTERS mode
            if static_model is not None:
                mode = MODE_LETTERS
                print(f"  🔄 Switched to LETTERS mode")
            else:
                print(f"  ⚠️  Static model not available - cannot use LETTERS mode")
                print(f"     Please train the static model first: python train_model.py")
        elif key_char == ord('w') or key_char == ord('W'):
            # Switch to WORDS mode
            if lstm_model is not None:
                mode = MODE_WORDS
                print(f"  🔄 Switched to WORDS mode")
            else:
                print(f"  ⚠️  LSTM model not available - cannot use WORDS mode")
                print(f"     Please train the LSTM model first: python train_lstm_model.py")
        elif is_control_pressed:
            # Toggle between LETTERS and WORDS mode (original toggle behavior)
            if static_model and lstm_model:
                if mode == MODE_LETTERS:
                    mode = MODE_WORDS
                    print(f"  🔄 Switched to WORDS mode")
                elif mode == MODE_WORDS:
                    mode = MODE_LETTERS
                    print(f"  🔄 Switched to LETTERS mode")
                else:
                    # If in BOTH mode, switch to LETTERS
                    mode = MODE_LETTERS
                    print(f"  🔄 Switched to LETTERS mode")
            elif static_model:
                print(f"  ℹ️  Only LETTERS mode available")
            elif lstm_model:
                print(f"  ℹ️  Only WORDS mode available")
        
        if key_char == ord('q'):
            break
        elif key == ord(' '):
            sentence += " "
            smoother.reset()
            print(f"  [space]  |  Sentence: {sentence}")
        elif key == 8 or key == 127:  # Backspace
            sentence = sentence[:-1]
            smoother.reset()
            print(f"  [delete] |  Sentence: {sentence}")
        elif key == ord('c'):
            sentence = ""
            smoother.reset()
            last_word_accepted = None
            word_cooldown = 0
            print("  [clear]")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()

    if sentence:
        print(f"\n📝 Final sentence: {sentence}")
    print("👋 Goodbye!")


if __name__ == "__main__":
    main()

