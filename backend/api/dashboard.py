"""
Dashboard API routes for user statistics and recent sessions.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.deps import get_current_user
from backend.models.user import User
from backend.models.workout import WorkoutLog

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DashboardStats(BaseModel):
    total_sessions: int
    total_duration_min: int
    total_exercises: int
    streak_days: int


class RecentSession(BaseModel):
    id: str
    movement: str
    date: str
    reps: int
    accuracy: int
    duration_min: Optional[int] = None


class DashboardResponse(BaseModel):
    stats: DashboardStats
    recent_sessions: List[RecentSession]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user dashboard statistics."""
    # Query all workouts for this user
    workouts = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id
    ).all()
    
    # Calculate statistics
    total_sessions = len(workouts)
    total_duration_min = sum(w.duration_min or 0 for w in workouts)
    
    # Count total exercises (if exercises field exists)
    total_exercises = 0
    for w in workouts:
        if w.exercises and isinstance(w.exercises, list):
            total_exercises += len(w.exercises)
        elif w.rep_count:
            total_exercises += w.rep_count
    
    # Calculate streak (consecutive days with workouts)
    streak_days = _calculate_streak(workouts)
    
    return DashboardStats(
        total_sessions=total_sessions,
        total_duration_min=total_duration_min,
        total_exercises=total_exercises,
        streak_days=streak_days
    )


@router.get("/recent-sessions", response_model=List[RecentSession])
async def get_recent_sessions(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent training sessions for the user."""
    workouts = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id
    ).order_by(desc(WorkoutLog.session_date)).limit(limit).all()
    
    sessions = []
    for w in workouts:
        # Extract movement name
        movement = "深蹲"  # default
        if w.exercise_type:
            movement = w.exercise_type
        elif w.exercises and isinstance(w.exercises, list) and len(w.exercises) > 0:
            first_ex = w.exercises[0]
            if isinstance(first_ex, dict):
                movement = first_ex.get("name", "深蹲")
        
        # Calculate accuracy based on errors
        accuracy = 100
        if w.errors and isinstance(w.errors, list):
            error_count = len(w.errors)
            accuracy = max(0, 100 - error_count * 10)
        
        sessions.append(RecentSession(
            id=w.id,
            movement=movement,
            date=w.session_date.isoformat() if w.session_date else "",
            reps=w.rep_count or 0,
            accuracy=accuracy,
            duration_min=w.duration_min
        ))
    
    return sessions


def _calculate_streak(workouts: List[WorkoutLog]) -> int:
    """Calculate consecutive day streak from workout history."""
    if not workouts:
        return 0
    
    # Get unique dates with workouts
    dates = set()
    for w in workouts:
        if w.session_date:
            dates.add(w.session_date)
    
    if not dates:
        return 0
    
    # Sort dates in descending order
    sorted_dates = sorted(dates, reverse=True)
    
    # Check if most recent workout is today or yesterday
    today = datetime.now().date()
    most_recent = sorted_dates[0]
    
    if (today - most_recent).days > 1:
        # Streak broken
        return 0
    
    # Count consecutive days
    streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i-1] - sorted_dates[i]).days == 1:
            streak += 1
        else:
            break
    
    return streak
