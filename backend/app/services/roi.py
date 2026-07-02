"""Campaign ROI aggregation (PRD §5.6)."""
from __future__ import annotations

from app.models import Campaign, Message, MessageStatus
from app.schemas import CampaignOut, CampaignRoi, MessageOut


def build_roi(campaign: Campaign, avg_ticket: float) -> CampaignRoi:
    messages: list[Message] = campaign.messages

    # Terminal statuses are cumulative: a delivered/read/replied message was
    # also sent. Count "reached at least this far" rather than exact-status.
    sent = len(messages)
    failed = sum(1 for m in messages if m.status == MessageStatus.failed)
    reached = [m for m in messages if m.status != MessageStatus.failed]
    delivered = sum(
        1 for m in reached
        if m.status in (MessageStatus.delivered, MessageStatus.read, MessageStatus.replied)
    )
    read = sum(1 for m in reached if m.status in (MessageStatus.read, MessageStatus.replied))
    replied = sum(1 for m in reached if m.status == MessageStatus.replied)
    booked = sum(1 for m in messages if m.booked)

    return CampaignRoi(
        campaign=CampaignOut.model_validate(campaign),
        sent=sent,
        delivered=delivered,
        read=read,
        replied=replied,
        failed=failed,
        booked=booked,
        avg_ticket=avg_ticket,
        # Booked drives real revenue (manual admin toggle per PRD decision).
        estimated_revenue=round(booked * avg_ticket, 2),
        messages=[MessageOut.model_validate(m) for m in messages],
    )
