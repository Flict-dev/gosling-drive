from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas.shares import ShareLinkCreate, ShareLinkRead
from app.application.services.audit import write_audit
from app.application.services.permissions import can_read_file
from app.domain.entities.enums import FileStatus
from app.infrastructure.database.models import FileModel, ShareLinkModel, UserModel
from app.infrastructure.database.session import get_db
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/shares", tags=["shares"])


@router.post(
    "",
    response_model=ShareLinkRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
@router.post("/", response_model=ShareLinkRead, status_code=status.HTTP_201_CREATED)
def create_share_link(
    payload: ShareLinkCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> ShareLinkModel:
    file = db.get(FileModel, payload.file_id)
    if (
        file is None
        or file.status != FileStatus.READY.value
        or not can_read_file(db, file, current_user)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    share_link = ShareLinkModel(
        file_id=file.id,
        owner_id=current_user.id,
        token=token_urlsafe(32),
        expires_at=payload.expires_at,
        max_downloads=payload.max_downloads,
    )
    db.add(share_link)
    db.flush()
    write_audit(
        db,
        user_id=current_user.id,
        action="share_create",
        resource_type="file",
        resource_id=file.id,
    )
    db.commit()
    db.refresh(share_link)
    return share_link


@router.get("", response_model=list[ShareLinkRead], include_in_schema=False)
@router.get("/", response_model=list[ShareLinkRead])
def list_share_links(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[ShareLinkModel]:
    return list(
        db.scalars(
            select(ShareLinkModel)
            .where(ShareLinkModel.owner_id == current_user.id)
            .order_by(ShareLinkModel.created_at.desc())
        )
    )


@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
def disable_share_link(
    share_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    share_link = db.get(ShareLinkModel, share_id)
    if share_link is None or share_link.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    share_link.is_active = False
    write_audit(
        db,
        user_id=current_user.id,
        action="share_disable",
        resource_type="share_link",
        resource_id=share_link.id,
    )
    db.commit()
