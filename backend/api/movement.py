"""
movementlibAPIroute
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.deps import get_current_user
from backend.models.movement import Movement
from backend.models.user import User
from backend.schemas.movement import MovementResponse, MovementCreate

router = APIRouter(prefix="/api/movements", tags=["movementlib"])


@router.get("", response_model=List[MovementResponse])
async def list_movements(
    muscle_group: Optional[str] = Query(None, description="按肌群Filter"),
    category: Optional[str] = Query(None, description="按typeFilter"),
    difficulty: Optional[str] = Query(None, description="按难度Filter"),
    equipment: Optional[str] = Query(None, description="按MachineFilter"),
    search: Optional[str] = Query(None, description="searchname"),
    db: Session = Depends(get_db)
):
    """getgetmovementlist, branchholdFilter"""
    query = db.query(Movement)

    if muscle_group:
        query = query.filter(Movement.muscle_group == muscle_group)
    if category:
        query = query.filter(Movement.category == category)
    if difficulty:
        query = query.filter(Movement.difficulty == difficulty)
    if equipment:
        query = query.filter(Movement.equipment == equipment)
    if search:
        query = query.filter(
            Movement.name.contains(search) | Movement.name_en.contains(search)
        )

    return query.all()


@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """getgetplace splitclass"""
    muscle_groups = db.query(Movement.muscle_group).distinct().all()
    categories = db.query(Movement.category).distinct().all()
    equipment_types = db.query(Movement.equipment).distinct().all()

    return {
        "muscle_groups": [g[0] for g in muscle_groups if g[0]],
        "categories": [c[0] for c in categories if c[0]],
        "equipment": [e[0] for e in equipment_types if e[0]],
    }


@router.get("/{movement_id}", response_model=MovementResponse)
async def get_movement(movement_id: str, db: Session = Depends(get_db)):
    """getgetmovement详情"""
    movement = db.query(Movement).filter(Movement.id == movement_id).first()
    if not movement:
        raise HTTPException(status_code=404, detail="movement store ")
    return movement


@router.post("", response_model=MovementResponse)
async def create_movement(
    data: MovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """createmovement(manage员)"""
    movement = Movement(**data.model_dump())
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement
