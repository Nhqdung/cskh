"""
Database connection manager and session factory using SQLAlchemy 2.0.
Supports both file-based SQLite and in-memory SQLite (for tests).
"""

import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from models.orm import Base, WorkShift, Setting

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_DB_FILE = DEFAULT_DATA_DIR / "cskh_assistant.db"


class DatabaseManager:
    """Manages SQLite engine and database sessions."""

    def __init__(self, db_url: str | None = None):
        if db_url is None:
            DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.db_url = f"sqlite:///{DEFAULT_DB_FILE}"
        else:
            self.db_url = db_url

        self.engine = create_engine(
            self.db_url,
            connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in self.db_url else {},
            echo=False,
            future=True,
        )
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            future=True,
        )

    def init_db(self) -> None:
        """Create all tables and seed default work shifts and core settings if missing."""
        Base.metadata.create_all(bind=self.engine)
        self.seed_defaults()

    def seed_defaults(self) -> None:
        """Seed default shifts (Ca 1, Ca 2, Ca 3) and default settings."""
        with self.get_session() as session:
            # 1. Default Shifts
            shifts_to_seed = [
                {"shift_num": 1, "name": "Ca 1", "start_time": "07:00", "end_time": "15:00", "crosses_midnight": False},
                {"shift_num": 2, "name": "Ca 2", "start_time": "15:00", "end_time": "23:00", "crosses_midnight": False},
                {"shift_num": 3, "name": "Ca 3", "start_time": "23:00", "end_time": "07:00", "crosses_midnight": True},
            ]
            for s in shifts_to_seed:
                existing = session.execute(
                    select(WorkShift).where(WorkShift.shift_num == s["shift_num"])
                ).scalar_one_or_none()
                if not existing:
                    session.add(WorkShift(**s))

            # 2. Default Core Settings
            default_settings = [
                ("APP_TIMEZONE", "Asia/Ho_Chi_Minh", "Application display timezone"),
                ("DATA_RETENTION_DAYS", "60", "Days before old messages are purged"),
                ("GEMINI_MODEL_NAME", "gemini-2.5-flash", "Gemini model identifier"),
                ("EMPLOYEE_NAME", "CSKH Member", "Employee name on reports"),
            ]
            for key, val, desc in default_settings:
                existing_setting = session.execute(
                    select(Setting).where(Setting.key == key)
                ).scalar_one_or_none()
                if not existing_setting:
                    session.add(Setting(key=key, value=val, description=desc))

            session.commit()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# Global default instance
db_manager = DatabaseManager()
