"""SQLAlchemy models. Every business-data table carries workspace_id (PRD §2)."""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class MessageStatus(str, enum.Enum):
    sent = "sent"
    delivered = "delivered"
    read = "read"
    failed = "failed"
    replied = "replied"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    sending = "sending"
    sent = "sent"
    failed = "failed"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Informational: the WhatsApp number on Meta (kept per PRD schema).
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(64))
    # Per-workspace AiSensy API key; overrides the global env key so each
    # client's AiSensy project stays isolated. Secret — never returned in API
    # responses (WorkspaceOut exposes only aisensy_configured).
    aisensy_api_key: Mapped[str | None] = mapped_column(String(512))
    lapsed_threshold_days: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    avg_ticket: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list[User]] = relationship(back_populates="workspace")
    contacts: Mapped[list[Contact]] = relationship(back_populates="workspace")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable → agency admin with cross-workspace access (PRD §2).
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("workspaces.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.staff, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace | None] = relationship(back_populates="users")

    @property
    def is_agency_admin(self) -> bool:
        """Agency admin = admin role with no workspace binding (sees all)."""
        return self.role == Role.admin and self.workspace_id is None


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "phone", name="uq_contact_workspace_phone"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32), nullable=False)  # E.164
    last_visit_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="contacts")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_offer: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus), default=CampaignStatus.draft, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list[Message]] = relationship(back_populates="campaign")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False, index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus), default=MessageStatus.sent, nullable=False)
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    error_detail: Mapped[str | None] = mapped_column(Text)  # loud failures (PRD §10)
    booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # manual admin toggle
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="messages")
    contact: Mapped[Contact] = relationship()
    replies: Mapped[list[Reply]] = relationship(back_populates="message")


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), index=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), nullable=False, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    body: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    message: Mapped[Message | None] = relationship(back_populates="replies")
