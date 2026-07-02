"""Pydantic request/response models."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import CampaignStatus, MessageStatus, Role


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserOut(ORM):
    id: int
    email: str
    role: Role
    workspace_id: int | None


# --- Workspaces ---
class WorkspaceCreate(BaseModel):
    name: str
    whatsapp_phone_number_id: str | None = None
    aisensy_api_key: str | None = None  # write-only; never echoed back
    lapsed_threshold_days: int = 45
    avg_ticket: float = 0.0


class WorkspaceOut(ORM):
    id: int
    name: str
    whatsapp_phone_number_id: str | None
    lapsed_threshold_days: int
    avg_ticket: float
    created_at: datetime
    # Derived flag so the UI knows sending is wired up without leaking the key.
    aisensy_configured: bool = False

    @classmethod
    def from_workspace(cls, ws, *, env_key_present: bool) -> "WorkspaceOut":
        data = cls.model_validate(ws)
        data.aisensy_configured = bool(ws.aisensy_api_key) or env_key_present
        return data


# --- Contacts ---
class ContactOut(ORM):
    id: int
    name: str | None
    phone: str
    last_visit_date: date | None
    created_at: datetime


class LapsedContactOut(ContactOut):
    days_since_visit: int | None


class UploadSummary(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: list[str]


# --- Campaigns ---
class CampaignCreate(BaseModel):
    template_name: str
    discount_offer: str | None = None


class CampaignOut(ORM):
    id: int
    template_name: str
    discount_offer: str | None
    status: CampaignStatus
    created_at: datetime


class MessageOut(ORM):
    id: int
    contact_id: int
    status: MessageStatus
    whatsapp_message_id: str | None
    error_detail: str | None
    booked: bool
    sent_at: datetime | None


class CampaignRoi(BaseModel):
    campaign: CampaignOut
    sent: int
    delivered: int
    read: int
    replied: int
    failed: int
    booked: int
    avg_ticket: float
    estimated_revenue: float
    messages: list[MessageOut]
