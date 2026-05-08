from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.schemas.files import StorageStats
from app.domain.entities.enums import FileStatus
from app.infrastructure.database.models import FileModel, UserModel
from app.infrastructure.database.session import get_db
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/stats", response_model=StorageStats)
def get_storage_stats(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> StorageStats:
    result = db.execute(
        select(func.count(FileModel.id), func.coalesce(func.sum(FileModel.size_bytes), 0)).where(
            FileModel.owner_id == current_user.id,
            FileModel.status == FileStatus.READY.value,
        )
    ).one()
    return StorageStats(files_count=result[0], total_size_bytes=result[1])
