"""Application settings and configuration."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

AGENT_NAME = os.getenv("AGENT_NAME", "CivicBridge Navigator")
AGENT_SEED_PHRASE = os.getenv("AGENT_SEED_PHRASE", "civicbridge-navigator-seed-2026")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
AGENT_MAILBOX_KEY = os.getenv("AGENT_MAILBOX_KEY", "").strip()

DATABASE_PATH = os.getenv("DATABASE_PATH", str(ROOT_DIR / "database" / "civicbridge.db"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
