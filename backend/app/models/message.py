from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Literal
from app.utils import uuid7str


class Attachment(BaseModel):
	name: str
	type: str
	data: Optional[str] = None


class Message(BaseModel):
	id: str = Field(default_factory=uuid7str)
	session_id: str
	role: Literal["user", "ai"]
	content: str
	attachments: list[Attachment] = []
	created_at: datetime = Field(default_factory=datetime.now)
	model_config = ConfigDict(extra="forbid", validate_by_name=True)