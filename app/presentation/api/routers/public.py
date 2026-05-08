from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.schemas.files import FileDownloadUrl
from app.application.services.audit import write_audit
from app.core.config import settings
from app.domain.entities.enums import FileStatus
from app.infrastructure.database.models import FileModel, ShareLinkModel
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3 import storage

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/{token}", response_model=FileDownloadUrl)
def public_download(token: str, db: Session = Depends(get_db)) -> FileDownloadUrl:
    share_link = db.query(ShareLinkModel).filter(ShareLinkModel.token == token).one_or_none()
    if share_link is None or not share_link.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    now = datetime.now(timezone.utc)
    expires_at = share_link.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is not None and expires_at < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
    if (
        share_link.max_downloads is not None
        and share_link.download_count >= share_link.max_downloads
    ):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Download limit reached")

    file = db.get(FileModel, share_link.file_id)
    if file is None or file.status != FileStatus.READY.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    share_link.download_count += 1
    write_audit(
        db,
        user_id=None,
        action="public_download_url",
        resource_type="file",
        resource_id=file.id,
        metadata={"share_link_id": share_link.id},
    )
    db.commit()
    return FileDownloadUrl(
        url=storage.presign_download(file.object_key, file.name),
        expires_in_seconds=settings.s3_presigned_expire_seconds,
    )

