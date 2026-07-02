"""Shared FastAPI dependencies: current user + workspace scoping (PRD §2)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User, Workspace
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_agency_admin(user: User = Depends(get_current_user)) -> User:
    """Only the agency admin (admin role, no workspace) may create workspaces."""
    if not user.is_agency_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agency admin only")
    return user


def get_scoped_workspace(
    workspace_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Workspace:
    """Return the workspace only if the caller may access it.

    Agency admins see every workspace; everyone else is pinned to their own.
    This is the single choke point that enforces tenant isolation — every
    /workspaces/{id}/... route depends on it.
    """
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    if not user.is_agency_admin and user.workspace_id != workspace_id:
        # Do not leak existence of other tenants' workspaces.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def require_workspace_admin(
    workspace: Workspace = Depends(get_scoped_workspace),
    user: User = Depends(get_current_user),
) -> Workspace:
    """Mutating actions (upload, campaigns, booked toggle) require admin role."""
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return workspace
