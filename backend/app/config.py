import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent.parent / ".env")


class Config:
	PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
	DATABASE_PATH: Path = PROJECT_ROOT / "data" / "ai_workspace.db"
	CDP_PORT: int = int(os.getenv("CDP_PORT", "9222"))
	LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
	LLM_BASE_URL: str = os.getenv(
		"LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
	)
	LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-vl-max")
	TRAJECTORY_DIR: Path = PROJECT_ROOT / "data" / "trajectories"
	MAX_CONCURRENCY: int = int(os.getenv("MAX_CONCURRENCY", "5"))
	CASE_TIMEOUT_SECONDS: int = int(os.getenv("CASE_TIMEOUT_SECONDS", "600"))
	TRAJECTORY_RETENTION_DAYS: int = 30