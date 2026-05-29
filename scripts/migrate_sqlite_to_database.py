from datetime import datetime
import json
from pathlib import Path
import os
import sys

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import sessionmaker


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BACKEND_DIR / "mindtrace.db"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models import Base, Habit, MoodCheckin, User  # noqa: E402


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def read_table(source_engine, table_name: str) -> list[dict]:
    inspector = inspect(source_engine)
    if table_name not in inspector.get_table_names():
        return []

    with source_engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(f"SELECT * FROM {table_name}")).mappings()]


def get_column_names(source_engine, table_name: str) -> set[str]:
    inspector = inspect(source_engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def parse_json_array(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []

    return parsed if isinstance(parsed, list) else []


def parse_datetime(value):
    if isinstance(value, datetime) or value is None:
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def copy_users(target_db, source_users: list[dict]) -> dict[int, int]:
    user_id_map = {}

    for source_user in source_users:
        existing_user = target_db.scalar(select(User).where(User.email == source_user["email"]))
        if existing_user is not None:
            user_id_map[source_user["id"]] = existing_user.id
            continue

        user = User(
            name=source_user["name"],
            email=source_user["email"],
            password_hash=source_user["password_hash"],
            created_at=parse_datetime(source_user["created_at"]),
        )
        target_db.add(user)
        target_db.flush()
        user_id_map[source_user["id"]] = user.id

    return user_id_map


def copy_mood_checkins(target_db, source_moods: list[dict], source_has_user_id: bool, user_id_map: dict[int, int], default_user_id: int | None) -> int:
    copied = 0

    for source_mood in source_moods:
        if target_db.get(MoodCheckin, source_mood["id"]) is not None:
            continue

        source_user_id = source_mood.get("user_id") if source_has_user_id else None
        target_user_id = user_id_map.get(source_user_id) if source_user_id is not None else default_user_id
        if target_user_id is None:
            continue

        target_db.add(
            MoodCheckin(
                id=source_mood["id"],
                user_id=target_user_id,
                mood_score=source_mood["mood_score"],
                factors=parse_json_array(source_mood["factors"]),
                note=source_mood["note"],
                created_at=parse_datetime(source_mood["created_at"]),
            )
        )
        copied += 1

    return copied


def copy_habits(target_db, source_habits: list[dict], source_has_user_id: bool, user_id_map: dict[int, int], default_user_id: int | None) -> int:
    copied = 0

    for source_habit in source_habits:
        if target_db.get(Habit, source_habit["id"]) is not None:
            continue

        source_user_id = source_habit.get("user_id") if source_has_user_id else None
        target_user_id = user_id_map.get(source_user_id) if source_user_id is not None else default_user_id
        if target_user_id is None:
            continue

        target_db.add(
            Habit(
                id=source_habit["id"],
                user_id=target_user_id,
                label=source_habit["label"],
                done=bool(source_habit["done"]),
                streak=source_habit["streak"],
                created_at=parse_datetime(source_habit["created_at"]),
                updated_at=parse_datetime(source_habit["updated_at"]),
            )
        )
        copied += 1

    return copied


def reset_postgres_sequences(target_db):
    for table_name in ("users", "mood_checkins", "habits"):
        target_db.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                    true
                )
                """
            )
        )


def main():
    sqlite_url = os.getenv("SQLITE_DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")
    target_url = os.getenv("DATABASE_URL")
    default_user_email = os.getenv("DEFAULT_USER_EMAIL")

    if not target_url:
        raise SystemExit("Set DATABASE_URL to your target SQL database before running this migration.")

    target_url = normalize_database_url(target_url)
    if target_url.startswith("sqlite"):
        raise SystemExit("DATABASE_URL must point to your target database, not SQLite.")

    source_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    target_engine = create_engine(target_url)
    TargetSession = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)

    Base.metadata.create_all(bind=target_engine)

    source_users = read_table(source_engine, "users")
    source_moods = read_table(source_engine, "mood_checkins")
    source_habits = read_table(source_engine, "habits")
    mood_has_user_id = "user_id" in get_column_names(source_engine, "mood_checkins")
    habit_has_user_id = "user_id" in get_column_names(source_engine, "habits")

    with TargetSession() as target_db:
        user_id_map = copy_users(target_db, source_users)
        default_user_id = None

        if default_user_email:
            default_user = target_db.scalar(select(User).where(User.email == default_user_email.strip().lower()))
            if default_user is None:
                raise SystemExit(f"DEFAULT_USER_EMAIL was set, but no target user exists for {default_user_email}.")
            default_user_id = default_user.id

        copied_moods = copy_mood_checkins(target_db, source_moods, mood_has_user_id, user_id_map, default_user_id)
        copied_habits = copy_habits(target_db, source_habits, habit_has_user_id, user_id_map, default_user_id)
        if target_engine.dialect.name == "postgresql":
            reset_postgres_sequences(target_db)
        target_db.commit()

    skipped_moods = len(source_moods) - copied_moods
    skipped_habits = len(source_habits) - copied_habits
    print(f"Copied {len(source_users)} users.")
    print(f"Copied {copied_moods} mood check-ins. Skipped {skipped_moods}.")
    print(f"Copied {copied_habits} habits. Skipped {skipped_habits}.")
    if skipped_moods or skipped_habits:
        print("Skipped rows were already present or had no user_id. Set DEFAULT_USER_EMAIL to attach old unowned rows.")


if __name__ == "__main__":
    main()
