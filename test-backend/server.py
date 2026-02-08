"""
SignCraft Backend — Streaming Beat Generator
Bridges the frontend to Lyria RealTime via WebSocket.
Audio streams in real-time — no waiting for full generation.
"""

import asyncio
import base64
import json
import os
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Beat generation (optional — needs google-genai + GEMINI_API_KEY) ──
client = None
types = None
MODEL_ID = "models/lyria-realtime-exp"

try:
    from google import genai
    from google.genai import types as _types
    types = _types

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1alpha"},
        )
        print("  Beat generation: enabled (GEMINI_API_KEY found)")
    else:
        print("  Beat generation: disabled (no GEMINI_API_KEY)")
except ImportError:
    print("  Beat generation: disabled (google-genai not installed)")

# ── ASL detector imports ───────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "asl-detector"))

from asl_handler import ASLDetectionSession

# ── ASL model globals (loaded on startup) ──────────────────────
static_model = None
lstm_model = None

# ── FastAPI App ─────────────────────────────────────────
app = FastAPI(title="SignCraft Beat Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def load_asl_models():
    """Load ASL models once at server startup."""
    global static_model, lstm_model

    asl_dir = os.path.join(os.path.dirname(__file__), "..", "asl-detector")
    static_path = os.path.join(asl_dir, "asl_model.keras")
    lstm_path = os.path.join(asl_dir, "asl_lstm_model.keras")

    # Load static letter model
    if os.path.exists(static_path):
        try:
            import tensorflow as tf

            try:
                static_model = tf.keras.models.load_model(
                    static_path, safe_mode=False
                )
            except Exception:
                static_model = tf.keras.models.load_model(
                    static_path, compile=False
                )
                static_model.compile(
                    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
                    loss="sparse_categorical_crossentropy",
                    metrics=["accuracy"],
                )
            print(f"  ASL: Static letter model loaded from {static_path}")
        except Exception as e:
            print(f"  ASL: Could not load static model: {e}")
    else:
        print(f"  ASL: Static model not found at {static_path}")

    # Load LSTM word model
    if os.path.exists(lstm_path):
        try:
            from model_lstm import load_trained_model

            lstm_model = load_trained_model(lstm_path)
            print(f"  ASL: LSTM word model loaded from {lstm_path}")
        except Exception as e:
            print(f"  ASL: Could not load LSTM model: {e}")
    else:
        print(f"  ASL: LSTM model not found at {lstm_path}")


@app.get("/")
async def root():
    return {"status": "SignCraft Beat Generator is running"}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/beat")
async def beat_stream(ws: WebSocket):
    """
    WebSocket endpoint for streaming beats.

    Frontend sends:  { "action": "start", "prompt": "chill lofi", "bpm": 120 }
                     { "action": "update", "prompt": "hard trap" }
                     { "action": "stop" }

    Backend sends:   binary audio chunks (PCM 16-bit, 48kHz, stereo)
                     { "type": "status", "message": "..." } as JSON text
    """
    await ws.accept()

    if not client or not types:
        await ws.send_text(
            json.dumps({"type": "error", "message": "Beat generation unavailable (no API key or google-genai not installed)"})
        )
        await ws.close()
        return

    session = None
    session_cm = None  # context manager
    receive_task = None
    is_streaming = False

    async def stream_audio_to_client(lyria_session, websocket):
        """Forward Lyria audio chunks to the frontend."""
        nonlocal is_streaming
        try:
            async for message in lyria_session.receive():
                if not is_streaming:
                    break
                if message.server_content and message.server_content.audio_chunks:
                    for chunk in message.server_content.audio_chunks:
                        if chunk.data is not None:
                            await websocket.send_bytes(chunk.data)
        except Exception as e:
            if is_streaming:
                try:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": str(e)})
                    )
                except Exception:
                    pass
        finally:
            is_streaming = False

    async def cleanup_session():
        """Safely close the Lyria session."""
        nonlocal session, session_cm, receive_task, is_streaming
        is_streaming = False
        if receive_task:
            receive_task.cancel()
            try:
                await receive_task
            except (asyncio.CancelledError, Exception):
                pass
            receive_task = None
        if session:
            try:
                await session.stop()
            except Exception:
                pass
        if session_cm:
            try:
                await session_cm.__aexit__(None, None, None)
            except Exception:
                pass
        session = None
        session_cm = None

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "start":
                prompt = msg.get("prompt", "instrumental beat")
                bpm = msg.get("bpm", 120)

                # Close existing session if any
                await cleanup_session()

                # Connect to Lyria
                await ws.send_text(
                    json.dumps({"type": "status", "message": "connecting"})
                )

                session_cm = client.aio.live.music.connect(model=MODEL_ID)
                session = await session_cm.__aenter__()

                await session.set_weighted_prompts(
                    prompts=[types.WeightedPrompt(text=prompt, weight=1.0)]
                )
                await session.set_music_generation_config(
                    config=types.LiveMusicGenerationConfig(
                        bpm=bpm,
                        temperature=1.0,
                    )
                )

                await session.play()
                is_streaming = True

                await ws.send_text(
                    json.dumps({"type": "status", "message": "streaming"})
                )

                # Start forwarding audio in the background
                receive_task = asyncio.create_task(
                    stream_audio_to_client(session, ws)
                )

            elif action == "update":
                # Change the prompt on-the-fly without reconnecting
                if session and is_streaming:
                    new_prompt = msg.get("prompt", "")
                    if new_prompt:
                        await session.set_weighted_prompts(
                            prompts=[
                                types.WeightedPrompt(text=new_prompt, weight=1.0)
                            ]
                        )
                        await ws.send_text(
                            json.dumps({"type": "status", "message": "updated"})
                        )

            elif action == "stop":
                await cleanup_session()
                await ws.send_text(
                    json.dumps({"type": "status", "message": "stopped"})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
        except Exception:
            pass
    finally:
        await cleanup_session()


# ── ASL Detection WebSocket ─────────────────────────────────────
@app.websocket("/ws/asl")
async def asl_detect(ws: WebSocket):
    """
    WebSocket endpoint for real-time ASL detection.

    Client sends:
        {"action":"frame","data":"<base64 JPEG>"}  — at ~10fps
        {"action":"set_mode","mode":"letters"|"words"}
        {"action":"stop"}

    Server sends:
        {"type":"status","message":"ready","models":{...}}
        {"type":"detection","kind":"letter","value":"A","confidence":0.87}
        {"type":"detection","kind":"word","value":"HELLO","confidence":0.65}
        {"type":"status","hand_detected":true|false}
    """
    await ws.accept()

    session = ASLDetectionSession(static_model, lstm_model)

    try:
        # Send ready status
        await ws.send_text(
            json.dumps(
                {
                    "type": "status",
                    "message": "ready",
                    "models": {
                        "static": static_model is not None,
                        "lstm": lstm_model is not None,
                    },
                }
            )
        )

        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            action = msg.get("action")

            if action == "frame":
                # Decode base64 JPEG
                b64 = msg.get("data", "")
                # Strip data-URL prefix if present
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                jpeg_bytes = base64.b64decode(b64)

                # Run detection in a thread to avoid blocking the event loop
                results = await asyncio.to_thread(session.process_frame, jpeg_bytes)

                for result in results:
                    await ws.send_text(json.dumps(result))

            elif action == "set_mode":
                mode = msg.get("mode", "letters")
                session.set_mode(mode)
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "status",
                            "message": "mode_changed",
                            "mode": mode,
                        }
                    )
                )

            elif action == "stop":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
        except Exception:
            pass
    finally:
        session.cleanup()
