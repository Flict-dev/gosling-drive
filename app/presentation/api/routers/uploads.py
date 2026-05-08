from datetime import timedelta
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas.files import FileRead
from app.application.schemas.uploads import (
    UploadCompleteRequest,
    UploadInitiateRequest,
    UploadInitiateResponse,
    UploadPartUrl,
    UploadPartUrlRequest,
    UploadPartUrlResponse,
    UploadSessionRead,
)
from app.application.services.audit import write_audit
from app.application.services.object_keys import build_object_key
from app.core.config import settings
from app.domain.entities.enums import FileStatus, UploadStatus
from app.infrastructure.database.models import (
    FileModel,
    FileVersionModel,
    FolderModel,
    UploadSessionModel,
    UserModel,
    utcnow,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3 import storage
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/initiate", response_model=UploadInitiateResponse, status_code=status.HTTP_201_CREATED)
def initiate_upload(
    payload: UploadInitiateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadInitiateResponse:
    if payload.size_bytes > settings.max_upload_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too big")
    if payload.folder_id:
        folder = db.get(FolderModel, payload.folder_id)
        if folder is None or folder.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    existing_file = db.scalar(
        select(FileModel).where(
            FileModel.owner_id == current_user.id,
            FileModel.folder_id == payload.folder_id,
            FileModel.name == payload.filename,
            FileModel.status != FileStatus.DELETED.value,
        )
    )
    if existing_file is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="File with this name already exists in the selected folder",
        )

    object_key = build_object_key(current_user.id, payload.filename)
    provider_upload_id = storage.create_multipart_upload(object_key, payload.content_type)
    total_parts = math.ceil(payload.size_bytes / settings.upload_part_size)

    file = FileModel(
        owner_id=current_user.id,
        folder_id=payload.folder_id,
        name=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        checksum_sha256=payload.checksum_sha256,
        bucket=settings.s3_bucket_name,
        object_key=object_key,
        status=FileStatus.UPLOADING.value,
    )
    db.add(file)
    db.flush()

    upload_session = UploadSessionModel(
        file_id=file.id,
        owner_id=current_user.id,
        provider_upload_id=provider_upload_id,
        bucket=settings.s3_bucket_name,
        object_key=object_key,
        part_size=settings.upload_part_size,
        total_parts=total_parts,
        status=UploadStatus.ACTIVE.value,
        expires_at=utcnow() + timedelta(hours=24),
    )
    db.add(upload_session)
    write_audit(
        db,
        user_id=current_user.id,
        action="upload_initiate",
        resource_type="file",
        resource_id=file.id,
        metadata={"filename": payload.filename, "size_bytes": payload.size_bytes},
    )
    db.commit()

    return UploadInitiateResponse(
        upload_session_id=upload_session.id,
        file_id=file.id,
        provider_upload_id=provider_upload_id,
        bucket=settings.s3_bucket_name,
        object_key=object_key,
        part_size=settings.upload_part_size,
        total_parts=total_parts,
    )


@router.post("/{upload_session_id}/parts", response_model=UploadPartUrlResponse)
def create_part_urls(
    upload_session_id: str,
    payload: UploadPartUrlRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadPartUrlResponse:
    upload_session = ensure_active_upload(db, upload_session_id, current_user.id)
    urls = []
    for part_number in payload.part_numbers:
        if part_number < 1 or part_number > upload_session.total_parts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Part number {part_number} is outside upload range",
            )
        urls.append(
            UploadPartUrl(
                part_number=part_number,
                url=storage.presign_upload_part(
                    upload_session.object_key,
                    upload_session.provider_upload_id,
                    part_number,
                ),
            )
        )
    return UploadPartUrlResponse(upload_session_id=upload_session.id, urls=urls)


@router.post("/{upload_session_id}/complete", response_model=FileRead)
def complete_upload(
    upload_session_id: str,
    payload: UploadCompleteRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FileModel:
    upload_session = ensure_active_upload(db, upload_session_id, current_user.id)
    file = db.get(FileModel, upload_session.file_id)
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    etag = storage.complete_multipart_upload(
        upload_session.object_key,
        upload_session.provider_upload_id,
        [part.model_dump() for part in payload.parts],
    )
    upload_session.status = UploadStatus.COMPLETED.value
    upload_session.completed_at = utcnow()
    file.status = FileStatus.READY.value
    file.current_version_number = 1

    db.add(
        FileVersionModel(
            file_id=file.id,
            version_number=1,
            bucket=file.bucket,
            object_key=file.object_key,
            size_bytes=file.size_bytes,
            checksum_sha256=file.checksum_sha256,
            etag=etag,
        )
    )
    write_audit(
        db,
        user_id=current_user.id,
        action="upload_complete",
        resource_type="file",
        resource_id=file.id,
        metadata={"parts": len(payload.parts), "etag": etag},
    )
    db.commit()
    db.refresh(file)
    return file


@router.post("/{upload_session_id}/abort", response_model=UploadSessionRead)
def abort_upload(
    upload_session_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadSessionModel:
    upload_session = ensure_active_upload(db, upload_session_id, current_user.id)
    storage.abort_multipart_upload(upload_session.object_key, upload_session.provider_upload_id)
    upload_session.status = UploadStatus.ABORTED.value
    file = db.get(FileModel, upload_session.file_id)
    if file is not None:
        file.status = FileStatus.FAILED.value
    write_audit(
        db,
        user_id=current_user.id,
        action="upload_abort",
        resource_type="file",
        resource_id=upload_session.file_id,
    )
    db.commit()
    db.refresh(upload_session)
    return upload_session


@router.get("/{upload_session_id}", response_model=UploadSessionRead)
def get_upload_status(
    upload_session_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> UploadSessionModel:
    upload_session = db.get(UploadSessionModel, upload_session_id)
    if upload_session is None or upload_session.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    return upload_session


def ensure_active_upload(db: Session, upload_session_id: str, owner_id: str) -> UploadSessionModel:
    upload_session = db.get(UploadSessionModel, upload_session_id)
    if upload_session is None or upload_session.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload session not found")
    if upload_session.status != UploadStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload session is not active")
    return upload_session
