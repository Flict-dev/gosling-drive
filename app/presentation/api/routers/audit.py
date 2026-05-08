from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas.audit import AuditLogRead
from app.infrastructure.database.models import AuditLogModel, UserModel
from app.infrastructure.database.session import get_db
from app.presentation.api.dependencies import get_current_user, require_admin

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/me", response_model=list[AuditLogRead])
def my_audit_log(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[AuditLogModel]:
    return list(
        db.scalars(
            select(AuditLogModel)
            .where(AuditLogModel.user_id == current_user.id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(100)
        )
    )


@router.get("/", response_model=list[AuditLogRead])
def all_audit_logs(
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_admin),
) -> list[AuditLogModel]:
    return list(
        db.scalars(select(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(200))
    )

