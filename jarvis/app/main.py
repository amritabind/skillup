"""
FastAPI + WebSocket server — Adaptive Learning Agents for Lifelong Skill-Building.
Run with: uvicorn app.main:app --reload --port 8000
"""

import asyncio
import json
import base64
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # loads GOOGLE_API_KEY from .env into os.environ

from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.websockets import WebSocketDisconnect
from google.genai import types
from google.genai.types import Blob, Content, Part, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig

from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Import agents
from app.agents.translator import skill_coach_agent
from app.agents.tutor import progress_assessor_agent
from app.agents.support import curriculum_planner_agent

# Import progress service
from app.progress_service import ProgressService

# ── App Setup ───────────────────────────────────────────────────────────────────
app = FastAPI(title="Adaptive Learning Agents for Lifelong Skill-Building")

# Global progress service (in-memory)
progress_service = ProgressService()

AGENT_MAP = {
    "coach":   skill_coach_agent,
    "assessor": progress_assessor_agent,
    "planner": curriculum_planner_agent,
}

# One shared session service (persists conversations across reconnects)
session_service = InMemorySessionService()

# One runner per agent type
runners = {
    name: Runner(app_name=name, agent=agent, session_service=session_service)
    for name, agent in AGENT_MAP.items()
}

# ── WebSocket Endpoint ───────────────────────────────────────────────
@app.websocket("/ws/{agent_type}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, agent_type: str, user_id: str,
                             voice: str = Query(default="Aoede")):
    await websocket.accept()

    if agent_type not in runners:
        await websocket.send_text(json.dumps({"error": f"Unknown agent: {agent_type}"}))
        await websocket.close()
        return

    runner = runners[agent_type]
    session_id = f"{agent_type}_{user_id}"

    # Get or create session
    session = await session_service.get_session(app_name=agent_type, user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name=agent_type, user_id=user_id, session_id=session_id)

    # Configure run — use proper Modality enum; omit transcription/resumption
    # configs that are not supported by native-audio models
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
    )

    # Fresh queue for this session
    live_request_queue = LiveRequestQueue()

    # ── UPSTREAM: Browser → Agent ─────────────────────────────
    async def upstream_task():
        try:
            while True:
                message = await websocket.receive()

                # WebSocket disconnect frame — exit cleanly
                if message.get("type") == "websocket.disconnect":
                    print("[UPSTREAM] Disconnect frame received")
                    break

                if "bytes" in message:
                    live_request_queue.send_realtime(
                        Blob(mime_type="audio/pcm;rate=16000", data=message["bytes"])
                    )
                elif "text" in message:
                    data = json.loads(message["text"])

                    if data["type"] == "text":
                        live_request_queue.send_content(
                            Content(role="user", parts=[Part.from_text(text=data["data"])])
                        )
                    elif data["type"] == "image":
                        live_request_queue.send_realtime(
                            Blob(
                                mime_type=data.get("mime_type", "image/jpeg"),
                                data=base64.b64decode(data["data"])
                            )
                        )
        except WebSocketDisconnect:
            print("[UPSTREAM] Client disconnected")
        except Exception as e:
            print(f"[UPSTREAM] Error: {e}")

    # ── DOWNSTREAM: Agent → Browser ───────────────────────────
    async def downstream_task():
        try:
            async for event in runner.run_live(
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_request_queue,
                run_config=run_config,
            ):
                # Audio transcript (show in UI as subtitles)
                if event.output_transcription and event.output_transcription.text:
                    await websocket.send_text(json.dumps({
                        "type": "transcript",
                        "data": event.output_transcription.text
                    }))

                part = event.content and event.content.parts and event.content.parts[0]
                if part:
                    if part.inline_data:
                        mime = part.inline_data.mime_type or ""
                        print(f"[DEBUG] inline_data mime={mime} bytes={len(part.inline_data.data)}")
                        # Accept any audio/* format (pcm, wav, mp3, ogg, etc.)
                        if mime.startswith("audio/"):
                            await websocket.send_text(json.dumps({
                                "type": "audio",
                                "mime": mime,
                                "data": base64.b64encode(part.inline_data.data).decode("ascii")
                            }))
                    elif part.text:
                        print(f"[DEBUG] text partial={event.partial}: {part.text[:80]}")
                        if event.partial:
                            await websocket.send_text(json.dumps({"type": "text", "data": part.text}))

                if event.interrupted:
                    await websocket.send_text(json.dumps({"type": "interrupted"}))

                if event.turn_complete:
                    await websocket.send_text(json.dumps({"type": "turn_complete"}))

        except WebSocketDisconnect:
            print(f"[DOWNSTREAM] Client disconnected")
        except Exception as e:
            print(f"[DOWNSTREAM] Error: {e}")
            try:
                await websocket.send_text(json.dumps({"type": "error", "data": str(e)}))
            except Exception:
                pass

    # Run both tasks — cancel the other when one finishes
    upstream_t  = asyncio.create_task(upstream_task())
    downstream_t = asyncio.create_task(downstream_task())
    try:
        done, pending = await asyncio.wait(
            {upstream_t, downstream_t},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
    finally:
        live_request_queue.close()
        try:
            await websocket.close()
        except Exception:
            pass

# ── Progress Tracking Endpoints ────────────────────────────────────
@app.get("/api/progress/{user_id}")
async def get_progress(user_id: str):
    """Get user's progress."""
    return progress_service.get_user_progress(user_id)

@app.post("/api/progress/{user_id}/xp")
async def add_xp(user_id: str, skill: str, amount: int):
    """Add XP to a skill."""
    return progress_service.add_xp(user_id, skill, amount)

@app.post("/api/progress/{user_id}/module")
async def complete_module(user_id: str, skill: str, module_id: str, xp_reward: int = 50):
    """Mark module as completed."""
    return progress_service.add_module_completion(user_id, skill, module_id, xp_reward)

@app.post("/api/progress/{user_id}/quiz")
async def record_quiz(user_id: str, skill: str, score: float):
    """Record quiz score (0-100)."""
    return progress_service.record_quiz_score(user_id, skill, score)

@app.post("/api/progress/{user_id}/hours")
async def add_hours(user_id: str, skill: str, hours: float):
    """Add learning hours."""
    return progress_service.add_learning_time(user_id, skill, hours)

@app.post("/api/progress/{user_id}/streak")
async def update_streak(user_id: str, days: int):
    """Update streak count."""
    return progress_service.update_streak(user_id, days)

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Get top users by XP."""
    return {"users": progress_service.get_leaderboard(limit)}

# ── Static files (frontend) ────────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")