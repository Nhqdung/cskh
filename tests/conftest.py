"""
Pytest configuration and fixtures.
Provides an isolated in-memory SQLite database and test environment.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.orm import Base, WorkShift, Setting
from database.connection import DatabaseManager, db_manager


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Sets environment variables for testing."""
    os.environ["APP_ENV"] = "test"
    os.environ["APP_TIMEZONE"] = "Asia/Ho_Chi_Minh"
    os.environ["EMPLOYEE_NAME"] = "Nguyễn Văn Test"
    os.environ["DISCORD_USER_ID"] = "1122334455"
    os.environ["META_PAGE_ID"] = "9988776655"


@pytest.fixture
def test_db():
    """Creates a fresh in-memory SQLite database for each test function."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(bind=engine)

    # Seed default shifts
    with Session() as session:
        session.add_all([
            WorkShift(shift_num=1, name="Ca 1", start_time="07:00", end_time="15:00", crosses_midnight=False),
            WorkShift(shift_num=2, name="Ca 2", start_time="15:00", end_time="23:00", crosses_midnight=False),
            WorkShift(shift_num=3, name="Ca 3", start_time="23:00", end_time="07:00", crosses_midnight=True),
            Setting(key="APP_TIMEZONE", value="Asia/Ho_Chi_Minh"),
            Setting(key="EMPLOYEE_NAME", value="Nguyễn Văn Test"),
        ])
        session.commit()

    # Point global db_manager to this in-memory test engine
    orig_engine = db_manager.engine
    orig_session = db_manager.SessionLocal
    db_manager.engine = engine
    db_manager.SessionLocal = Session

    yield db_manager

    # Teardown
    db_manager.engine = orig_engine
    db_manager.SessionLocal = orig_session
