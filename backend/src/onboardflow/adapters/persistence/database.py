from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import DateTime, JSON, String

from onboardflow.config.settings import get_settings
from onboardflow.domain.models import utc_now


class Base(DeclarativeBase):
    pass


class OnboardingRunRecord(Base):
    __tablename__ = "onboarding_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    input_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_result: Mapped[dict | None] = mapped_column(JSON)
    result: Mapped[dict | None] = mapped_column(JSON)
    markdown: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(String)
    action_history: Mapped[list] = mapped_column(JSON, nullable=False)
    dispatch_receipts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    revision_number: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def touch_record(record: OnboardingRunRecord) -> None:
    record.updated_at = utc_now()
