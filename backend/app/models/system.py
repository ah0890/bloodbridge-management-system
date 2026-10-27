from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime
from app.models.enums import NotificationKind, Provenance, str_enum


class Notification(Base):
    """In-app notification for one user. No external delivery is performed."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "read_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[NotificationKind] = mapped_column(str_enum(NotificationKind, "notification_kind"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class DatasetImport(Base):
    """Record of an authorised data import, including source and licence metadata."""

    __tablename__ = "dataset_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # blood_banks | inventory | donors
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_license: Mapped[str] = mapped_column(String(200), nullable=False)
    provenance: Mapped[Provenance] = mapped_column(str_enum(Provenance, "provenance"), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    imported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    dry_run: Mapped[bool] = mapped_column(default=False, nullable=False)
    rows_total: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_accepted: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_rejected: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class AppSetting(Base):
    """Admin-editable operational settings that override environment defaults."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | int | float | str | bool] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
