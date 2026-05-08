from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.infrastructure.storage.s3 import storage
from app.presentation.api.routers import api_router
from app.presentation.web.router import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.ensure_bucket()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="app/presentation/web/static"), name="static")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

