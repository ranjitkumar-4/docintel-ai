import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    LLM_PROVIDER: str = "local"  # "local", "openai", "gemini"
    EMBEDDING_PROVIDER: str = "local"
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "chroma_db")
    UPLOAD_DIR: str = str(BASE_DIR / "documents")
    DATA_DIR: str = str(BASE_DIR / "data")
    
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100
    EMBEDDING_MODEL: str = "local-hash-v1"
    
    SIMILARITY_THRESHOLD: float = 0.25
    TOP_K_RESULTS: int = 6
    
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    APP_ENV: str = "development"
    ALLOW_DESTRUCTIVE_RESET: bool = False

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Relative storage paths are anchored to the project configuration, not the
# process working directory, so CLI, tests, and service startup use one index.
for storage_setting in ("CHROMA_PERSIST_DIR", "UPLOAD_DIR", "DATA_DIR"):
    storage_path = Path(getattr(settings, storage_setting)).expanduser()
    if not storage_path.is_absolute():
        storage_path = BASE_DIR / storage_path
    setattr(settings, storage_setting, str(storage_path.resolve()))

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
