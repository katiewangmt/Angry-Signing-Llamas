"""Export a fixed raw-landmark fixture and its Python-normalized feature vector."""
import os, json, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "asl-detector"))
from landmarks import extract_landmarks_new  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(OUT, exist_ok=True)

rng = np.random.default_rng(42)
raw = rng.uniform(-1, 1, size=(21, 3)).astype(np.float64)  # fake but fixed landmarks

class _LM:
    def __init__(self, x, y, z): self.x, self.y, self.z = x, y, z

hand = [_LM(*row) for row in raw]
vec = extract_landmarks_new(hand)  # shape (63,)

with open(os.path.join(OUT, "landmarks_raw.json"), "w") as f:
    json.dump([{"x": float(r[0]), "y": float(r[1]), "z": float(r[2])} for r in raw], f)
with open(os.path.join(OUT, "preprocess_expected.json"), "w") as f:
    json.dump([float(v) for v in vec], f)
print("wrote fixtures: landmarks_raw.json, preprocess_expected.json")
