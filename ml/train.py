from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "training_data.csv"
MODEL_DIR = BASE_DIR / "models"

df = pd.read_csv(DATA_PATH)

FEATURES = [
    "mood_score",
    "note_length",
    "has_note",
    "factor_count",
    "poor_sleep",
    "work_stress",
    "exercise_factor",
    "social_media_factor",
    "good_food",
    "socializing",
    "loneliness",
    "achievement",
    "active_habit_count",
    "completed_habits",
    "completion_rate",
    "longest_streak",
]

TARGETS = ["burnout_risk", "anxiety", "focus_score"]

X = df[FEATURES]
MODEL_DIR.mkdir(parents=True, exist_ok=True)

for target in TARGETS:
    print(f"\nTraining model for: {target}")

    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"MAE: {mae:.2f}")
    print(f"R²: {r2:.3f}")

    model_path = MODEL_DIR / f"{target}_model.pkl"
    joblib.dump(model, model_path)
    print(f"Saved -> {model_path}")

print("\nAll models trained and saved!")
