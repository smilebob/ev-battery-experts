"""
Database models and security layer for Web & Admin Dashboard.
Stores users (with bcrypt salted hashes), application runtime configuration,
and custom vehicle catalog packs. Zero secrets stored in plaintext.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import bcrypt
import jwt
from sqlmodel import SQLModel, Field, create_engine, Session, select

DATA_DIR = Path(os.environ.get("SOH_DATA_DIR", Path.home() / ".config" / "ev-battery-soh" / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "app_soh.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Secret key for JWT signing - generated once per install or taken from env
JWT_SECRET_KEY = os.environ.get("SOH_JWT_SECRET", "soh_auto_generated_ephemeral_jwt_secret_998124_CHANGE_ME")
JWT_ALGORITHM = "HS256"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="auditor")  # admin, auditor, viewer
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = Field(default=True)


class AppConfig(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    min_delta_soc: float = Field(default=40.0)
    calibration_100_weight: float = Field(default=2.5)
    default_forecast_years: int = Field(default=3)
    knee_point_enabled: bool = Field(default=True)
    custom_signing_key_path: Optional[str] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


engine = create_engine(DATABASE_URL, echo=False)


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


def init_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # 1. Init default config if missing
        config = session.get(AppConfig, 1)
        if not config:
            config = AppConfig()
            session.add(config)
            session.commit()

        # 2. Init default admin user if none exists
        admin_user = session.exec(select(User).where(User.username == "admin")).first()
        if not admin_user:
            default_admin = User(
                username="admin",
                password_hash=hash_password("admin1234"),
                role="admin"
            )
            session.add(default_admin)
            session.commit()
            print("INFO: Default admin created (username: 'admin', password: 'admin1234'). Please update immediately in admin.")
