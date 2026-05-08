from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class FileStatus(StrEnum):
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class UploadStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class AccessPermission(StrEnum):
    READ = "read"
    WRITE = "write"

