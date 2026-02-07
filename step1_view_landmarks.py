"""
Step 1: View hand landmarks live from your webcam.
Press 'q' to quit.

IMPORTANT - Mac users:
  1. Always run with: python3.12 (NOT /usr/bin/python3)
  2. First run may trigger a camera permission popup - click Allow
  3. If camera fails, quit Terminal (Cmd+Q), reopen, and run again
"""

import cv2
import mediapipe as mp
import time
import sys

# --- Set up MediaPipe Hands ---
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5,
)

# --- Try to open webcam with retries ---
print("Attempting to open webcam...")
print("(If you see a permission popup, click ALLOW, then restart this script)")
print()

cap = None
for attempt in range(5):
    cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
    time.sleep(1)  # Give macOS time to initialize camera

    if cap.isOpened():
        # Try to actually read a frame to confirm it works
        ret, test_frame = cap.read()
        if ret and test_frame is not None:
            print(f"Camera opened successfully on attempt {attempt + 1}!")
            break
        else:
            print(f"Attempt {attempt + 1}: Camera opened but can't read frames. Retrying...")
            cap.release()
            cap = None
    else:
        print(f"Attempt {attempt + 1}: Camera not ready. Retrying...")
        if cap:
            cap.release()
        cap = None
    time.sleep(2)

if cap is None or not cap.isOpened():
    print()
    print("=" * 60)
    print("CAMERA COULD NOT OPEN. Try these steps:")
    print()
    print("1. Make sure you're running with python3.12:")
    print("   python3.12 step1_view_landmarks.py")
    print()
    print("2. QUIT Terminal completely (Cmd+Q)")
    print("3. Open System Settings > Privacy & Security > Camera")
    print("4. Make sure Terminal is toggled ON")
    print("5. Reopen Terminal and run the script again")
    print()
    print("6. If Terminal isn't listed, try running this first:")
    print("   tccutil reset Camera")
    print("   Then quit and reopen Terminal and run again.")
    print("=" * 60)
    sys.exit(1)

print()
print("Hold up your hand in front of the camera.")
print("You should see 21 colored dots on your hand.")
print("Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        continue  # Skip bad frames instead of crashing

    # Flip so it looks like a mirror
    frame = cv2.flip(frame, 1)

    # MediaPipe needs RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    # Draw landmarks if a hand is found
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
            )
        cv2.putText(frame, "Hand detected!", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(frame, "No hand detected", (10, 30),
                     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("ASL Reader - Step 1: View Landmarks", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Done!")