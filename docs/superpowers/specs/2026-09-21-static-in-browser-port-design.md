# Angry-Signing-Llamas — Fully In-Browser Build for ghg.gg

**Date:** 2026-09-21
**Status:** Approved design, pre-implementation
**Repo:** github.com/katiewangmt/Angry-Signing-Llamas (`static-in-browser-port` branch)

## Problem

The game must be uploaded to **Greenhouse Games (ghg.gg)**, which is a **static host**:

- Requires `index.html` at the zip root (flat), or exactly one wrapping folder containing `index.html`.
- **Blocks all off-origin network requests** — no backend servers, no WebSockets, no external fetches. "Your game can't reach anything off its own origin once deployed, so bundle everything locally."

The current game is **entirely backend-driven** and cannot run on such a host as-is. A previous attempt failed with `Missing index.html entry point` because the source zip wrapped everything in `Angry-Signing-Llamas-main/` and `index.html` lives under `frontend/`. Fixing the zip structure alone is insufficient — the game would upload but be unplayable, because its core mechanic and audio depend on a Python backend.

### Backend dependencies (full sweep of `frontend/index.html`)

| Endpoint | Purpose | Portability |
|---|---|---|
| `/ws/asl` | ASL detection — frames sent to Python (MediaPipe + 2 Keras models), returns detected letters/words. **Core mechanic.** | Portable: in-browser MediaPipe + TF.js |
| `/api/tts` | Text-to-speech for **8 fixed phrases** (Bella voice) | Portable: bundle 8 pre-generated clips |
| `/ws/beat` | **Lyria** real-time AI music generation for background music | **Not portable** — replace with bundled looping track |

There are no other network calls. Leaderboard/stats are client-side.

## Scope (agreed)

**Core gameplay, faithful.** ASL detection + TTS work fully in-browser and match the original's feel. Lyria background music is replaced by a bundled royalty-free loop. No feature is dropped except real-time AI music generation.

## Approach (chosen: A)

**Convert the trained models to TensorFlow.js and run MediaPipe in the browser.**

Run `@mediapipe/tasks-vision` HandLandmarker (WASM) in the browser to extract the 21 hand landmarks, convert the two existing Keras models to TF.js, and port the `landmarks.py` preprocessing and `PredictionSmoother` logic to JS. This preserves the actual trained accuracy and all custom signs (`6_7`, `BADDIE`, etc.), with everything bundled and nothing off-origin.

Rejected alternatives:
- **B — Retrain / use MediaPipe's built-in gesture recognizer.** Throws away trained models; can't recognize the custom signs.
- **C — Ship the Python backend via Pyodide/WASM.** MediaPipe's C++ and TensorFlow do not run in Pyodide; impractical.

## Design

### Core idea: swap the detection *source*, keep the game

The game logic already sits behind a narrow interface. A detection source emits JSON messages and `handleASLMessage` (`frontend/index.html:1864`) routes them to gameplay. The port **replaces the WebSocket detection source with a local in-browser engine that emits the identical messages.** Tutorial matching, challenge mode, landmark drawing, scoring, and UI stay untouched.

**Message contract to reproduce exactly:**
- `{type:"status", hand_detected:bool, landmarks?:[[x,y] × 21]}` (landmarks normalized 0–1)
- `{type:"detection", kind:"letter", value:<letter>, confidence:<float>}`
- `{type:"detection", kind:"word", word:<word>, confidence:<float>}`

### New modules (separate JS files, bundled — not inline in `index.html`)

- **`detection/handLandmarker.js`** — wraps `@mediapipe/tasks-vision` HandLandmarker (WASM + `hand_landmarker.task`, both bundled locally). Input: video frame. Output: 21 landmarks (or none).
- **`detection/preprocess.js`** — faithful JS port of `extract_landmarks_new` / feature normalization from `asl-detector/landmarks.py` → the 63-feature vector (21 landmarks × 3 coords). **Must match Python exactly** or accuracy degrades.
- **`detection/models.js`** — loads both TF.js models; runs static (Dense) inference per frame and LSTM inference over a rolling `SEQUENCE_LENGTH` landmark buffer.
- **`detection/smoother.js`** — JS port of `PredictionSmoother` + word buffer/cooldown logic from `test-backend/asl_handler.py`, using the same constants (`STATIC_CONFIDENCE_THRESHOLD`, `STABLE_FRAMES`, `COOLDOWN_FRAMES`, `LSTM_CONFIDENCE_THRESHOLD`, etc.).
- **`detection/engine.js`** — orchestrates the above in a `requestAnimationFrame` loop and emits the contract messages to the existing handler. Public API: `start()`, `stop()`, `setMode(mode)` — mirroring today's `startASLDetection` / `stopASLDetection` / mode toggles.
- **`audio/tts.js`** — replaces the `/api/tts` fetch with a lookup of 8 pre-generated bundled clips (`audio/tts/*.mp3`), keyed by the existing `SPEAK_MAP` phrases.
- **Music shim** — replaces the `/ws/beat` Lyria socket with a bundled royalty-free loop (`audio/music/loop.mp3`) plus a small play/stop/volume shim reusing the existing music-toggle UI. Track is CC0 / royalty-free, source and license recorded in the repo.

### Build-time asset pipeline (one-time, Python — never shipped)

- Convert `asl-detector/asl_model.keras` and `asl-detector/asl_lstm_model.keras` → TF.js format via `tensorflowjs_converter` into `frontend/detection/models/`.
- Pre-generate the 8 TTS clips once via ElevenLabs (Bella, `EXAVITQu4vr4xnSDxMaL`) → `frontend/audio/tts/*.mp3`. The API key is used **only** at build time and never ships.

### Zip packaging (the original ask)

A small build script assembles a clean static `dist/` from `frontend/` plus the converted models and audio, then zips it **flat** with `index.html` at the root:

```
index.html
detection/  (js + models/ + mediapipe wasm + hand_landmarker.task)
audio/      (tts/*.mp3, music/loop.mp3)
signs/      (existing sign images/videos)
*.webp      (llama images)
```

The zip contains **only static assets — no `server.py`, no `.env`, no API key** — satisfying ghg.gg's structure and off-origin rules. Total well within the 1 GB / 10,000-file limits.

## Validation checkpoint (gate before full build)

Per the requirement to test before committing to the full port, **Step 1 is a spike, and implementation pauses for sign-off after it:**

1. Convert the **static** model to TF.js.
2. Port `preprocess.js` and load the model in the browser.
3. **Parity test:** feed a fixed set of hand landmarks through both the Python backend path and the JS path; assert the predicted letter and confidence match within tolerance.
4. Webcam smoke test: confirm live letter detection works in-browser and feels right.

**Gate:** review results together. Only proceed to the LSTM/word model, TTS, music, and packaging once this passes. If TF.js cannot load a layer, fall back to re-exporting the model architecture and reloading weights.

## Testing

- **Parity test** (static + later LSTM): identical input → identical output across Python and JS preprocessing + model.
- **Manual:** webcam smoke test of letters, at least one word sign, TTS playback for the 8 phrases, and the music loop.
- **End-to-end:** build the zip and perform a real ghg.gg upload to confirm it validates and runs.

## Follow-ups (tracked, not done in this work)

- **Rotate the leaked ElevenLabs API key** — currently hardcoded in `test-backend/server.py:382` and `elevenlabs/no_pip_server.py:13` and committed to the public repo. Deferred by user decision; do later.
