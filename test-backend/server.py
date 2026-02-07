"""
SignCraft Backend — Streaming Beat Generator
Bridges the frontend to Lyria RealTime via WebSocket.
Audio streams in real-time — no waiting for full generation.
"""

import asyncio
import json
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types

# ── Config ──────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "Missing GEMINI_API_KEY environment variable.\n"
        "Run:  export GEMINI_API_KEY='your-key-here'  then restart the server."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"api_version": "v1alpha"},
)

MODEL_ID = "models/lyria-realtime-exp"

# ── FastAPI App ─────────────────────────────────────────
app = FastAPI(title="SignCraft Beat Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
