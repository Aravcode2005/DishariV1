from datetime import datetime
from typing import Literal
from uuid import UUID

from app.schemas.common import Schema


class DocumentResponse(Schema):
    id: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    status: Literal["stored"] = "stored"
    synthetic: Literal[True] = True
