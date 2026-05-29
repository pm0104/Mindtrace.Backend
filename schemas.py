from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MoodCheckinCreate(BaseModel):
    mood_score: int = Field(ge=1, le=5)
    factors: list[str] = Field(default_factory=list)
    note: str = ""


class MoodCheckinRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mood_score: int
    factors: list[str]
    note: str
    created_at: datetime


class HabitCreate(BaseModel):
    label: str = Field(min_length=1, max_length=255)
    done: bool = False
    streak: int = Field(default=0, ge=0)


class HabitUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    done: bool | None = None
    streak: int | None = Field(default=None, ge=0)
    date: str | None = None


class HabitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    done: bool
    streak: int
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class AuthResponse(BaseModel):
    token: str
    user: UserRead
