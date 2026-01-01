"""環境設定"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./simple_rag.db")
    
    # Qdrant
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", 6333))
    
    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma2:9b")
    
    # LLM
    llm_type: str = os.getenv("LLM_TYPE", "mock")
    
    # App
    debug: bool = os.getenv("DEBUG", "1") == "1"
    upload_dir: str = os.getenv("UPLOAD_DIR", "./.tmp/uploads")


settings = Settings()