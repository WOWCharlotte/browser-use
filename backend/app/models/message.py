from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils import uuid7str


class Attachment(BaseModel):
	name: str
	type: str
	data: Optional[str] = None


class Message(BaseModel):
	id: str = Field(default_factory=uuid7str)
	session_id: str
	role: str
	content: str
	attachments: list[Attachment] = []
	created_at: datetime = Field(default_factory=datetime.now)
	model_config = ConfigDict(extra="forbid", validate_by_name=True)