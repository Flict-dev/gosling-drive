from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.schemas.folders import FolderCreate, FolderRead, FolderUpdate
from app.application.services.audit import write_audit
from app.infrastructure.database.models import FolderModel, UserModel
from app.infrastructure.database.session import get_db
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("/", response_model=list[FolderRead])
def list_folders(
    parent_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[FolderModel]:
    return list(
        db.scalars(
            select(FolderModel)
            .where(FolderModel.owner_id == current_user.id, FolderModel.parent_id == parent_id)
            .order_by(FolderModel.name)
        )
    )


@router.post("/", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FolderModel:
    if payload.parent_id:
        ensure_owned_folder(db, payload.parent_id, current_user.id)

    folder = FolderModel(owner_id=current_user.id, parent_id=payload.parent_id, name=payload.name)
    db.add(folder)
    try:
        db.flush()
        write_audit(
            db,
            user_id=current_user.id,
            action="folder_create",
            resource_type="folder",
            resource_id=folder.id,
            metadata={"name": folder.name},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder with this name already exists in the selected parent folder",
        ) from exc
    db.refresh(folder)
    return folder


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FolderModel:
    return ensure_owned_folder(db, folder_id, current_user.id)


@router.patch("/{folder_id}", response_model=FolderRead)
def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> FolderModel:
    folder = ensure_owned_folder(db, folder_id, current_user.id)
    if payload.parent_id:
        ensure_owned_folder(db, payload.parent_id, current_user.id)
    if payload.name is not None:
        folder.name = payload.name
    if payload.parent_id is not None:
        folder.parent_id = payload.parent_id

    write_audit(
        db,
        user_id=current_user.id,
        action="folder_update",
        resource_type="folder",
        resource_id=folder.id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Folder name conflict") from exc
    db.refresh(folder)
    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    folder = ensure_owned_folder(db, folder_id, current_user.id)
    db.delete(folder)
    write_audit(
        db,
        user_id=current_user.id,
        action="folder_delete",
        resource_type="folder",
        resource_id=folder.id,
    )
    db.commit()


def ensure_owned_folder(db: Session, folder_id: str, owner_id: str) -> FolderModel:
    folder = db.get(FolderModel, folder_id)
    if folder is None or folder.owner_id != owner_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder
