from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.applications.create_revision_config.router import router as revision_router
from app.applications.procman_utilities.router import router as procman_router

app = FastAPI(title=settings.APP_NAME, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_ORIGIN,
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(revision_router, prefix=f"{settings.API_V1_PREFIX}/revision-config")
app.include_router(procman_router, prefix=f"{settings.API_V1_PREFIX}/procman")


@app.get("/health")
async def health():
    return {"status": "ok", "application": settings.APP_NAME}
