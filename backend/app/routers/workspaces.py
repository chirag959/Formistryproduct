"""Workspace management. Creation is agency-admin only (PRD §2)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, get_scoped_workspace, require_agency_admin
from app.models import User, Workspace
from app.schemas import UserOut, WorkspaceCreate, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Agency admin sees all; a scoped user sees only their own workspace."""
    if user.is_agency_admin:
        return db.query(Workspace).order_by(Workspace.name).all()
    if user.workspace_id is None:
        return []
    return db.query(Workspace).filter(Workspace.id == user.workspace_id).all()


@router.post("", response_model=WorkspaceOut, status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    _: User = Depends(require_agency_admin),
    db: Session = Depends(get_db),
):
    ws = Workspace(**body.model_dump())
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(workspace: Workspace = Depends(get_scoped_workspace)):
    return workspace


@router.get("/me/current", response_model=UserOut)
def whoami(user: User = Depends(get_current_user)):
    return user
