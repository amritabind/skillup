"""
THE CORE ADK STREAMING PATTERN
================================
Every real-time agent uses this exact same structure:

  WebSocket ──► LiveRequestQueue ──► run_live() ──► Agent ──► Gemini Live API
                (upstream_task)      (downstream_task)

Two concurrent async tasks:
  1. upstream_task   : Client → Queue → Agent  (you speak/send image)
  2. downstream_task : Agent → WebSocket → Client (agent responds)

Interruptions are AUTOMATIC — Gemini Live API handles them natively.
When you speak while agent is talking, it stops and listens.
"""

import asyncio
import json
import base64

from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def run_agent_session(websocket, agent, app_name: str, user_id: str, session_id: str, modality="AUDIO"):
    """
    Universal session runner — works for voice, vision, text agents.
    modality: "AUDIO" for voice agents, "TEXT" for text-only agents
    """
    session_service = InMemorySessionService()
    runner = Runner(app_name=app_name, agent=agent, session_service=session_service)

    # --- Get or create persistent session ---
    session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)

    # --- Configure streaming behavior ---
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,          # Bidirectional = interruptions work!
        response_modalities=[modality],              # "AUDIO" or "TEXT"
        input_audio_transcription=types.AudioTranscriptionConfig(),   # Transcribe what user says
        output_audio_transcription=types.AudioTranscriptionConfig(),  # Transcribe what agent says
        session_resumption=types.SessionResumptionConfig(),           # Survive network drops
    )

    # --- Create a fresh queue for THIS session (never reuse!) ---
    live_request_queue = LiveRequestQueue()

    # ============================================================
    # UPSTREAM: Client → Agent  (sending voice/text/images)
    # ============================================================
    async def upstream_task():
        try:
            while True:
                message = await websocket.receive()

                if "bytes" in message:
                    # Raw audio bytes from the microphone
                    audio_blob = types.Blob(
                        mime_type="audio/pcm;rate=16000",
                        data=message["bytes"]
                    )
                    live_request_queue.send_realtime(audio_blob)  # Continuous stream (no turn boundaries)

                elif "text" in message:
                    data = json.loads(message["text"])

                    if data.get("type") == "text":
                        content = types.Content(parts=[types.Part(text=data["text"])])
                        live_request_queue.send_content(content)  # Turn-by-turn text

                    elif data.get("type") == "image":
                        # Send an image (e.g., homework photo)
                        image_bytes = base64.b64decode(data["data"])
                        image_blob = types.Blob(mime_type=data.get("mime_type", "image/jpeg"), data=image_bytes)
                        live_request_queue.send_realtime(image_blob)

        except Exception as e:
            print(f"Upstream closed: {e}")

    # ============================================================
    # DOWNSTREAM: Agent → Client  (receiving audio/text responses)
    # ============================================================
    async def downstream_task():
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # 1. Audio transcription (what agent said, as text — for UI display)
                if event.output_transcription and event.output_transcription.text:
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "data": event.output_transcription.text
                    }))

                # 2. Audio bytes (agent's voice)
                part = event.content and event.content.parts and event.content.parts[0]
                if part:
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                        await websocket.send_text(json.dumps({
                            "type": "audio",
                            "data": base64.b64encode(part.inline_data.data).decode("ascii")
                        }))
                    elif part.text and event.partial:
                        # Streaming text (for TEXT modality)
                        await websocket.send_text(json.dumps({"type": "text", "data": part.text}))

                # 3. ⚡ INTERRUPTION SIGNAL — tell the frontend to stop playback!
                if event.interrupted:
                    await websocket.send_text(json.dumps({"type": "interrupted"}))

                # 4. Turn complete signal
                if event.turn_complete:
                    await websocket.send_text(json.dumps({"type": "turn_complete"}))

        except Exception as e:
            print(f"Downstream closed: {e}")

    # --- Run both tasks concurrently ---
    try:
        await asyncio.gather(upstream_task(), downstream_task(), return_exceptions=True)
    finally:
        live_request_queue.close()  # Always close!