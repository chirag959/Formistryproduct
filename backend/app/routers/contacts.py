"""Contact upload + lapsed listing (PRD §5.1, §5.2)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_scoped_workspace, require_workspace_admin
from app.models import Contact, Workspace
from app.schemas import ContactOut, LapsedContactOut, UploadSummary
from app.services.csv_import import import_contacts
from app.services.lapsed import days_since_visit, get_lapsed_contacts

router = APIRouter(prefix="/workspaces/{workspace_id}/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(
    workspace: Workspace = Depends(get_scoped_workspace),
    db: Session = Depends(get_db),
):
    return (
        db.query(Contact)
        .filter(Contact.workspace_id == workspace.id)
        .order_by(Contact.created_at.desc())
        .all()
    )


@router.post("/upload", response_model=UploadSummary)
async def upload_contacts(
    file: UploadFile = File(...),
    workspace: Workspace = Depends(require_workspace_admin),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    content = await file.read()
    return import_contacts(db, workspace.id, content)


@router.get("/lapsed", response_model=list[LapsedContactOut])
def lapsed_contacts(
    workspace: Workspace = Depends(get_scoped_workspace),
    db: Session = Depends(get_db),
):
    contacts = get_lapsed_contacts(db, workspace)
    return [
        LapsedContactOut(
            id=c.id,
            name=c.name,
            phone=c.phone,
            last_visit_date=c.last_visit_date,
            created_at=c.created_at,
            days_since_visit=days_since_visit(c),
        )
        for c in contacts
    ]
