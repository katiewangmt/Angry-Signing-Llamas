"""
landmarks.py — MediaPipe hand landmark extraction utilities

Extracts and normalizes 21 hand landmarks (63 features) from images/frames.
Landmarks are normalized relative to the wrist position for translation invariance,
and scaled by the hand bounding box size for scale invariance.
"""

import numpy as np

# MediaPipe hand landmark indices for reference
LANDMARK_NAMES = [
    "WRIST",
    "THUMB_CMC", "THUMB_MCP", "THUMB_IP", "THUMB_TIP",
    "INDEX_MCP", "INDEX_PIP", "INDEX_DIP", "INDEX_TIP",
    "MIDDLE_MCP", "MIDDLE_PIP", "MIDDLE_DIP", "MIDDLE_TIP",
    "RING_MCP", "RING_PIP", "RING_DIP", "RING_TIP",
    "PINKY_MCP", "PINKY_PIP", "PINKY_DIP", "PINKY_TIP",
]

NUM_LANDMARKS = 21
NUM_FEATURES = NUM_LANDMARKS * 3  # x, y, z per landmark = 63 features

ASL_LABELS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
NUM_CLASSES = len(ASL_LABELS)


def init_mediapipe_hands(static_mode=False, max_hands=1, min_detection_conf=0.7, min_tracking_conf=0.5):
    """Initialize MediaPipe Hands solution using the new task API."""
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    
    # Download model if needed (it's bundled with mediapipe)
    base_options = python.BaseOptions(model_asset_path=get_hand_landmarker_model_path())
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO if not static_mode else vision.RunningMode.IMAGE,
        num_hands=max_hands,
        min_hand_detection_confidence=min_detection_conf,
        min_tracking_confidence=min_tracking_conf,
    )
    return vision.HandLandmarker.create_from_options(options)


def get_hand_landmarker_model_path():
    """Get or download the hand landmarker model."""
    import os
    import urllib.request
    
    model_path = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")
    if not os.path.exists(model_path):
        print("📥 Downloading hand landmarker model...")
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        urllib.request.urlretrieve(url, model_path)
        print("✅ Model downloaded")
    return model_path


def extract_landmarks(hand_landmarks) -> np.ndarray:
    """
    Extract and normalize 21 hand landmarks from a MediaPipe hand result.

    Normalization:
    1. Subtract wrist position (translation invariance)
    2. Scale by max distance from wrist (scale invariance)

    Returns:
        np.ndarray of shape (63,) — flattened [x0,y0,z0, x1,y1,z1, ...]
    """
    coords = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark])

    # Normalize: translate to wrist origin
    wrist = coords[0].copy()
    coords -= wrist

    # Normalize: scale by max distance from wrist
    max_dist = np.max(np.linalg.norm(coords, axis=1))
    if max_dist > 0:
        coords /= max_dist

    return coords.flatten()


_frame_timestamp_ms = 0

def extract_from_frame(frame, hands_model):
    """
    Process an OpenCV BGR frame and extract hand landmarks.

    Args:
        frame: BGR image (numpy array)
        hands_model: Initialized MediaPipe HandLandmarker

    Returns:
        (landmarks, results)
        landmarks: np.ndarray of shape (63,) or None if no hand detected
        results: MediaPipe results object for drawing
    """
    global _frame_timestamp_ms
    import cv2
    import mediapipe as mp
    
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    
    _frame_timestamp_ms += 33  # ~30fps
    results = hands_model.detect_for_video(mp_image, _frame_timestamp_ms)

    if results.hand_landmarks and len(results.hand_landmarks) > 0:
        hand = results.hand_landmarks[0]
        landmarks = extract_landmarks_new(hand)
        return landmarks, results
    return None, results


def extract_landmarks_new(hand_landmarks) -> np.ndarray:
    """
    Extract and normalize landmarks from new MediaPipe task API format.
    """
    coords = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks])

    # Normalize: translate to wrist origin
    wrist = coords[0].copy()
    coords -= wrist

    # Normalize: scale by max distance from wrist
    max_dist = np.max(np.linalg.norm(coords, axis=1))
    if max_dist > 0:
        coords /= max_dist

    return coords.flatten()


def draw_landmarks_on_frame(frame, results):
    """Draw MediaPipe hand landmarks on a frame using new task API."""
    import cv2

    if not results.hand_landmarks:
        return frame
    
    h, w = frame.shape[:2]
    
    # Hand connections for drawing
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),  # Index
        (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
        (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
        (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
        (5, 9), (9, 13), (13, 17),  # Palm
    ]
    
    for hand_landmarks in results.hand_landmarks:
        # Draw connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            start = hand_landmarks[start_idx]
            end = hand_landmarks[end_idx]
            start_point = (int(start.x * w), int(start.y * h))
            end_point = (int(end.x * w), int(end.y * h))
            cv2.line(frame, start_point, end_point, (255, 255, 255), 2)
        
        # Draw landmarks
        for lm in hand_landmarks:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 5, (0, 255, 128), -1)
            cv2.circle(frame, (cx, cy), 5, (0, 200, 100), 2)
    
    return frame


def augment_landmarks(landmarks: np.ndarray, num_augmented=5, noise_std=0.02, rotation_range=15) -> list:
    """
    Generate augmented versions of landmark data for more robust training.

    Augmentations:
    - Gaussian noise on coordinates
    - Small 2D rotation around wrist
    - Minor scale jitter

    Args:
        landmarks: shape (63,) normalized landmark vector
        num_augmented: number of augmented samples to generate
        noise_std: standard deviation of Gaussian noise
        rotation_range: max rotation in degrees

    Returns:
        List of augmented landmark arrays, each shape (63,)
    """
    augmented = []
    coords = landmarks.reshape(21, 3)

    for _ in range(num_augmented):
        aug = coords.copy()

        # Add Gaussian noise
        aug += np.random.normal(0, noise_std, aug.shape)

        # Random 2D rotation (x, y plane)
        angle = np.radians(np.random.uniform(-rotation_range, rotation_range))
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rot_matrix = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        aug[:, :2] = aug[:, :2] @ rot_matrix.T

        # Random scale jitter (±10%)
        scale = np.random.uniform(0.9, 1.1)
        aug *= scale

        # Re-normalize
        max_dist = np.max(np.linalg.norm(aug, axis=1))
        if max_dist > 0:
            aug /= max_dist

        augmented.append(aug.flatten())

    return augmented
