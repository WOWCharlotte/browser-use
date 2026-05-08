import os
from pathlib import Path


class Config:
	PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
	DATABASE_PATH: Path = PROJECT_ROOT / "data" / "ai_workspace.db"
	CDP_PORT: int = int(os.getenv("CDP_PORT", "9222"))
	LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
	LLM_BASE_URL: str = os.getenv(
		"LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
	)
	LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-vl-max")