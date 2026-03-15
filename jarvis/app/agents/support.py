from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types

# ── Learning path tools ───────────────────────────────────────────────
def get_skill_tracks() -> dict:
    """Returns available skill tracks and their module counts."""
    return {
        "tracks": [
            {"id": "coding",    "name": "Coding Basics",        "modules": 12, "avg_minutes": 5},
            {"id": "sheets",    "name": "Spreadsheets & Data",   "modules": 8,  "avg_minutes": 5},
            {"id": "comms",     "name": "Communication",         "modules": 10, "avg_minutes": 5},
            {"id": "finance",   "name": "Financial Literacy",    "modules": 9,  "avg_minutes": 5},
            {"id": "digital",   "name": "Digital Tools",         "modules": 7,  "avg_minutes": 5},
            {"id": "jobsearch", "name": "Job Search Skills",     "modules": 6,  "avg_minutes": 5},
        ]
    }

def get_learner_progress(learner_id: str) -> dict:
    """Returns the learner's current progress across all skill tracks."""
    # In production replace with a real database lookup
    return {
        "learner_id": learner_id,
        "completed_modules": {"coding": 3, "sheets": 1, "comms": 0},
        "current_streak_days": 4,
        "total_minutes_learned": 35,
        "recommended_next": "coding",
        "weak_areas": ["loops", "functions"],
    }

def schedule_next_session(learner_id: str, track: str, preferred_time: str) -> dict:
    """Schedules the next micro-learning session for the learner."""
    return {
        "scheduled": True,
        "track": track,
        "time": preferred_time,
        "reminder_set": True,
        "message": f"Great! I'll remind you at {preferred_time} for a 5-minute {track} module."
    }

# ── Curriculum Planner Agent ──────────────────────────────────────────
curriculum_planner_llm = Gemini(
    model="gemini-2.5-flash-native-audio-latest",
)

curriculum_planner_agent = Agent(
    name="curriculum_planner",
    model=curriculum_planner_llm,
    instruction="""
        You are a curriculum planner for an adaptive lifelong-learning system focused on
        gig workers, students, and people in low-income areas who face automation-driven
        job displacement. Your job is to help learners build a personalised learning path
        that fits around their real daily routine — commutes, lunch breaks, evenings.

        CORE WORKFLOW:
        1. Greet warmly and ask about their current job or the role they're aiming for
        2. Ask about daily time availability ("Do you have 5–10 minutes during your commute?")
        3. Use get_learner_progress() to understand where they are
        4. Use get_skill_tracks() to explain available tracks in plain language
        5. Recommend the single most impactful track to start today with a clear reason
        6. Offer to schedule their next session using schedule_next_session()

        PLANNING PRINCIPLES:
        - Prioritise skills with highest near-term job-market return for their context
        - Each recommendation should connect directly to a real job outcome:
          "Learning basic Python means you can automate data entry — that's a skill
           that adds value on platforms like Upwork within weeks."
        - Account for access constraints: suggest offline-friendly approaches if needed
        - Never overwhelm — recommend ONE track and ONE first module at a time
        - Celebrate consistency over intensity: a 4-day streak of 5-minute sessions
          beats a single 2-hour session

        INTERRUPTION RULES:
        - If the learner interrupts → stop immediately and address what they said
        - Keep responses short: max 2–3 sentences before pausing for their input

        TONE: Warm, practical, and motivating. Speak like a knowledgeable friend,
        not a corporate advisor.
    """,
    tools=[
        FunctionTool(get_skill_tracks),
        FunctionTool(get_learner_progress),
        FunctionTool(schedule_next_session),
    ]
)