# Angry-Signing-Llamas In-Browser Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Angry-Signing-Llamas run entirely in the browser (no backend) so it can be uploaded to the static host ghg.gg.

**Architecture:** Replace the three backend calls (`/ws/asl`, `/api/tts`, `/ws/beat`) with in-browser equivalents that emit the *same* messages the existing game logic already consumes. ASL detection runs via `@mediapipe/tasks-vision` (WASM) + the two Keras models converted to TensorFlow.js; TTS becomes 8 pre-generated bundled clips; Lyria music becomes a bundled royalty-free loop. A build script assembles a flat static `dist/` and zips it with `index.html` at the root.

**Tech Stack:** Vanilla JS (ES modules), `@tensorflow/tfjs`, `@mediapipe/tasks-vision`, Python (build-time model conversion + TTS generation), Node (build-time parity test + dist assembly).

## Global Constraints

- **No off-origin network requests at runtime.** All JS, WASM, models, audio, and the `.task` file are served from the bundle's own origin. No CDN `<script src>`, no `fetch` to any external host, no WebSocket.
- **`index.html` at the zip root.** Final zip is flat: `index.html` + asset folders, no wrapping folder.
- **The shipped zip contains only static assets.** No `server.py`, no `.env`, no API keys, no Python.
- **Detection parity is the acceptance bar.** Ported JS preprocessing + model inference must match the Python backend's output on identical input.
- **Exact ported constants (from `test-backend/asl_handler.py`):** letter smoother `window_size=8, stable_count=4, cooldown=8, confidence_threshold=0.65`; word smoother `window_size=8, stable_count=3, cooldown=10, confidence_threshold=0.3`; `SEQUENCE_LENGTH=30`; `PREDICTION_INTERVAL=1`.
- **Labels (verbatim):** `ASL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"` (26). `SEQUENCE_LABELS = ["I_LOVE_YOU","THANK_YOU","SIGMA","BADDIE","RIZZ","6_7","OK","HELLO","GOODBYE"]` (9). `WORD_TO_LETTER = {THANK_YOU:"T", OK:"O", HELLO:"H", GOODBYE:"G", I_LOVE_YOU:"I", "6_7":"6"}`.
- **Frame is mirrored before detection** (`cv2.flip(frame,1)`); the JS port must feed a horizontally-flipped frame to MediaPipe.
- All work happens in `/Users/katie/ADI2026-1` on branch `static-in-browser-port`.

## File Structure

```
frontend/
  index.html                 # MODIFIED: load ES modules, replace WS calls with engine calls
  detection/
    preprocess.js            # NEW: extract_landmarks_new port (63-feature vector)
    smoother.js              # NEW: PredictionSmoother port
    models.js                # NEW: load TF.js models, run static + LSTM inference
    handLandmarker.js        # NEW: MediaPipe tasks-vision wrapper
    engine.js                # NEW: orchestration loop, emits status/detection messages
    labels.js                # NEW: shared label constants
    models/
      static/model.json      # NEW (generated): converted static model
      lstm/model.json        # NEW (generated): converted LSTM model
    vendor/
      tfjs/tf.min.js         # NEW (vendored): TensorFlow.js
      mediapipe/             # NEW (vendored): tasks-vision js + wasm
    hand_landmarker.task     # NEW (copied from asl-detector/)
  audio/
    tts/*.mp3                # NEW (generated): 8 voice clips
    music/loop.mp3           # NEW (sourced): royalty-free loop
    tts.js                   # NEW: bundled-clip playback (replaces /api/tts)
    music.js                 # NEW: loop playback (replaces /ws/beat)
build/
  convert_models.py          # NEW: Keras -> TF.js conversion
  export_parity_fixture.py   # NEW: dump fixed input + Python model output
  generate_tts.py            # NEW: ElevenLabs -> 8 mp3s (build-time only)
  parity_test.mjs            # NEW: Node parity check (JS vs Python output)
  fixtures/                  # NEW (generated): parity fixtures
  build_dist.mjs             # NEW: assemble flat dist/ and zip it
package.json                 # NEW: dev deps (tfjs, tasks-vision) + scripts
```

---

## PHASE 0 — Vendoring & setup

### Task 0: Install and vendor runtime dependencies

**Files:**
- Create: `package.json`
- Create: `frontend/detection/vendor/tfjs/tf.min.js` (copied)
- Create: `frontend/detection/vendor/mediapipe/` (copied)
- Create: `frontend/detection/hand_landmarker.task` (copied)

**Interfaces:**
- Produces: vendored `tf` global (via `tf.min.js`), MediaPipe `vision_bundle.mjs` + WASM under `vendor/mediapipe/`, and a local `hand_landmarker.task`. Later tasks load these by relative path only.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "angry-signing-llamas-build",
  "private": true,
  "type": "module",
  "scripts": {
    "convert": "python3 build/convert_models.py",
    "fixture": "python3 build/export_parity_fixture.py",
    "parity": "node build/parity_test.mjs",
    "tts": "python3 build/generate_tts.py",
    "dist": "node build/build_dist.mjs"
  },
  "devDependencies": {
    "@tensorflow/tfjs": "4.22.0",
    "@mediapipe/tasks-vision": "0.10.18"
  }
}
```

- [ ] **Step 2: Install dev deps**

Run: `cd /Users/katie/ADI2026-1 && npm install`
Expected: `node_modules/@tensorflow/tfjs` and `node_modules/@mediapipe/tasks-vision` exist.

- [ ] **Step 3: Vendor the runtime files into the frontend**

```bash
cd /Users/katie/ADI2026-1
mkdir -p frontend/detection/vendor/tfjs frontend/detection/vendor/mediapipe
cp node_modules/@tensorflow/tfjs/dist/tf.min.js frontend/detection/vendor/tfjs/tf.min.js
cp -R node_modules/@mediapipe/tasks-vision/wasm frontend/detection/vendor/mediapipe/wasm
cp node_modules/@mediapipe/tasks-vision/vision_bundle.mjs frontend/detection/vendor/mediapipe/vision_bundle.mjs
cp asl-detector/hand_landmarker.task frontend/detection/hand_landmarker.task
```

- [ ] **Step 4: Verify vendored files exist**

Run: `ls -la frontend/detection/vendor/tfjs/tf.min.js frontend/detection/vendor/mediapipe/vision_bundle.mjs frontend/detection/hand_landmarker.task && ls frontend/detection/vendor/mediapipe/wasm | head`
Expected: all three paths listed; `wasm/` contains `vision_wasm_internal.wasm` and `vision_wasm_internal.js`.

- [ ] **Step 5: Add build artifacts to .gitignore (keep vendored runtime, ignore node_modules)**

Add to `.gitignore`: `node_modules/` and `build/fixtures/`. Do NOT ignore `frontend/detection/vendor/` or `frontend/detection/models/` — those ship.

- [ ] **Step 6: Commit**

```bash
git add package.json package-lock.json .gitignore frontend/detection/vendor frontend/detection/hand_landmarker.task
git commit -m "chore: vendor tfjs + mediapipe tasks-vision for static build"
```

---

## PHASE 1 — Detection spike + VALIDATION GATE

> This phase proves the risky part (model conversion + preprocessing parity) before any further work. **Implementation STOPS after Task 4 for user sign-off.**

### Task 1: Shared labels module

**Files:**
- Create: `frontend/detection/labels.js`

**Interfaces:**
- Produces: `ASL_LABELS` (string[]), `SEQUENCE_LABELS` (string[]), `WORD_TO_LETTER` (object).

- [ ] **Step 1: Create `frontend/detection/labels.js`**

```javascript
// Ported verbatim from asl-detector/landmarks.py and model_lstm.py + asl_handler.py
export const ASL_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
export const SEQUENCE_LABELS = [
  "I_LOVE_YOU", "THANK_YOU", "SIGMA", "BADDIE", "RIZZ", "6_7", "OK", "HELLO", "GOODBYE",
];
export const WORD_TO_LETTER = {
  THANK_YOU: "T", OK: "O", HELLO: "H", GOODBYE: "G", I_LOVE_YOU: "I", "6_7": "6",
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/detection/labels.js
git commit -m "feat: shared ASL label constants for in-browser detection"
```

### Task 2: Landmark preprocessing port (`preprocess.js`) with parity test

**Files:**
- Create: `frontend/detection/preprocess.js`
- Create: `build/export_parity_fixture.py`
- Create: `build/parity_test.mjs`
- Create: `build/fixtures/` (generated)

**Interfaces:**
- Consumes: nothing.
- Produces: `extractLandmarks(landmarks) -> Float32Array(63)` where `landmarks` is an array of 21 `{x,y,z}`.

- [ ] **Step 1: Write `frontend/detection/preprocess.js`** (direct port of `extract_landmarks_new`)

```javascript
// Port of extract_landmarks_new() from asl-detector/landmarks.py
// Input: array of 21 objects with numeric .x .y .z (MediaPipe tasks-vision landmark)
// Output: Float32Array(63) = flattened [x0,y0,z0, x1,y1,z1, ...]
// Normalization: translate to wrist (index 0), scale by max L2 distance from wrist.
export function extractLandmarks(landmarks) {
  const coords = new Array(21);
  const wx = landmarks[0].x, wy = landmarks[0].y, wz = landmarks[0].z;
  let maxDist = 0;
  for (let i = 0; i < 21; i++) {
    const x = landmarks[i].x - wx;
    const y = landmarks[i].y - wy;
    const z = landmarks[i].z - wz;
    coords[i] = [x, y, z];
    const d = Math.sqrt(x * x + y * y + z * z);
    if (d > maxDist) maxDist = d;
  }
  const out = new Float32Array(63);
  for (let i = 0; i < 21; i++) {
    const [x, y, z] = coords[i];
    if (maxDist > 0) {
      out[i * 3] = x / maxDist;
      out[i * 3 + 1] = y / maxDist;
      out[i * 3 + 2] = z / maxDist;
    } else {
      out[i * 3] = x; out[i * 3 + 1] = y; out[i * 3 + 2] = z;
    }
  }
  return out;
}
```

- [ ] **Step 2: Write `build/export_parity_fixture.py`** (deterministic raw landmarks + Python-normalized vector)

```python
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
```

- [ ] **Step 3: Generate the fixture**

Run: `cd /Users/katie/ADI2026-1 && npm run fixture`
Expected: prints "wrote fixtures..."; `build/fixtures/preprocess_expected.json` has 63 numbers.

- [ ] **Step 4: Write `build/parity_test.mjs`** (preprocess section — model section added in Task 3)

```javascript
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { extractLandmarks } from "../frontend/detection/preprocess.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const F = path.join(__dirname, "fixtures");
const TOL = 1e-5;

function assertClose(a, b, tol, label) {
  if (a.length !== b.length) throw new Error(`${label}: length ${a.length} != ${b.length}`);
  let maxErr = 0;
  for (let i = 0; i < a.length; i++) maxErr = Math.max(maxErr, Math.abs(a[i] - b[i]));
  if (maxErr > tol) throw new Error(`${label}: max abs err ${maxErr} > ${tol}`);
  console.log(`PASS ${label} (max abs err ${maxErr.toExponential(2)})`);
}

// --- Preprocess parity ---
const raw = JSON.parse(fs.readFileSync(path.join(F, "landmarks_raw.json"), "utf8"));
const expected = JSON.parse(fs.readFileSync(path.join(F, "preprocess_expected.json"), "utf8"));
const got = Array.from(extractLandmarks(raw));
assertClose(got, expected, TOL, "preprocess");

console.log("ALL PARITY CHECKS PASSED");
```

- [ ] **Step 5: Run the parity test — expect PASS**

Run: `cd /Users/katie/ADI2026-1 && npm run parity`
Expected: `PASS preprocess ...` then `ALL PARITY CHECKS PASSED`. If it fails, fix `preprocess.js` to match Python before continuing.

- [ ] **Step 6: Commit**

```bash
git add frontend/detection/preprocess.js build/export_parity_fixture.py build/parity_test.mjs
git commit -m "feat: port landmark preprocessing with Python-parity test"
```

### Task 3: Convert static model to TF.js + extend parity test to model output

**Files:**
- Create: `build/convert_models.py`
- Create: `frontend/detection/models/static/model.json` (+ weight bins) (generated)
- Modify: `build/export_parity_fixture.py` (append static-model expected output)
- Modify: `build/parity_test.mjs` (add static model check)

**Interfaces:**
- Consumes: `extractLandmarks` (Task 2).
- Produces: converted static model at `frontend/detection/models/static/model.json`; a reusable `loadLocalLayersModel(modelJsonPath)` helper in `parity_test.mjs`.

- [ ] **Step 1: Write `build/convert_models.py`** (robust to Keras 3 via architecture-rebuild fallback)

```python
"""Convert the trained Keras models to TensorFlow.js layers format.

Primary path: tensorflowjs.converters.save_keras_model on the loaded model.
Fallback (if conversion of the .keras file fails): rebuild the architecture from
asl-detector and load weights, then convert the rebuilt model.
"""
import os, sys
DETECTOR = os.path.join(os.path.dirname(__file__), "..", "asl-detector")
sys.path.insert(0, DETECTOR)
OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "detection", "models")

import tensorflow as tf  # noqa: E402
import tensorflowjs as tfjs  # noqa: E402

def convert(keras_path, out_subdir, rebuild_fn=None):
    out_dir = os.path.join(OUT, out_subdir)
    os.makedirs(out_dir, exist_ok=True)
    try:
        model = tf.keras.models.load_model(keras_path, compile=False, safe_mode=False)
        tfjs.converters.save_keras_model(model, out_dir)
        print(f"converted {keras_path} -> {out_dir}")
    except Exception as e:
        if rebuild_fn is None:
            raise
        print(f"direct convert failed ({e}); rebuilding architecture and loading weights")
        model = rebuild_fn()
        model.load_weights(keras_path)
        tfjs.converters.save_keras_model(model, out_dir)
        print(f"converted (rebuilt) {keras_path} -> {out_dir}")

def _rebuild_static():
    from model import create_asl_model
    return create_asl_model()

def _rebuild_lstm():
    from model_lstm import create_lstm_model
    return create_lstm_model()

if __name__ == "__main__":
    convert(os.path.join(DETECTOR, "asl_model.keras"), "static", _rebuild_static)
    convert(os.path.join(DETECTOR, "asl_lstm_model.keras"), "lstm", _rebuild_lstm)
```

- [ ] **Step 2: Run the conversion**

Run: `cd /Users/katie/ADI2026-1 && npm run convert`
Expected: `frontend/detection/models/static/model.json` and `frontend/detection/models/lstm/model.json` both exist (each with a `.bin` weights file). If a direct convert fails, the rebuild fallback should succeed and say so.

- [ ] **Step 3: Append static-model expected output to `build/export_parity_fixture.py`**

Add before the final print:

```python
    # Static model expected output on the fixed vector
    from model import load_trained_model as _load_static
    static = _load_static(os.path.join(os.path.dirname(__file__), "..", "asl-detector", "asl_model.keras"))
    probs = static.predict(vec.reshape(1, -1), verbose=0)[0]
    with open(os.path.join(OUT, "static_expected.json"), "w") as f:
        json.dump({"argmax": int(np.argmax(probs)), "probs": [float(p) for p in probs]}, f)
```

- [ ] **Step 4: Regenerate fixtures**

Run: `cd /Users/katie/ADI2026-1 && npm run fixture`
Expected: `build/fixtures/static_expected.json` exists with `argmax` and 26 probs.

- [ ] **Step 5: Add a pure-JS local model loader + static-model check to `build/parity_test.mjs`**

Insert after the imports:

```javascript
import * as tf from "@tensorflow/tfjs";

// Load a tfjs layers model from local files (no native deps, no file:// handler needed)
async function loadLocalLayersModel(modelJsonPath) {
  const modelJSON = JSON.parse(fs.readFileSync(modelJsonPath, "utf8"));
  const dir = path.dirname(modelJsonPath);
  const specs = [];
  const buffers = [];
  for (const group of modelJSON.weightsManifest) {
    for (const p of group.paths) buffers.push(fs.readFileSync(path.join(dir, p)));
    specs.push(...group.weights);
  }
  const wd = Buffer.concat(buffers);
  const handler = {
    load: async () => ({
      modelTopology: modelJSON.modelTopology,
      weightSpecs: specs,
      weightData: wd.buffer.slice(wd.byteOffset, wd.byteOffset + wd.byteLength),
      format: modelJSON.format,
      generatedBy: modelJSON.generatedBy,
      convertedBy: modelJSON.convertedBy,
    }),
  };
  return tf.loadLayersModel(handler);
}
```

Then insert before the final `console.log("ALL PARITY CHECKS PASSED")`:

```javascript
// --- Static model parity ---
const staticExpected = JSON.parse(fs.readFileSync(path.join(F, "static_expected.json"), "utf8"));
const staticModel = await loadLocalLayersModel(
  path.join(__dirname, "..", "frontend", "detection", "models", "static", "model.json")
);
const input = tf.tensor2d([Array.from(extractLandmarks(raw))]); // shape [1,63]
const out = staticModel.predict(input);
const probs = Array.from(await out.data());
const argmax = probs.indexOf(Math.max(...probs));
if (argmax !== staticExpected.argmax) {
  throw new Error(`static argmax ${argmax} != Python ${staticExpected.argmax}`);
}
assertClose(probs, staticExpected.probs, 1e-3, "static-model probs");
console.log(`PASS static-model argmax (${argmax})`);
```

- [ ] **Step 6: Run parity — expect PASS on preprocess + static model**

Run: `cd /Users/katie/ADI2026-1 && npm run parity`
Expected: `PASS preprocess`, `PASS static-model probs`, `PASS static-model argmax`, `ALL PARITY CHECKS PASSED`.

- [ ] **Step 7: Commit**

```bash
git add build/convert_models.py build/export_parity_fixture.py build/parity_test.mjs frontend/detection/models/static
git commit -m "feat: convert static model to TF.js, verify inference parity with Python"
```

### Task 4: In-browser letter-detection smoke harness + GATE

**Files:**
- Create: `frontend/detection/handLandmarker.js`
- Create: `frontend/spike.html` (temporary smoke harness; removed after gate)

**Interfaces:**
- Consumes: `extractLandmarks` (Task 2), the static model files (Task 3), vendored MediaPipe (Task 0).
- Produces: `createHandLandmarker() -> { detectForVideo(video, timestampMs) -> landmarksArray|null }`.

- [ ] **Step 1: Write `frontend/detection/handLandmarker.js`**

```javascript
import { FilesetResolver, HandLandmarker } from "./vendor/mediapipe/vision_bundle.mjs";

// Wraps MediaPipe tasks-vision HandLandmarker with locally-served WASM + .task model.
export async function createHandLandmarker() {
  const fileset = await FilesetResolver.forVisionTasks("./detection/vendor/mediapipe/wasm");
  const landmarker = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: "./detection/hand_landmarker.task" },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.7,
    minTrackingConfidence: 0.5,
  });
  return {
    // Returns array of 21 {x,y,z} for the first hand, or null. Feeds a
    // horizontally-flipped frame to match the Python cv2.flip(frame,1).
    detectForVideo(video, timestampMs, flipCanvas, flipCtx) {
      const vw = video.videoWidth, vh = video.videoHeight;
      flipCanvas.width = vw; flipCanvas.height = vh;
      flipCtx.save();
      flipCtx.translate(vw, 0); flipCtx.scale(-1, 1);
      flipCtx.drawImage(video, 0, 0, vw, vh);
      flipCtx.restore();
      const res = landmarker.detectForVideo(flipCanvas, timestampMs);
      if (res.landmarks && res.landmarks.length > 0) return res.landmarks[0];
      return null;
    },
  };
}
```

- [ ] **Step 2: Write `frontend/spike.html`** (minimal: webcam → landmarks → static model → show letter)

```html
<!doctype html><meta charset="utf-8"><title>spike</title>
<video id="v" autoplay playsinline muted style="width:320px"></video>
<div id="out" style="font:24px monospace">…</div>
<script src="./detection/vendor/tfjs/tf.min.js"></script>
<script type="module">
import { extractLandmarks } from "./detection/preprocess.js";
import { ASL_LABELS } from "./detection/labels.js";
import { createHandLandmarker } from "./detection/handLandmarker.js";

async function loadModel(p){ return tf.loadLayersModel(p); }
const v = document.getElementById("v"), out = document.getElementById("out");
const fc = document.createElement("canvas"), fctx = fc.getContext("2d");
v.srcObject = await navigator.mediaDevices.getUserMedia({ video: true });
await v.play();
const hl = await createHandLandmarker();
const model = await loadModel("./detection/models/static/model.json");
let t = 0;
function loop(){
  t += 33;
  const lm = hl.detectForVideo(v, t, fc, fctx);
  if (lm){
    const vec = extractLandmarks(lm);
    const probs = model.predict(tf.tensor2d([Array.from(vec)]));
    probs.data().then(d => {
      let mi = 0; for (let i=1;i<d.length;i++) if (d[i]>d[mi]) mi=i;
      out.textContent = `${ASL_LABELS[mi]}  (${d[mi].toFixed(2)})`;
      probs.dispose();
    });
  } else out.textContent = "(no hand)";
  requestAnimationFrame(loop);
}
loop();
</script>
```

- [ ] **Step 3: Serve and smoke-test in a browser**

Run: `cd /Users/katie/ADI2026-1/frontend && python3 -m http.server 5178`
Then open `http://localhost:5178/spike.html`, allow the camera, and sign a few letters.
Expected: recognizable letters appear with confidence; matches how the current backend behaves.

- [ ] **Step 4: 🚦 VALIDATION GATE — stop for sign-off**

Report to the user: parity test output (Task 3 Step 6) + observations from the webcam smoke test. **Do not proceed to Phase 2 until the user confirms detection quality is acceptable.** If parity or quality is poor, revisit conversion/preprocessing before continuing.

- [ ] **Step 5: Commit the spike (harness removed later in Task 12)**

```bash
git add frontend/detection/handLandmarker.js frontend/spike.html
git commit -m "feat: in-browser hand landmarker + letter-detection spike harness"
```

---

## PHASE 2 — Full detection engine (after gate)

### Task 5: LSTM model parity

**Files:**
- Modify: `build/export_parity_fixture.py` (append LSTM expected output)
- Modify: `build/parity_test.mjs` (add LSTM check)

**Interfaces:**
- Consumes: converted LSTM model (Task 3 Step 2 already produced `models/lstm/`), `loadLocalLayersModel` (Task 3).
- Produces: verified LSTM inference parity.

- [ ] **Step 1: Append LSTM fixture to `build/export_parity_fixture.py`**

Add before the final print:

```python
    # LSTM expected output on a fixed 30x63 sequence
    seq = rng.uniform(-1, 1, size=(30, 63)).astype(np.float32)
    from model_lstm import load_trained_model as _load_lstm
    lstm = _load_lstm(os.path.join(os.path.dirname(__file__), "..", "asl-detector", "asl_lstm_model.keras"))
    lprobs = lstm.predict(seq.reshape(1, 30, 63), verbose=0)[0]
    with open(os.path.join(OUT, "lstm_seq.json"), "w") as f:
        json.dump(seq.tolist(), f)
    with open(os.path.join(OUT, "lstm_expected.json"), "w") as f:
        json.dump({"argmax": int(np.argmax(lprobs)), "probs": [float(p) for p in lprobs]}, f)
```

- [ ] **Step 2: Regenerate fixtures**

Run: `cd /Users/katie/ADI2026-1 && npm run fixture`
Expected: `build/fixtures/lstm_seq.json` (30×63) and `lstm_expected.json` exist.

- [ ] **Step 3: Add LSTM check to `build/parity_test.mjs`** (before final success log)

```javascript
// --- LSTM model parity ---
const lstmSeq = JSON.parse(fs.readFileSync(path.join(F, "lstm_seq.json"), "utf8"));
const lstmExpected = JSON.parse(fs.readFileSync(path.join(F, "lstm_expected.json"), "utf8"));
const lstmModel = await loadLocalLayersModel(
  path.join(__dirname, "..", "frontend", "detection", "models", "lstm", "model.json")
);
const lin = tf.tensor3d([lstmSeq]); // shape [1,30,63]
const lout = lstmModel.predict(lin);
const lprobs = Array.from(await lout.data());
const largmax = lprobs.indexOf(Math.max(...lprobs));
if (largmax !== lstmExpected.argmax) throw new Error(`lstm argmax ${largmax} != Python ${lstmExpected.argmax}`);
assertClose(lprobs, lstmExpected.probs, 2e-3, "lstm-model probs");
console.log(`PASS lstm-model argmax (${largmax})`);
```

- [ ] **Step 4: Run parity — expect all PASS**

Run: `cd /Users/katie/ADI2026-1 && npm run parity`
Expected: preprocess, static, and lstm all PASS.

- [ ] **Step 5: Commit**

```bash
git add build/export_parity_fixture.py build/parity_test.mjs frontend/detection/models/lstm
git commit -m "feat: verify LSTM model inference parity with Python"
```

### Task 6: PredictionSmoother port with unit tests

**Files:**
- Create: `frontend/detection/smoother.js`
- Create: `build/smoother_test.mjs`
- Modify: `package.json` (add `"smoke:smoother": "node build/smoother_test.mjs"`)

**Interfaces:**
- Consumes: nothing.
- Produces: `class PredictionSmoother { constructor({windowSize, stableCount, cooldown, confidenceThreshold}); update(prediction|null, confidence) -> [accepted|null, conf]; reset() }`.

- [ ] **Step 1: Write `frontend/detection/smoother.js`** (port of `PredictionSmoother`)

```javascript
// Port of PredictionSmoother from test-backend/asl_handler.py.
// prediction is an integer class index or null; returns [accepted|null, conf].
export class PredictionSmoother {
  constructor({ windowSize = 12, stableCount = 8, cooldown = 15, confidenceThreshold = 0.65 } = {}) {
    this.windowSize = windowSize;
    this.stableCount = stableCount;
    this.cooldown = cooldown;
    this.confidenceThreshold = confidenceThreshold;
    this.window = [];
    this.cooldownCounter = 0;
    this.lastAccepted = null;
  }

  _push(v) {
    this.window.push(v);
    if (this.window.length > this.windowSize) this.window.shift();
  }

  update(prediction, confidence) {
    if (this.cooldownCounter > 0) {
      this.cooldownCounter -= 1;
      if (this.cooldownCounter === 0) this.lastAccepted = null;
    }

    if (confidence < this.confidenceThreshold) {
      this._push(null);
      return [null, 0];
    }

    this._push(prediction);

    if (this.window.length >= this.stableCount) {
      const recent = this.window.filter((p) => p !== null);
      if (recent.length >= this.stableCount) {
        const counts = new Map();
        for (const p of recent) counts.set(p, (counts.get(p) || 0) + 1);
        let mostCommon = null, count = 0;
        for (const [k, c] of counts) if (c > count) { mostCommon = k; count = c; }
        if (count >= this.stableCount && this.cooldownCounter === 0) {
          if (mostCommon !== this.lastAccepted) {
            this.lastAccepted = mostCommon;
            this.cooldownCounter = this.cooldown;
            this.window = [];
            return [mostCommon, confidence];
          }
        }
      }
    }
    return [null, 0];
  }

  reset() {
    this.window = [];
    this.cooldownCounter = 0;
    this.lastAccepted = null;
  }
}
```

- [ ] **Step 2: Write `build/smoother_test.mjs`**

```javascript
import assert from "node:assert";
import { PredictionSmoother } from "../frontend/detection/smoother.js";

// stable_count identical high-confidence predictions -> accept once, then cooldown
const s = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
let accepted = null;
for (let i = 0; i < 4; i++) { const [a] = s.update(5, 0.9); if (a !== null) accepted = a; }
assert.strictEqual(accepted, 5, "should accept class 5 after 4 stable frames");

// immediately after acceptance, cooldown blocks re-acceptance
const [a2] = s.update(5, 0.9);
assert.strictEqual(a2, null, "cooldown should block immediate re-accept");

// low confidence never accepts
const s2 = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
let any = null;
for (let i = 0; i < 8; i++) { const [a] = s2.update(3, 0.5); if (a !== null) any = a; }
assert.strictEqual(any, null, "low confidence must not be accepted");

console.log("PASS smoother unit tests");
```

- [ ] **Step 3: Run — expect PASS**

Run: `cd /Users/katie/ADI2026-1 && node build/smoother_test.mjs`
Expected: `PASS smoother unit tests`.

- [ ] **Step 4: Commit**

```bash
git add frontend/detection/smoother.js build/smoother_test.mjs package.json
git commit -m "feat: port PredictionSmoother with unit tests"
```

### Task 7: Models module (`models.js`)

**Files:**
- Create: `frontend/detection/models.js`

**Interfaces:**
- Consumes: global `tf` (vendored), model files.
- Produces: `async function loadModels() -> { predictStatic(Float32Array63) -> {index, confidence}, predictSequence(Array30x63) -> {index, confidence} }`.

- [ ] **Step 1: Write `frontend/detection/models.js`**

```javascript
// Loads the converted TF.js models and runs inference. Assumes global `tf`
// (vendored tf.min.js loaded via <script> before the module).
export async function loadModels() {
  const staticModel = await tf.loadLayersModel("./detection/models/static/model.json");
  const lstmModel = await tf.loadLayersModel("./detection/models/lstm/model.json");

  function argmaxConf(dataArr) {
    let mi = 0;
    for (let i = 1; i < dataArr.length; i++) if (dataArr[i] > dataArr[mi]) mi = i;
    return { index: mi, confidence: dataArr[mi] };
  }

  return {
    predictStatic(vec63) {
      return tf.tidy(() => {
        const out = staticModel.predict(tf.tensor2d([Array.from(vec63)]));
        const d = out.dataSync();
        return argmaxConf(d);
      });
    },
    predictSequence(seq30x63) {
      return tf.tidy(() => {
        const out = lstmModel.predict(tf.tensor3d([seq30x63]));
        const d = out.dataSync();
        return argmaxConf(d);
      });
    },
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/detection/models.js
git commit -m "feat: TF.js model loader/inference wrapper"
```

### Task 8: Detection engine (`engine.js`)

**Files:**
- Create: `frontend/detection/engine.js`

**Interfaces:**
- Consumes: `createHandLandmarker` (Task 4), `extractLandmarks` (Task 2), `loadModels` (Task 7), `PredictionSmoother` (Task 6), labels (Task 1).
- Produces: `async function createEngine({ video, onMessage }) -> { start(), stop(), setMode(mode) }`. `onMessage(msg)` receives the exact contract objects (`{type:"status",...}` / `{type:"detection",...}`).

- [ ] **Step 1: Write `frontend/detection/engine.js`** (ports `ASLDetectionSession.process_frame`)

```javascript
import { createHandLandmarker } from "./handLandmarker.js";
import { extractLandmarks } from "./preprocess.js";
import { loadModels } from "./models.js";
import { PredictionSmoother } from "./smoother.js";
import { ASL_LABELS, SEQUENCE_LABELS, WORD_TO_LETTER } from "./labels.js";

const SEQUENCE_LENGTH = 30;
const PREDICTION_INTERVAL = 1;

export async function createEngine({ video, onMessage }) {
  const hl = await createHandLandmarker();
  const models = await loadModels();
  const flipCanvas = document.createElement("canvas");
  const flipCtx = flipCanvas.getContext("2d");

  let mode = "letters";
  let running = false;
  let timestamp = 0;
  let frameCount = 0;
  let rafId = null;

  const letterSmoother = new PredictionSmoother({ windowSize: 8, stableCount: 4, cooldown: 8, confidenceThreshold: 0.65 });
  const wordSmoother = new PredictionSmoother({ windowSize: 8, stableCount: 3, cooldown: 10, confidenceThreshold: 0.3 });
  let wordBuffer = [];

  function setMode(m) {
    if (m === "letters" || m === "words" || m === "both") {
      mode = m;
      letterSmoother.reset();
      wordSmoother.reset();
      wordBuffer = [];
    }
  }

  function processFrame() {
    if (!running) return;
    timestamp += 33;
    frameCount += 1;

    const hand = hl.detectForVideo(video, timestamp, flipCanvas, flipCtx);
    const handDetected = !!hand;
    const vec = handDetected ? extractLandmarks(hand) : null;

    // status message (landmarks are the flipped-frame coords, [x,y] pairs)
    const status = { type: "status", hand_detected: handDetected };
    if (handDetected) status.landmarks = hand.map((lm) => [lm.x, lm.y]);
    onMessage(status);

    // letters
    if ((mode === "letters" || mode === "both")) {
      if (handDetected && vec) {
        const { index, confidence } = models.predictStatic(vec);
        const [accepted, conf] = letterSmoother.update(index, confidence);
        if (accepted !== null) {
          onMessage({ type: "detection", kind: "letter", value: ASL_LABELS[accepted], confidence: Math.round(conf * 1000) / 1000 });
        }
      } else {
        letterSmoother.update(null, 0);
      }
    }

    // words
    if ((mode === "words" || mode === "both")) {
      if (handDetected && vec) {
        wordBuffer.push(Array.from(vec));
      } else if (wordBuffer.length > 0) {
        wordBuffer.push(wordBuffer[wordBuffer.length - 1]);
      }
      if (wordBuffer.length > SEQUENCE_LENGTH) wordBuffer.shift();

      let wordPred = null, wordConf = 0;
      if (wordBuffer.length === SEQUENCE_LENGTH && frameCount % PREDICTION_INTERVAL === 0) {
        const r = models.predictSequence(wordBuffer);
        wordPred = r.index; wordConf = r.confidence;
      }
      const [accepted, conf] = wordPred !== null
        ? wordSmoother.update(wordPred, wordConf)
        : wordSmoother.update(null, 0);
      if (accepted !== null) {
        const wordName = SEQUENCE_LABELS[accepted];
        const display = WORD_TO_LETTER[wordName] || wordName;
        const c = Math.round(conf * 1000) / 1000;
        if (display === "DELETE") onMessage({ type: "detection", kind: "word", value: "DELETE", word: "DELETE", confidence: c });
        else if (display === "SPACE") onMessage({ type: "detection", kind: "word", value: "SPACE", word: "SPACE", confidence: c });
        else onMessage({ type: "detection", kind: "word", value: display, word: wordName, confidence: c });
      }
    }

    rafId = requestAnimationFrame(processFrame);
  }

  return {
    start() { if (running) return; running = true; timestamp = 0; frameCount = 0; rafId = requestAnimationFrame(processFrame); },
    stop() { running = false; if (rafId) cancelAnimationFrame(rafId); rafId = null; },
    setMode,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/detection/engine.js
git commit -m "feat: in-browser ASL detection engine emitting the WS message contract"
```

### Task 9: Wire engine into `index.html` (replace `/ws/asl`)

**Files:**
- Modify: `frontend/index.html` (detection wiring around lines 1820–1936; add module script)

**Interfaces:**
- Consumes: `createEngine` (Task 8).
- Produces: `startASLDetection()` / `stopASLDetection()` / mode changes now driven by the engine; `handleASLMessage(msg)` called with engine messages.

- [ ] **Step 1: Load vendored tfjs + expose an engine bootstrap.** In `frontend/index.html`, add before the main inline `<script>`:

```html
<script src="./detection/vendor/tfjs/tf.min.js"></script>
<script type="module">
  import { createEngine } from "./detection/engine.js";
  window.__createEngine = createEngine;
</script>
```

- [ ] **Step 2: Replace the WebSocket detection with the engine.** In the inline script, change `handleASLMessage(event)` to accept a message object directly (it currently does `JSON.parse(event.data)`):

Replace:
```javascript
    function handleASLMessage(event) {
      const msg = JSON.parse(event.data);
```
with:
```javascript
    function handleASLMessage(msg) {
```

- [ ] **Step 3: Rewrite `startASLDetection` / `stopASLDetection`** to use the engine. Replace the bodies of both functions (lines ~1847–1898) with:

```javascript
    let aslEngine = null;
    async function startASLDetection() {
      if (aslEngine) return;
      const video = document.getElementById('webcamVideo');
      if (!video.srcObject) return;
      aslEngine = await window.__createEngine({
        video,
        onMessage: (msg) => {
          if (msg.type === 'status') updateAslFps();
          handleASLMessage(msg);
        },
      });
      isDetecting = true;
      if (activeTab === 'tutorial') updateTutorialMode();
      aslEngine.start();
    }

    function stopASLDetection() {
      isDetecting = false;
      if (aslEngine) { aslEngine.stop(); aslEngine = null; }
    }
```

- [ ] **Step 4: Route mode changes to the engine.** Find where `updateTutorialMode()` / mode toggles previously sent `{action:'set_mode', mode}` over the socket and replace those `aslSocket.send(...)` calls with `if (aslEngine) aslEngine.setMode(mode);` (search the file for `set_mode`).

- [ ] **Step 5: Remove dead WS code.** Delete `getBackendWebSocketUrl`, `sendFrame`, `scheduleNextFrame`, `sendFrameLoop`, and any remaining `aslSocket` references.

- [ ] **Step 6: Smoke test (letters + words).**

Run: `cd /Users/katie/ADI2026-1/frontend && python3 -m http.server 5178`
Open `http://localhost:5178/index.html`, allow camera. Verify letter detection, switch to word/tutorial mode, and sign at least one word.
Expected: detection drives the game UI exactly as before; landmark overlay draws.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html
git commit -m "feat: drive ASL detection from the in-browser engine, remove WS client"
```

---

## PHASE 3 — Audio (TTS + music)

### Task 10: Pre-generate TTS clips and replace `/api/tts`

**Files:**
- Create: `build/generate_tts.py`
- Create: `frontend/audio/tts/*.mp3` (generated)
- Create: `frontend/audio/tts.js`
- Modify: `frontend/index.html` (TTS call site ~lines 2029–2069)

**Interfaces:**
- Consumes: nothing at runtime (clips bundled).
- Produces: `speak(text)` in `audio/tts.js` mapping a phrase to a bundled clip.

- [ ] **Step 1: Write `build/generate_tts.py`** (build-time only; key from env, never shipped)

```python
"""Generate 8 TTS clips (Bella voice) via ElevenLabs. Build-time only.
Requires ELEVENLABS_API_KEY in the environment. Output NOT committed with any key."""
import os, sys, json, urllib.request

API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    sys.exit("Set ELEVENLABS_API_KEY in the environment (do not hardcode).")

VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Bella (matches frontend selectedVoiceId)
BASE = "https://api.elevenlabs.io/v1"
PHRASES = {
    "thank_you": "Thank you", "i_love_you": "I love you", "hello": "Hello",
    "goodbye": "Goodbye", "ok": "OK", "six_seven": "Six seven",
    "delete": "Delete", "space": "Space",
}
OUT = os.path.join(os.path.dirname(__file__), "..", "frontend", "audio", "tts")
os.makedirs(OUT, exist_ok=True)

for key, text in PHRASES.items():
    req = urllib.request.Request(
        f"{BASE}/text-to-speech/{VOICE_ID}",
        data=json.dumps({"text": text, "model_id": "eleven_monolingual_v1"}).encode(),
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        audio = resp.read()
    with open(os.path.join(OUT, f"{key}.mp3"), "wb") as f:
        f.write(audio)
    print(f"wrote {key}.mp3 ({len(audio)} bytes)")
```

- [ ] **Step 2: Generate clips** (key provided at build time only)

Run: `cd /Users/katie/ADI2026-1 && ELEVENLABS_API_KEY=<key> npm run tts`
Expected: 8 mp3 files in `frontend/audio/tts/`. (The user supplies the key; it is never written to a committed file.)

- [ ] **Step 3: Write `frontend/audio/tts.js`**

```javascript
// Bundled-clip TTS. Maps the game's SPEAK_MAP phrases to pre-generated files.
const CLIP = {
  "Thank you": "./audio/tts/thank_you.mp3",
  "I love you": "./audio/tts/i_love_you.mp3",
  "Hello": "./audio/tts/hello.mp3",
  "Goodbye": "./audio/tts/goodbye.mp3",
  "OK": "./audio/tts/ok.mp3",
  "Six seven": "./audio/tts/six_seven.mp3",
  "Delete": "./audio/tts/delete.mp3",
  "Space": "./audio/tts/space.mp3",
};
let current = null;
export function speak(spokenText, volume = 1) {
  const src = CLIP[spokenText];
  if (!src) return;
  if (current) { current.pause(); current = null; }
  const audio = new Audio(src);
  audio.volume = volume;
  current = audio;
  audio.play().catch(() => {});
}
```

- [ ] **Step 4: Replace the `/api/tts` fetch in `index.html`.** Expose the module (add to the module script from Task 9 Step 1): `import { speak } from "./audio/tts.js"; window.__speak = speak;`. Then replace the `fetch(`${backendUrl}/api/tts`...)` block (lines ~2053–2069+) with:

```javascript
      window.__speak(speakable, voiceVolumeLevel);
```

- [ ] **Step 5: Smoke test.** Reload `index.html`; trigger each of the 8 phrases.
Expected: correct clip plays; no network request to `/api/tts` (check devtools Network tab is clean of it).

- [ ] **Step 6: Commit**

```bash
git add build/generate_tts.py frontend/audio/tts frontend/audio/tts.js frontend/index.html
git commit -m "feat: bundled TTS clips replace backend /api/tts"
```

### Task 11: Bundled background music replaces Lyria (`/ws/beat`)

**Files:**
- Create: `frontend/audio/music/loop.mp3` (sourced, royalty-free)
- Create: `frontend/audio/music/LICENSE.txt` (source + license)
- Create: `frontend/audio/music.js`
- Modify: `frontend/index.html` (music toggle wiring; Lyria socket ~lines 2279–2400)

**Interfaces:**
- Consumes: nothing at runtime.
- Produces: `music.play()`, `music.stop()`, `music.setVolume(v)` in `audio/music.js`.

- [ ] **Step 1: Source a CC0/royalty-free chiptune loop.** Download one clip to `frontend/audio/music/loop.mp3` and record its URL + license in `frontend/audio/music/LICENSE.txt`. (Confirm the specific track with the user before committing.)

- [ ] **Step 2: Write `frontend/audio/music.js`**

```javascript
// Looping background music from a bundled file (replaces Lyria /ws/beat).
let audio = null;
export const music = {
  play(volume = 0.5) {
    if (!audio) { audio = new Audio("./audio/music/loop.mp3"); audio.loop = true; }
    audio.volume = volume;
    audio.play().catch(() => {});
  },
  stop() { if (audio) { audio.pause(); audio.currentTime = 0; } },
  setVolume(v) { if (audio) audio.volume = v; },
};
```

- [ ] **Step 3: Wire the existing music toggle to this module.** Expose it (`import { music } from "./audio/music.js"; window.__music = music;`). Find the Lyria `beatSocket` wiring (search `WS_URL`, `beatSocket`, `Connecting to Lyria`) and replace: connect→`window.__music.play()`, disconnect→`window.__music.stop()`, volume slider→`window.__music.setVolume(v)`. Remove `beatSocket` / `getBackendWebSocketUrl('/ws/beat')` code.

- [ ] **Step 4: Smoke test.** Toggle music on/off; adjust volume.
Expected: loop plays/stops/volumes; no WebSocket attempt.

- [ ] **Step 5: Commit**

```bash
git add frontend/audio/music frontend/audio/music.js frontend/index.html
git commit -m "feat: bundled looping music replaces Lyria backend"
```

---

## PHASE 4 — Package & ship

### Task 12: Remove spike harness and confirm no off-origin calls

**Files:**
- Delete: `frontend/spike.html`
- Modify: `frontend/index.html` (only if any stray backend refs remain)

- [ ] **Step 1: Delete the spike harness**

Run: `cd /Users/katie/ADI2026-1 && git rm frontend/spike.html`

- [ ] **Step 2: Grep for any remaining off-origin references**

Run: `grep -niE "localhost:8000|/ws/|/api/|onrender|new WebSocket|http://|https://" frontend/index.html | grep -viE "fonts.googleapis|fonts.gstatic|w3.org|http-equiv|charset"`
Expected: **no matches** (Google Fonts links are the only allowed external refs — and they should be vendored too; see Step 3).

- [ ] **Step 3: Vendor Google Fonts (Press Start 2P, DM Mono).** ghg.gg blocks off-origin, so the `fonts.googleapis.com` stylesheet + font files must be bundled. Download the CSS and `.woff2` files into `frontend/fonts/`, rewrite the `@font-face` `src` URLs to relative paths, and replace the `<link href="https://fonts.googleapis.com...">` with a local `<link href="./fonts/fonts.css">`.

- [ ] **Step 4: Re-grep — expect zero external references**

Run: `grep -niE "http://|https://" frontend/index.html`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add -A frontend
git commit -m "chore: remove spike harness, vendor fonts, drop all off-origin refs"
```

### Task 13: Build the flat static zip

**Files:**
- Create: `build/build_dist.mjs`
- Modify: `package.json` (already has `"dist"` script)

**Interfaces:**
- Consumes: `frontend/` tree.
- Produces: `dist/` (flat, index.html at root) and `angry-signing-llamas-ghg.zip`.

- [ ] **Step 1: Write `build/build_dist.mjs`**

```javascript
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url)) + "/..";
const src = path.join(root, "frontend");
const dist = path.join(root, "dist");
const zip = path.join(root, "angry-signing-llamas-ghg.zip");

// Only ship static assets; never ship spike/build/backend/secret files.
const EXCLUDE = new Set(["spike.html", "README.md"]);

fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });

function copyDir(from, to) {
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    if (EXCLUDE.has(entry.name)) continue;
    const s = path.join(from, entry.name), d = path.join(to, entry.name);
    if (entry.isDirectory()) { fs.mkdirSync(d, { recursive: true }); copyDir(s, d); }
    else fs.copyFileSync(s, d);
  }
}
copyDir(src, dist);

// Guard: index.html must be at the dist root, and no secrets present.
if (!fs.existsSync(path.join(dist, "index.html"))) throw new Error("index.html missing at dist root");
const leaked = execSync(`grep -rilE "xi-api-key|ELEVENLABS_API_KEY|sk_[a-z0-9]" ${dist} || true`).toString().trim();
if (leaked) throw new Error("Potential secret in dist:\n" + leaked);

fs.rmSync(zip, { force: true });
execSync(`cd ${dist} && zip -r -q ${zip} .`);
const files = execSync(`cd ${dist} && find . -type f | wc -l`).toString().trim();
console.log(`Built ${zip} — ${files} files, index.html at root, no secrets.`);
```

- [ ] **Step 2: Build the zip**

Run: `cd /Users/katie/ADI2026-1 && npm run dist`
Expected: `Built .../angry-signing-llamas-ghg.zip — <N> files, index.html at root, no secrets.`

- [ ] **Step 3: Verify zip structure (flat, index.html at root)**

Run: `unzip -l angry-signing-llamas-ghg.zip | head -20`
Expected: `index.html` appears at the top level (not inside a wrapping folder).

- [ ] **Step 4: Final local test of the exact dist that ships**

Run: `cd /Users/katie/ADI2026-1/dist && python3 -m http.server 5179`
Open `http://localhost:5179/`, allow camera; verify letters, words, TTS, and music all work with **no network calls** beyond the page's own origin (devtools Network tab).

- [ ] **Step 5: Add `dist/` and the zip to .gitignore, commit the build script**

Add to `.gitignore`: `dist/` and `angry-signing-llamas-ghg.zip`.

```bash
git add build/build_dist.mjs .gitignore
git commit -m "feat: flat static dist builder + zip with secret/structure guards"
```

### Task 14: Upload to ghg.gg

- [ ] **Step 1:** Provide `angry-signing-llamas-ghg.zip` to the user and confirm the upload succeeds on ghg.gg (the "missing index.html entry point" error should be gone).
- [ ] **Step 2:** If ghg.gg reports any issue, capture the exact message and iterate on packaging (structure, file count, or an unexpected off-origin reference).

---

## Follow-ups (not in this plan)

- **Rotate the leaked ElevenLabs API key** (hardcoded in `test-backend/server.py:382` and `elevenlabs/no_pip_server.py:13`). Deferred by user decision.

## Notes on risk

- The **only** deep technical risk is model conversion + inference parity; it is fully de-risked by Phase 1's automated parity tests (Tasks 2–3, 5) and gated on user sign-off (Task 4) before further investment.
- If `tensorflowjs` cannot convert the `.keras` files directly (Keras 3 friction), `convert_models.py` rebuilds the architectures via `create_asl_model` / `create_lstm_model` and loads weights — a path proven by the parity tests either way.
