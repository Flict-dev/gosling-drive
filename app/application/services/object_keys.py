from pathlib import PurePath
from uuid import uuid4


def build_object_key(user_id: str, filename: str) -> str:
    safe_name = PurePath(filename).name.replace("/", "_").replace("\\", "_")
    return f"users/{user_id}/{uuid4()}/{safe_name}"

