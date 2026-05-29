from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..models import Habit, User
    from .auth import get_current_user
    from ..schemas import HabitCreate, HabitRead, HabitUpdate
except ImportError:
    from database import get_db
    from models import Habit, User
    from routes.auth import get_current_user
    from schemas import HabitCreate, HabitRead, HabitUpdate


router = APIRouter(prefix="/api/habits", tags=["habits"])


def parse_habit_date(value: str | None) -> date_type:
    if value is None:
        return date_type.today()

    try:
        return date_type.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date. Use YYYY-MM-DD.") from exc


def sync_habits_for_date(db: Session, target_date: date_type, user_id: int) -> list[Habit]:
    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.created_at.asc()).all()
    changed = False

    for habit in habits:
        last_update_date = habit.updated_at.date() if habit.updated_at else habit.created_at.date()
        if habit.done and last_update_date < target_date:
            habit.done = False
            changed = True

    if changed:
        db.commit()
        for habit in habits:
            db.refresh(habit)

    return habits


@router.get("/", response_model=list[HabitRead])
def get_habits(
    date: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target_date = parse_habit_date(date)
    return sync_habits_for_date(db, target_date, current_user.id)


@router.post("/", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
def create_habit(
    payload: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    habit = Habit(
        user_id=current_user.id,
        label=payload.label.strip(),
        done=payload.done,
        streak=payload.streak,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.patch("/{habit_id}", response_model=HabitRead)
def update_habit(
    habit_id: int,
    payload: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id).first()
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    target_date = parse_habit_date(payload.date)
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("date", None)

    if "label" in updates:
        updates["label"] = updates["label"].strip()

    if "done" in updates:
        next_done = updates.pop("done")
        last_update_date = habit.updated_at.date() if habit.updated_at else habit.created_at.date()

        if next_done and not habit.done:
            if last_update_date < target_date:
                habit.streak += 1
            elif last_update_date == target_date:
                habit.streak = max(1, habit.streak)
        elif not next_done and habit.done and last_update_date == target_date:
            habit.streak = max(0, habit.streak - 1)

        habit.done = next_done

    for field, value in updates.items():
        setattr(habit, field, value)

    db.commit()
    db.refresh(habit)
    return habit


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_habit(
    habit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == current_user.id).first()
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    db.delete(habit)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
