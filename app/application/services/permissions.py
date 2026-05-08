from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.enums import AccessPermission
from app.infrastructure.database.models import AccessGrantModel, FileModel, UserModel


def can_read_file(db: Session, file: FileModel, user: UserModel) -> bool:
    if file.owner_id == user.id:
        return True
    grant = db.scalar(
        select(AccessGrantModel).where(
            AccessGrantModel.file_id == file.id,
            AccessGrantModel.grantee_id == user.id,
            AccessGrantModel.permission.in_(
                [AccessPermission.READ.value, AccessPermission.WRITE.value]
            ),
        )
    )
    return grant is not None


def can_write_file(db: Session, file: FileModel, user: UserModel) -> bool:
    if file.owner_id == user.id:
        return True
    grant = db.scalar(
        select(AccessGrantModel).where(
            AccessGrantModel.file_id == file.id,
            AccessGrantModel.grantee_id == user.id,
            AccessGrantModel.permission == AccessPermission.WRITE.value,
        )
    )
    return grant is not None

