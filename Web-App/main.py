from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os

from database import Base, engine
from users import router as users_router
from trips import router as trips_router
from messages import router as messages_router
from auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Создание таблиц при старте
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    yield
    # Очистка при завершении
    print("Application shutting down")

app = FastAPI(
    title="Travel Buddies API",
    description="API для поиска попутчиков и организации совместных путешествий",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(trips_router, prefix="/api/v1")
app.include_router(messages_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Travel Buddies API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "trips": "/api/v1/trips",
            "messages": "/api/v1/messages"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "travel-buddies-api"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV") == "development"
    )