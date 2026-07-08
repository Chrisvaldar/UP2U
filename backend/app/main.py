from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import dev, photos, reveal, sessions
from app import ws

from app.limiter import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app = FastAPI(title="UP2U")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://up2u-app.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(reveal.router)
app.include_router(photos.router)
app.include_router(dev.router)
app.include_router(ws.router)
