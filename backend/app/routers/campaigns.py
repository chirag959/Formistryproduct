"""Campaigns: create + fire to lapsed contacts, status/ROI, booked toggle.

Sending runs in a FastAPI BackgroundTask (PRD §3) so the 'Send to X' click
returns immediately while ~500 messages go out.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import SessionLocal, get_db
from app.deps import get_scoped_workspace, require_workspace_admin
from app.models import Campaign, CampaignStatus, Contact, Message, MessageStatus, Workspace
from app.schemas import CampaignCreate, CampaignOut, CampaignRoi, MessageOut
from app.services.lapsed import get_lapsed_contacts
from app.services.roi import build_roi
from app.services.whatsapp import WhatsAppError, is_configured, send_template

logger = logging.getLogger("campaigns")
router = APIRouter(prefix="/workspaces/{workspace_id}/campaigns", tags=["campaigns"])


def _dispatch_campaign(campaign_id: int, workspace_id: int) -> None:
    """Background worker: send the template to every lapsed contact, log each."""
    db = SessionLocal()
    try:
        campaign = db.get(Campaign, campaign_id)
        workspace = db.get(Workspace, workspace_id)
        if not campaign or not workspace:
            return
        campaign.status = CampaignStatus.sending
        db.commit()

        contacts = get_lapsed_contacts(db, workspace)
        body_params = [campaign.discount_offer] if campaign.discount_offer else None
        any_ok = False

        for contact in contacts:
            msg = Message(
                campaign_id=campaign.id,
                contact_id=contact.id,
                workspace_id=workspace.id,
                status=MessageStatus.sent,
            )
            try:
                wamid = send_template(
                    phone_number_id=workspace.whatsapp_phone_number_id or "",
                    to_phone=contact.phone,
                    template_name=campaign.template_name,
                    body_params=body_params,
                )
                msg.whatsapp_message_id = wamid
                msg.status = MessageStatus.sent
                any_ok = True
            except WhatsAppError as exc:
                msg.status = MessageStatus.failed
                msg.error_detail = str(exc)  # loud, visible failure (PRD §10)
                logger.error("Campaign %s contact %s failed: %s", campaign.id, contact.id, exc)
            db.add(msg)
            db.commit()

        campaign.status = CampaignStatus.sent if any_ok or not contacts else CampaignStatus.failed
        db.commit()
        logger.info("Campaign %s dispatched to %s contacts", campaign.id, len(contacts))
    finally:
        db.close()


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    workspace: Workspace = Depends(get_scoped_workspace),
    db: Session = Depends(get_db),
):
    return (
        db.query(Campaign)
        .filter(Campaign.workspace_id == workspace.id)
        .order_by(Campaign.created_at.desc())
        .all()
    )


@router.post("", response_model=CampaignOut, status_code=201)
def create_and_send(
    body: CampaignCreate,
    background: BackgroundTasks,
    workspace: Workspace = Depends(require_workspace_admin),
    db: Session = Depends(get_db),
):
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail="WhatsApp is not configured (set WHATSAPP_ACCESS_TOKEN).",
        )
    if not workspace.whatsapp_phone_number_id:
        raise HTTPException(
            status_code=400,
            detail="Workspace has no whatsapp_phone_number_id configured.",
        )

    campaign = Campaign(
        workspace_id=workspace.id,
        template_name=body.template_name,
        discount_offer=body.discount_offer,
        status=CampaignStatus.draft,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    background.add_task(_dispatch_campaign, campaign.id, workspace.id)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignRoi)
def campaign_roi(
    campaign_id: int,
    workspace: Workspace = Depends(get_scoped_workspace),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.workspace_id == workspace.id)
        .one_or_none()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return build_roi(campaign, workspace.avg_ticket)


@router.post("/{campaign_id}/messages/{message_id}/booked", response_model=MessageOut)
def toggle_booked(
    campaign_id: int,
    message_id: int,
    booked: bool = True,
    workspace: Workspace = Depends(require_workspace_admin),
    db: Session = Depends(get_db),
):
    """Manually mark a message as booked (drives the ROI revenue number)."""
    msg = (
        db.query(Message)
        .filter(
            Message.id == message_id,
            Message.campaign_id == campaign_id,
            Message.workspace_id == workspace.id,
        )
        .one_or_none()
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.booked = booked
    db.commit()
    db.refresh(msg)
    return msg
