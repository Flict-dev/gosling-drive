from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.schemas.access import AccessGrantCreate, AccessGrantRead
from app.application.services.audit import write_audit
from app.domain.entities.enums import AccessPermission
from app.infrastructure.database.models import AccessGrantModel, FileModel, UserModel
from app.infrastructure.database.session import get_db
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/access", tags=["access"])


@router.post("/", response_model=AccessGrantRead, status_code=status.HTTP_201_CREATED)
def grant_access(
    payload: AccessGrantCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> AccessGrantModel:
    if payload.permission not in {AccessPermission.READ.value, AccessPermission.WRITE.value}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid permission")

    file = db.get(FileModel, payload.file_id)
    if file is None or file.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    grantee = db.scalar(select(UserModel).where(UserModel.email == payload.grantee_email.lower()))
    if grantee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grantee not found")
    if grantee.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot grant access to yourself")

    grant = AccessGrantModel(
        file_id=file.id,
        owner_id=current_user.id,
        grantee_id=grantee.id,
        permission=payload.permission,
    )
    db.add(grant)
    try:
        db.flush()
        write_audit(
            db,
            user_id=current_user.id,
            action="access_grant",
            resource_type="file",
            resource_id=file.id,
            metadata={"grantee_id": grantee.id, "permission": payload.permission},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Access already granted") from exc
    db.refresh(grant)
    return grant


@router.delete("/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_access(
    grant_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    grant = db.get(AccessGrantModel, grant_id)
    if grant is None or grant.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access grant not found")
    db.delete(grant)
    write_audit(
        db,
        user_id=current_user.id,
        action="access_revoke",
        resource_type="file",
        resource_id=grant.file_id,
        metadata={"grantee_id": grant.grantee_id},
    )
    db.commit()
