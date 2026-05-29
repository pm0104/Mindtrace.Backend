from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .database import Base, engine, ensure_user_scoped_columns
    from .routes.auth import router as auth_router
    from .routes.habits import router as habits_router
    from .routes.mood import router as mood_router
    from .routes.predict import router as predict_router
except ImportError:
    from database import Base, engine, ensure_user_scoped_columns
    from routes.auth import router as auth_router
    from routes.habits import router as habits_router
    from routes.mood import router as mood_router
    from routes.predict import router as predict_router

app = FastAPI(
    title="MindTrace API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
ensure_user_scoped_columns()

app.include_router(auth_router)
app.include_router(mood_router)
app.include_router(habits_router)
app.include_router(predict_router)


@app.get("/")
def read_root():
    return {"message": "MindTrace API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
