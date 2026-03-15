# SkillUp — Adaptive Learning Agents for Lifelong Skill-Building

> Bite-sized, voice-driven learning modules delivered in real time, adapting to learner pace and context — built for gig workers, students, and anyone upskilling on the go.

---

## Problem Statement

Automation is displacing an estimated **85 million jobs by 2025** (World Economic Forum). The workers most at risk — gig workers, students in low-income areas — often lack consistent access to structured learning. Traditional e-learning requires long blocks of focused time and stable internet. This system takes the opposite approach: **interrupt daily routines with 5-minute, voice-first, adaptive skill modules** delivered through a phone browser during commutes, breaks, or downtime.

---

## How It Works — End to End

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROWSER (Frontend)                          │
│                                                                 │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────────┐   │
│  │  Skill     │  │  Progress    │  │  Curriculum           │   │
│  │  Coach     │  │  Check       │  │  Planner              │   │
│  │  (voice)   │  │  (cam+voice) │  │  (voice + schedule)   │   │
│  └─────┬──────┘  └──────┬───────┘  └───────────┬───────────┘   │
│        │                │                       │               │
│  ┌─────▼────────────────▼───────────────────────▼───────────┐  │
│  │           WebSocket  ws://localhost:8000/ws/{agent}/{uid} │  │
│  └─────────────────────────────┬─────────────────────────────┘  │
└────────────────────────────────│────────────────────────────────┘
                                 │  PCM audio bytes (binary)
                                 │  JSON { type, data }  (text)
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                    FastAPI Server  (app/main.py)                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  websocket_endpoint()  /ws/{agent_type}/{user_id}        │   │
│  │                                                          │   │
│  │   upstream_task ──────────────────────────────────────►  │   │
│  │   Browser input → LiveRequestQueue                       │   │
│  │     • PCM bytes  → Blob(audio/pcm;rate=16000)            │   │
│  │     • text msg   → Content(role=user, Part.from_text)    │   │
│  │     • image msg  → Blob(image/jpeg)                      │   │
│  │                                                          │   │
│  │   downstream_task ◄───────────────────────────────────── │   │
│  │   runner.run_live() → WebSocket                          │   │
│  │     • audio/pcm  → { type:"audio",      data: base64 }  │   │
│  │     • transcript → { type:"transcript", data: text  }   │   │
│  │     • partial txt→ { type:"text",       data: text  }   │   │
│  │     • interrupted→ { type:"interrupted" }               │   │
│  │     • turn done  → { type:"turn_complete" }              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│   AGENT_MAP                                                      │
│   ┌──────────┬───────────────────┬──────────────────────────┐   │
│   │ "coach"  │ "assessor"        │ "planner"                │   │
│   └────┬─────┴──────────┬────────┴───────────────┬──────────┘   │
└────────│────────────────│────────────────────────│──────────────┘
         │                │                         │
         ▼                ▼                         ▼
┌────────────────────────────────────────────────────────────────┐
│              Google ADK  —  Agent Layer                        │
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  Skill Coach    │  │Progress Assessor│  │  Curriculum   │  │
│  │  (Aoede voice)  │  │  (Puck voice)   │  │  Planner      │  │
│  │                 │  │                 │  │  (Charon)     │  │
│  │  Micro-lessons  │  │  Vision: reads  │  │  Tools:       │  │
│  │  Hook→Concept   │  │  phone camera   │  │  • skill_tracks│ │
│  │  →Example       │  │  photos of work │  │  • learner_    │  │
│  │  →Challenge     │  │  Assess mastery │  │    progress   │  │
│  │  →Recap         │  │  Give next step │  │  • schedule_  │  │
│  └────────┬────────┘  └────────┬────────┘  │    session    │  │
│           │                   │            └──────┬────────┘  │
└───────────│───────────────────│────────────────────│──────────┘
            │                   │                    │
            ▼                   ▼                    ▼
┌────────────────────────────────────────────────────────────────┐
│          Gemini Live API  (gemini-3-flash-preview)          │
│                                                                │
│  • Native bidirectional audio streaming                        │
│  • Interruption handling built-in                              │
│  • Vision understanding (multimodal)                           │
│  • Session resumption across network drops                     │
└────────────────────────────────────────────────────────────────┘
```

---

## The Three Agents

### 1. Skill Coach (`/ws/coach/...`)
**Voice:** Aoede

Delivers adaptive 5-minute micro-lessons across six skill tracks. Each module follows a fixed structure:

```
Hook (10s) → Core Concept (60-90s) → Real-world Example (30s)
    → Mini Challenge (60s) → Recap + Bridge (20s)
```

The coach **adapts in real time**: if the learner struggles it slows down and uses relatable analogies (commutes, grocery shopping); if they ace it, it skips basics and increases depth. It never lectures for more than 60 seconds without checking back.

**Skill tracks available:**
- Coding Basics (Python, web, no-code)
- Spreadsheets & Data
- Communication & Writing
- Financial Literacy
- Digital Tools
- Job Search Skills

---

### 2. Progress Assessor (`/ws/assessor/...`)
**Voice:** Puck | **Requires camera**

The learner holds up their phone camera to show handwritten notes, code on paper, a budget worksheet, or a resume draft. The agent:

1. Reads all visible content using Gemini's vision capability
2. Identifies the skill and assesses mastery (Beginner → Strong)
3. Calls out 1–2 things done correctly first
4. Identifies the **single most important thing** to fix
5. Gives one concrete 5-minute next-step practice task

---

### 3. Curriculum Planner (`/ws/planner/...`)
**Voice:** Charon | **Uses tools**

Interviews the learner about their job context and daily availability, then builds a personalised learning path. Uses three function tools:

| Tool | Purpose |
|---|---|
| `get_skill_tracks()` | Lists all available tracks with module counts |
| `get_learner_progress(learner_id)` | Returns completed modules, streak, weak areas |
| `schedule_next_session(learner_id, track, time)` | Books the next micro-session and sets a reminder |

---

## Architecture — Data Flow Detail

```
MICROPHONE INPUT
    │
    │  Float32 PCM  →  converted to Int16 PCM (4096-sample chunks)
    │  sent as binary WebSocket frames
    ▼
upstream_task()
    │
    │  Blob(mime_type="audio/pcm;rate=16000", data=bytes)
    │  LiveRequestQueue.send_realtime()
    ▼
Gemini Live API  ──  processes audio stream continuously
    │                native VAD (voice activity detection)
    │                native interruption handling
    ▼
downstream_task()  ←  runner.run_live() async generator
    │
    ├── event.output_transcription.text  →  { type: "transcript" }
    ├── part.inline_data (audio/pcm)     →  { type: "audio", data: base64 }
    ├── part.text + event.partial        →  { type: "text" }
    ├── event.interrupted                →  { type: "interrupted" }  ← stops playback
    └── event.turn_complete              →  { type: "turn_complete" }
    │
    ▼
BROWSER
    │
    ├── audio  →  decode base64 → Int16 → Float32 → AudioContext.createBufferSource
    ├── transcript / text  →  appended to lesson transcript panel
    └── interrupted  →  audioContext.close()  (cuts playback immediately)
```

---

## Project Structure

```
jarvis/
├── app/
│   ├── main.py               # FastAPI server + WebSocket handler
│   ├── core_pattern.py       # Reference doc: the ADK streaming pattern
│   ├── agents/
│   │   ├── translator.py     # Skill Coach agent
│   │   ├── tutor.py          # Progress Assessor agent
│   │   └── support.py        # Curriculum Planner agent
│   └── static/
│       ├── index.html        # Frontend UI
│       └── send_image.js     # Camera capture utility
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10+
- A Google Cloud project with the **Gemini Live API** enabled
- `GOOGLE_API_KEY` or Application Default Credentials configured

---

## Installation

```bash
# 1. Clone / navigate to the project
cd jarvis

# 2. Install dependencies
pip install fastapi uvicorn google-adk google-genai

# 3. Set your API key
$env:GOOGLE_API_KEY = "your-key-here"          # PowerShell
# export GOOGLE_API_KEY="your-key-here"         # bash/zsh

# 4. Start the server
python -m uvicorn app.main:app --reload --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Usage

1. **Select an agent** from the three cards at the top.
2. Click **Start Session** — your microphone activates and a WebSocket opens.
3. Speak naturally. The agent responds with voice and shows a transcript below.
4. **Interrupt at any time** — just start talking; Gemini's native VAD stops the agent mid-sentence.
5. For the **Progress Check** agent, grant camera access and click **Send Work Photo** to let the agent see your work.
6. Click **Stop** to end the session. Progress bars update after each session.

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| One WebSocket per session | Keeps state simple; LiveRequestQueue is not thread-safe across sessions |
| Binary frames for audio, JSON for control | Avoids base64 overhead on the hot audio path |
| `asyncio.gather` for upstream + downstream | True bidirectionality — sending and receiving happen concurrently |
| `live_request_queue.close()` in `finally` | Prevents the run_live generator from hanging after disconnect |
| Gemini Live API (not standard chat) | Only the Live API supports real-time audio streaming + native interruption |
| 5-minute module cap | Matches the attention window of commuters; reduces dropout |

---

## Extending the System

**Add a new skill track:** Update the `get_skill_tracks()` function in [app/agents/support.py](app/agents/support.py) and add corresponding module content to the Skill Coach's instruction.

**Persist learner progress:** Replace the mock dict in `get_learner_progress()` with a database call (SQLite, Postgres, Firebase — any async-compatible driver works).

**Push notifications for commute reminders:** Add a `/schedule` REST endpoint that stores the preferred time from `schedule_next_session()` and uses a background task (APScheduler or Celery) to push a browser notification.

**Multi-language support:** Add a `language_code` parameter to the WebSocket URL and pass it through to the agent's `SpeechConfig` at session creation time.
