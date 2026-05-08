from fastapi import APIRouter

from app.presentation.api.routers import access, audit, auth, files, folders, public, shares, storage, uploads

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(folders.router)
api_router.include_router(files.router)
api_router.include_router(uploads.router)
api_router.include_router(shares.router)
api_router.include_router(public.router)
api_router.include_router(access.router)
api_router.include_router(audit.router)
api_router.include_router(storage.router)
