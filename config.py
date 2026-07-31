"""
Application configuration.
Reads all sensitive/environment-specific values from environment variables (.env)
so the same codebase runs unmodified locally (SQLite) and on Railway (PostgreSQL).
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _database_url() -> str:
    """Normalize DATABASE_URL. Railway/Heroku-style postgres:// -> postgresql://"""
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{os.path.join(BASE_DIR, 'clientflow.db')}"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 25)) * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "zip", "rar", "png", "jpg", "jpeg", "xlsx", "xls"}

    # Sessions
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Mail (ready for future SMTP wiring)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@clientflow.local")

    # Admin bootstrap account
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "administrator")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "3000330210")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@clientflow.local")

    # Company info
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "System Makers")
    PROJECT_MANAGER_NAME = os.environ.get("PROJECT_MANAGER_NAME", "Mohamed Naser")
    PROJECT_MANAGER_EMAIL = os.environ.get("PROJECT_MANAGER_EMAIL", "contact@clientflow.local")
    PROJECT_MANAGER_PHONE = os.environ.get("PROJECT_MANAGER_PHONE", "+20 100 000 0000")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
