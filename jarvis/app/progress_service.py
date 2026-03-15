"""
Progress tracking system — in-memory storage for XP, badges, hours, modules, skill levels, quiz scores.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

class SkillLevel(str, Enum):
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    EXPERT = "Expert"

@dataclass
class Badge:
    """Achievement badge."""
    id: str
    name: str
    description: str
    icon: str  # emoji or icon name
    unlocked_at: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class SkillProgress:
    """Per-skill progress tracking."""
    name: str
    level: SkillLevel = SkillLevel.BEGINNER
    xp: int = 0  # XP within this skill
    modules_completed: int = 0
    quiz_score: float = 0.0  # 0-100
    hours_learned: float = 0.0
    
    def to_dict(self):
        return {
            "name": self.name,
            "level": self.level.value,
            "xp": self.xp,
            "modules_completed": self.modules_completed,
            "quiz_score": self.quiz_score,
            "hours_learned": self.hours_learned
        }

@dataclass
class UserProgress:
    """Complete user progress profile."""
    user_id: str
    total_xp: int = 0
    total_hours: float = 0.0
    streak_days: int = 0
    last_session: Optional[str] = None
    skills: Dict[str, SkillProgress] = field(default_factory=dict)
    badges: Dict[str, Badge] = field(default_factory=dict)
    quiz_scores: List[Dict] = field(default_factory=list)  # [{"skill": "...", "score": 85, "date": "..."}]
    modules_completed: List[str] = field(default_factory=list)  # ["coding-101", "spreadsheet-02", ...]
    
    def get_overall_level(self) -> SkillLevel:
        """Calculate overall skill level based on all skills."""
        if not self.skills:
            return SkillLevel.BEGINNER
        avg_xp = sum(s.xp for s in self.skills.values()) / len(self.skills)
        if avg_xp >= 500:
            return SkillLevel.EXPERT
        elif avg_xp >= 200:
            return SkillLevel.INTERMEDIATE
        return SkillLevel.BEGINNER
    
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "total_xp": self.total_xp,
            "total_hours": self.total_hours,
            "streak_days": self.streak_days,
            "overall_level": self.get_overall_level().value,
            "last_session": self.last_session,
            "skills": {name: skill.to_dict() for name, skill in self.skills.items()},
            "badges": {id: badge.to_dict() for id, badge in self.badges.items()},
            "quiz_scores": self.quiz_scores,
            "modules_completed": self.modules_completed,
            "badge_count": len(self.badges)
        }


class ProgressService:
    """Manage progress for all users in-memory."""
    
    # Define all possible badges
    AVAILABLE_BADGES = {
        "first_session": Badge(
            id="first_session",
            name="Getting Started",
            description="Complete your first learning session",
            icon="🚀"
        ),
        "xp_100": Badge(
            id="xp_100",
            name="Rising Star",
            description="Earn 100 XP",
            icon="⭐"
        ),
        "xp_500": Badge(
            id="xp_500",
            name="Power Learner",
            description="Earn 500 XP",
            icon="💪"
        ),
        "xp_1000": Badge(
            id="xp_1000",
            name="Knowledge Master",
            description="Earn 1000 XP",
            icon="👑"
        ),
        "5_modules": Badge(
            id="5_modules",
            name="Completionist",
            description="Complete 5 modules",
            icon="✅"
        ),
        "perfect_quiz": Badge(
            id="perfect_quiz",
            name="Perfect Score",
            description="Score 100% on a quiz",
            icon="🎯"
        ),
        "10_hours": Badge(
            id="10_hours",
            name="Time Invested",
            description="Learn for 10+ hours",
            icon="⏱️"
        ),
        "7_streak": Badge(
            id="7_streak",
            name="Weekly Grinder",
            description="Maintain 7-day streak",
            icon="🔥"
        ),
        "skill_master": Badge(
            id="skill_master",
            name="Skill Master",
            description="Reach Expert in any skill",
            icon="🏆"
        ),
    }
    
    def __init__(self):
        self.users: Dict[str, UserProgress] = {}
    
    def get_or_create_user(self, user_id: str) -> UserProgress:
        """Get existing user progress or create new one."""
        if user_id not in self.users:
            self.users[user_id] = UserProgress(user_id=user_id)
        return self.users[user_id]
    
    def add_xp(self, user_id: str, skill_name: str, xp_amount: int) -> Dict:
        """Add XP to user and skill."""
        user = self.get_or_create_user(user_id)
        user.total_xp += xp_amount
        
        # Update skill XP
        if skill_name not in user.skills:
            user.skills[skill_name] = SkillProgress(name=skill_name)
        user.skills[skill_name].xp += xp_amount
        
        # Check level up
        user.skills[skill_name].level = self._calculate_level(user.skills[skill_name].xp)
        
        # Check badges
        self._check_badge_unlocks(user_id)
        
        return {
            "total_xp": user.total_xp,
            "skill_xp": user.skills[skill_name].xp,
            "skill_level": user.skills[skill_name].level.value
        }
    
    def add_module_completion(self, user_id: str, skill_name: str, module_id: str, xp_reward: int = 50) -> Dict:
        """Mark module as completed."""
        user = self.get_or_create_user(user_id)
        
        if module_id not in user.modules_completed:
            user.modules_completed.append(module_id)
        
        if skill_name not in user.skills:
            user.skills[skill_name] = SkillProgress(name=skill_name)
        user.skills[skill_name].modules_completed += 1
        
        # Award XP
        return self.add_xp(user_id, skill_name, xp_reward)
    
    def record_quiz_score(self, user_id: str, skill_name: str, score: float) -> Dict:
        """Record quiz score (0-100)."""
        user = self.get_or_create_user(user_id)
        score = max(0, min(100, score))
        
        user.quiz_scores.append({
            "skill": skill_name,
            "score": score,
            "date": datetime.now().isoformat()
        })
        
        if skill_name not in user.skills:
            user.skills[skill_name] = SkillProgress(name=skill_name)
        user.skills[skill_name].quiz_score = score
        
        # Award XP based on score
        xp_reward = int(score / 10) * 10  # 100 = 100 XP, 85 = 80 XP, etc.
        self.add_xp(user_id, skill_name, xp_reward)
        
        return {
            "score": score,
            "xp_earned": xp_reward,
            "total_xp": user.total_xp
        }
    
    def add_learning_time(self, user_id: str, skill_name: str, hours: float) -> Dict:
        """Add hours learned."""
        user = self.get_or_create_user(user_id)
        user.total_hours += hours
        
        if skill_name not in user.skills:
            user.skills[skill_name] = SkillProgress(name=skill_name)
        user.skills[skill_name].hours_learned += hours
        
        # Update last session
        user.last_session = datetime.now().isoformat()
        
        self._check_badge_unlocks(user_id)
        
        return {
            "total_hours": user.total_hours,
            "skill_hours": user.skills[skill_name].hours_learned
        }
    
    def update_streak(self, user_id: str, streak_days: int) -> Dict:
        """Update streak count."""
        user = self.get_or_create_user(user_id)
        user.streak_days = streak_days
        self._check_badge_unlocks(user_id)
        return {"streak_days": user.streak_days}
    
    def _calculate_level(self, xp: int) -> SkillLevel:
        """Determine skill level from XP."""
        if xp >= 500:
            return SkillLevel.EXPERT
        elif xp >= 200:
            return SkillLevel.INTERMEDIATE
        return SkillLevel.BEGINNER
    
    def _check_badge_unlocks(self, user_id: str) -> List[str]:
        """Check and unlock badges. Returns newly unlocked badge IDs."""
        user = self.users.get(user_id)
        if not user:
            return []
        
        newly_unlocked = []
        
        # First session
        if "first_session" not in user.badges and user.total_xp > 0:
            self._unlock_badge(user_id, "first_session")
            newly_unlocked.append("first_session")
        
        # XP milestones
        if "xp_100" not in user.badges and user.total_xp >= 100:
            self._unlock_badge(user_id, "xp_100")
            newly_unlocked.append("xp_100")
        if "xp_500" not in user.badges and user.total_xp >= 500:
            self._unlock_badge(user_id, "xp_500")
            newly_unlocked.append("xp_500")
        if "xp_1000" not in user.badges and user.total_xp >= 1000:
            self._unlock_badge(user_id, "xp_1000")
            newly_unlocked.append("xp_1000")
        
        # Module completion
        if "5_modules" not in user.badges and len(user.modules_completed) >= 5:
            self._unlock_badge(user_id, "5_modules")
            newly_unlocked.append("5_modules")
        
        # Perfect quiz
        if "perfect_quiz" not in user.badges:
            if any(q["score"] == 100 for q in user.quiz_scores):
                self._unlock_badge(user_id, "perfect_quiz")
                newly_unlocked.append("perfect_quiz")
        
        # Hours learned
        if "10_hours" not in user.badges and user.total_hours >= 10:
            self._unlock_badge(user_id, "10_hours")
            newly_unlocked.append("10_hours")
        
        # Streak
        if "7_streak" not in user.badges and user.streak_days >= 7:
            self._unlock_badge(user_id, "7_streak")
            newly_unlocked.append("7_streak")
        
        # Skill master
        if "skill_master" not in user.badges:
            if any(s.level == SkillLevel.EXPERT for s in user.skills.values()):
                self._unlock_badge(user_id, "skill_master")
                newly_unlocked.append("skill_master")
        
        return newly_unlocked
    
    def _unlock_badge(self, user_id: str, badge_id: str):
        """Unlock a badge for a user."""
        user = self.users.get(user_id)
        if not user or badge_id in user.badges:
            return
        
        badge = self.AVAILABLE_BADGES[badge_id].to_dict()
        badge["unlocked_at"] = datetime.now().isoformat()
        user.badges[badge_id] = Badge(**badge)
    
    def get_user_progress(self, user_id: str) -> Dict:
        """Get complete user progress."""
        user = self.get_or_create_user(user_id)
        return user.to_dict()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by XP."""
        users = sorted(
            self.users.values(),
            key=lambda u: u.total_xp,
            reverse=True
        )[:limit]
        return [u.to_dict() for u in users]
