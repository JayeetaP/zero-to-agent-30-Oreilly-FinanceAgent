import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

FRONTEND_DIR = ROOT / "frontend"
FIXTURE_FILE = ROOT / "data" / "news_fixture.json"
MEMORY_FILE = ROOT / "data" / "memory.local.json"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:9b")
APP_HOST = os.getenv("BRIEFING_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("BRIEFING_PORT", "8000"))

