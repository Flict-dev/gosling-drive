from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.entities.enums import AccessPermission, FileStatus, UploadStatus, UserRole
from app.infrastructure.database.base import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    folders: Mapped[list["FolderModel"]] = relationship(back_populates="owner")
    files: Mapped[list["FileModel"]] = relationship(back_populates="owner")


class FolderModel(Base):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint("owner_id", "parent_id", "name", name="uq_folders_owner_parent_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    parent_id: Mapped[str] = mapped_column(ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner: Mapped[UserModel] = relationship(back_populates="folders")
    parent: Mapped["FolderModel"] = relationship(remote_side=[id])
    files: Mapped[list["FileModel"]] = relationship(back_populates="folder")


class FileModel(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("owner_id", "folder_id", "name", name="uq_files_owner_folder_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    folder_id: Mapped[str] = mapped_column(ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=FileStatus.UPLOADING.value, index=True)
    current_version_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    owner: Mapped[UserModel] = relationship(back_populates="files")
    folder: Mapped[FolderModel] = relationship(back_populates="files")
    versions: Mapped[list["FileVersionModel"]] = relationship(back_populates="file")


class FileVersionModel(Base):
    __tablename__ = "file_versions"
    __table_args__ = (
        UniqueConstraint("file_id", "version_number", name="uq_file_versions_file_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=True)
    etag: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    file: Mapped[FileModel] = relationship(back_populates="versions")


class UploadSessionModel(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    provider_upload_id: Mapped[str] = mapped_column(String(255), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    part_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=UploadStatus.ACTIVE.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class ShareLinkModel(Base):
    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    max_downloads: Mapped[int] = mapped_column(Integer, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AccessGrantModel(Base):
    __tablename__ = "access_grants"
    __table_args__ = (
        UniqueConstraint("file_id", "grantee_id", name="uq_access_grants_file_grantee"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(ForeignKey("files.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    grantee_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    permission: Mapped[str] = mapped_column(String(32), default=AccessPermission.READ.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
