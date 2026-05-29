"""
Workout logging API routes.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.deps import get_current_user
from backend.models.user import User
from backend.models.workout import WorkoutLog

router = APIRouter(prefix="/api/workout", tags=["workout"])


class SaveWorkoutRequest(BaseModel):
    session_id: str
    exercise_type: str
    duration_min: int
    rep_count: int
    errors: Optional[List[str]] = None
    error_details: Optional[Dict[str, int]] = None
    angles_log: Optional[List[Any]] = None


class SaveWorkoutResponse(BaseModel):
    success: bool
    id: str


class WorkoutLogResponse(BaseModel):
    id: str
    session_date: str
    exercise_type: str
    duration_min: int
    rep_count: int
    errors: Optional[List[str]] = None


@router.post("/save", response_model=SaveWorkoutResponse)
async def save_workout(
    request: SaveWorkoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a completed workout session."""
    try:
        workout = WorkoutLog(
            user_id=current_user.id,
            session_date=date.today(),
            day_label=f"Day - {request.exercise_type.capitalize()}",
            exercise_type=request.exercise_type,
            duration_min=request.duration_min,
            rep_count=request.rep_count,
            errors=request.errors,
            error_details=request.error_details,
            angles_log=request.angles_log,
        )
        
        db.add(workout)
        db.commit()
        db.refresh(workout)
        
        return SaveWorkoutResponse(success=True, id=workout.id)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save workout: {str(e)}")


@router.get("/history", response_model=List[WorkoutLogResponse])
async def get_workout_history(
    limit: Optional[int] = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's workout history."""
    workouts = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id
    ).order_by(WorkoutLog.session_date.desc()).limit(limit).all()
    
    return [
        WorkoutLogResponse(
            id=w.id,
            session_date=w.session_date.isoformat() if w.session_date else "",
            exercise_type=w.exercise_type or "未知动作",
            duration_min=w.duration_min or 0,
            rep_count=w.rep_count or 0,
            errors=w.errors
        )
        for w in workouts
    ]


@router.get("/stats")
async def get_workout_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get workout statistics for the user."""
    workouts = db.query(WorkoutLog).filter(
        WorkoutLog.user_id == current_user.id
    ).all()
    
    # Calculate stats
    total_sessions = len(workouts)
    total_reps = sum(w.rep_count or 0 for w in workouts)
    total_duration = sum(w.duration_min or 0 for w in workouts)
    
    # Get unique exercise types
    exercise_types = set(w.exercise_type for w in workouts if w.exercise_type)
    
    # Calculate streak
    workout_dates = sorted(set(w.session_date for w in workouts if w.session_date), reverse=True)
    streak = 0
    today = date.today()
    
    if workout_dates:
        # Check if most recent is today or yesterday
        if (today - workout_dates[0]).days <= 1:
            streak = 1
            for i in range(1, len(workout_dates)):
                if (workout_dates[i-1] - workout_dates[i]).days == 1:
                    streak += 1
                else:
                    break
    
    return {
        "total_sessions": total_sessions,
        "total_reps": total_reps,
        "total_duration_min": total_duration,
        "exercise_types": list(exercise_types),
        "streak_days": streak
    }
