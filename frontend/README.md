# Angry Signing Llamas

A fully static, in-browser ASL practice game. No backend and no external API calls.

- **Hand detection:** MediaPipe HandLandmarker (WASM + model bundled in `detection/`).
- **Sign recognition:** TF.js models bundled in `detection/models/`.
- **Audio:** pre-generated voice clips and music in `audio/`.

## Run locally

Serve the `frontend/` folder with any static file server, for example:

    python3 -m http.server 3000 --directory frontend

Open http://localhost:3000 and allow camera access (the camera needs localhost or HTTPS).

## Build the submission zip

    npm ci
    npm run dist

This creates `angry-signing-llamas-ghg.zip` with `index.html` at the root.
