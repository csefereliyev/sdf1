import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE = os.environ.get("DATABASE", str(BASE_DIR / "instance" / "events.db"))
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@university.az")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
