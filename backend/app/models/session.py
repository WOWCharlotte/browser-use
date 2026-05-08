from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from app.utils import uuid7str


class Session(BaseModel):
	id: str = Field(default_factory=uuid7str)
	title: str
	created_at: datetime = Field(default_factory=datetime.now)
	updated_at: datetime = Field(default_factory=datetime.now)
	model_config = ConfigDict(extra="forbid", validate_by_name=True)