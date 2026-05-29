from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, status

try:
    from ..database import get_db
    from ..models import MoodCheckin, User
    from .auth import get_current_user
    from ..schemas import MoodCheckinCreate, MoodCheckinRead
except ImportError:
    from database import get_db
    from models import MoodCheckin, User
    from routes.auth import get_current_user
    from schemas import MoodCheckinCreate, MoodCheckinRead


router = APIRouter(prefix="/api/mood", tags=["mood"])


@router.get("/", response_model=list[MoodCheckinRead])
def get_mood_checkins(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(MoodCheckin)
        .filter(MoodCheckin.user_id == current_user.id)
        .order_by(MoodCheckin.created_at.desc())
        .all()
    )


@router.post("/", response_model=MoodCheckinRead, status_code=status.HTTP_201_CREATED)
def create_mood_checkin(
    payload: MoodCheckinCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mood_checkin = MoodCheckin(
        user_id=current_user.id,
        mood_score=payload.mood_score,
        factors=payload.factors,
        note=payload.note,
    )
    db.add(mood_checkin)
    db.commit()
    db.refresh(mood_checkin)
    return mood_checkin
