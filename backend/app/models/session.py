from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.utils import uuid7str


class Session(BaseModel):
	id: str = Field(default_factory=uuid7str)
	title: str
	created_at: datetime = Field(default_factory=datetime.now)
	updated_at: datetime = Field(default_factory=datetime.now)
	model_config = ConfigDict(extra="forbid", validate_by_name=True)