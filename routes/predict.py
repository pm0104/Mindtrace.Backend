import sys
from importlib import import_module
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

try:
    from .auth import get_current_user
except ImportError:
    from routes.auth import get_current_user


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


router = APIRouter(prefix="/api/predict", tags=["predictions"])


class PredictionInput(BaseModel):
    mood_score: int = Field(ge=1, le=5)
    note_length: int = Field(ge=0)
    has_note: int = Field(ge=0, le=1)
    factor_count: int = Field(ge=0)
    poor_sleep: int = Field(ge=0, le=1)
    work_stress: int = Field(ge=0, le=1)
    exercise_factor: int = Field(ge=0, le=1)
    social_media_factor: int = Field(ge=0, le=1)
    good_food: int = Field(ge=0, le=1)
    socializing: int = Field(ge=0, le=1)
    loneliness: int = Field(ge=0, le=1)
    achievement: int = Field(ge=0, le=1)
    active_habit_count: int = Field(ge=0)
    completed_habits: int = Field(ge=0)
    completion_rate: float = Field(ge=0, le=1)
    longest_streak: int = Field(ge=0)


@router.post("/")
def get_prediction(data: PredictionInput, _current_user=Depends(get_current_user)):
    try:
        predict_module = import_module("ml.predict")
        predict_mental_health = predict_module.predict_mental_health
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prediction module is not available.",
        ) from exc

    return predict_mental_health(
        mood_score=data.mood_score,
        note_length=data.note_length,
        has_note=data.has_note,
        factor_count=data.factor_count,
        poor_sleep=data.poor_sleep,
        work_stress=data.work_stress,
        exercise_factor=data.exercise_factor,
        social_media_factor=data.social_media_factor,
        good_food=data.good_food,
        socializing=data.socializing,
        loneliness=data.loneliness,
        achievement=data.achievement,
        active_habit_count=data.active_habit_count,
        completed_habits=data.completed_habits,
        completion_rate=data.completion_rate,
        longest_streak=data.longest_streak,
    )
