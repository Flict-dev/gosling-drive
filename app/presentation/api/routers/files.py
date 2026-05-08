from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.application.schemas.files import (
    FileDownloadUrl,
    FileRead,
    FileUpdate,
    FileVersionRead,
    StorageStats,
)
from app.application.schemas.uploads import (
    UploadInitiateRequest,
    UploadInitiateResponse,
    UploadVersionInitiateRequest,
)
from app.application.services.audit import write_audit
from app.application.services.permissions import can_read_file, can_write_file
from app.core.config import settings
from app.domain.entities.enums import FileStatus
from app.infrastructure.database.models import (
    AccessGrantModel,
    FileModel,
    FileVersionModel,
    FolderModel,
    UserModel,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3 import storage
from app.presentation.api.dependencies import get_current_user
from app.presentation.api.routers.uploads import initiate_upload, initiate_version_upload

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/", response_model=list[FileRead])
def list_files(
    folder_id: str | None = None,
    include_shared: bool = True,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[FileModel]:
    shared_file_ids = select(AccessGrantModel.file_id).where(
        AccessGrantModel.grantee_id == current_user.id
    )
    ownership_filter = FileModel.owner_id == current_user.id
    if include_shared:
        ownership_filter = or_(ownership_filter, FileModel.id.in_(shared_file_ids))
    query = (
        select(FileModel)
        .where(
            ownership_filter,
            FileModel.status != FileStatus.DELETED.value,
            FileModel.folder_id == folder_id,
        )
        .order_by(FileModel.created_at.desc())
    )
    return list(db.scalars(query))


@router.post("/uploads", response_model=UploadInitiateResponse, status_code=status.HTTP_201_CREATED)
def initiate_file_upload(
    payload: UploadInitiateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadInitiateResponse:
    return initiate_upload(payload, db, current_user)


@router.get("/{file_id}", response_model=FileRead)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FileModel:
    file = ensure_readable_file(db, file_id, current_user)
    if file.status == FileStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


@router.patch("/{file_id}", response_model=FileRead)
def update_file(
    file_id: str,
    payload: FileUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FileModel:
    file = ensure_writable_file(db, file_id, current_user)
    if payload.name:
        file.name = payload.name
    if payload.folder_id is not None:
        folder = db.get(FolderModel, payload.folder_id)
        if folder is None or folder.owner_id != file.owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        file.folder_id = payload.folder_id
    write_audit(
        db,
        user_id=current_user.id,
        action="file_update",
        resource_type="file",
        resource_id=file.id,
    )
    db.commit()
    db.refresh(file)
    return file


@router.get("/{file_id}/download-url", response_model=FileDownloadUrl)
def get_download_url(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FileDownloadUrl:
    file = ensure_readable_file(db, file_id, current_user)
    ensure_file_ready(file)
    write_audit(
        db,
        user_id=current_user.id,
        action="file_download_url",
        resource_type="file",
        resource_id=file.id,
    )
    db.commit()
    return FileDownloadUrl(
        url=storage.presign_download(file.object_key, file.name),
        expires_in_seconds=settings.s3_presigned_expire_seconds,
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    file = ensure_writable_file(db, file_id, current_user)
    if file.status == FileStatus.READY.value:
        storage.delete_object(file.object_key)
    file.status = FileStatus.DELETED.value
    write_audit(
        db,
        user_id=current_user.id,
        action="file_delete",
        resource_type="file",
        resource_id=file.id,
    )
    db.commit()


@router.post(
    "/{file_id}/versions/uploads",
    response_model=UploadInitiateResponse,
    status_code=status.HTTP_201_CREATED,
)
def initiate_file_version_upload(
    file_id: str,
    payload: UploadVersionInitiateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadInitiateResponse:
    file = ensure_writable_file(db, file_id, current_user)
    return initiate_version_upload(file, payload, db, current_user)


@router.get("/{file_id}/versions", response_model=list[FileVersionRead])
def list_versions(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[FileVersionModel]:
    file = ensure_readable_file(db, file_id, current_user)
    return sorted(file.versions, key=lambda version: version.version_number)


@router.get("/stats/me", response_model=StorageStats)
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


def ensure_readable_file(db: Session, file_id: str, user: UserModel) -> FileModel:
    file = db.get(FileModel, file_id)
    if file is None or not can_read_file(db, file, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


def ensure_writable_file(db: Session, file_id: str, user: UserModel) -> FileModel:
    file = db.get(FileModel, file_id)
    if file is None or not can_write_file(db, file, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file


def ensure_file_ready(file: FileModel) -> None:
    if file.status != FileStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File is not ready")
