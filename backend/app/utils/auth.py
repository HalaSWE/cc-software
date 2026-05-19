"""
Auth Utilities — JWT tokens, password hashing, RBAC dependencies
"""
import os
from datetime import datetime, timedelta, timezone
from typing import List

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-to-a-random-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(plain_password: str) -> str:
    """Hash a plain password using bcrypt."""
    return bcrypt.hashpw(plain_password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))

def create_access_token(data: dict) -> str:
    """Create a JWT token with expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract user from JWT token.
    Used as a dependency in protected routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id).first()

    if user is None or not user.is_active:
        raise credentials_exception

    return user

def require_roles(allowed_roles: List[UserRole]):
    """
    Dependency factory — restricts access to specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles([UserRole.ADMIN]))])
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker

require_admin = require_roles([UserRole.ADMIN])
require_pm = require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER])
require_any = require_roles([UserRole.ADMIN, UserRole.PROJECT_MANAGER, UserRole.TEAM_MEMBER])

def check_project_access(project_id: int, user: User, db: Session) -> None:
    """
    Raises HTTP 403 if the user cannot access this project.
    Admin: always allowed.
    PM / Team Member: only if they are the manager or an assigned member.
    """
    if user.role == UserRole.ADMIN:
        return
    from app.models.project import Project, ProjectMemberDetail
    is_manager = db.query(Project).filter_by(
        project_id=project_id, manager_id=user.user_id
    ).first() is not None
    is_member = db.query(ProjectMemberDetail).filter_by(
        assigned_project=project_id, user_id=user.user_id
    ).first() is not None
    if not (is_manager or is_member):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have access to this project")

def visible_project_ids(user: User, db: Session):
    """Return set of project_ids the user can see, or None if admin (sees all)."""
    if user.role == UserRole.ADMIN:
        return None
    from app.models.project import Project, ProjectMemberDetail
    managed  = {r[0] for r in db.query(Project.project_id).filter(Project.manager_id == user.user_id).all()}
    membered = {r[0] for r in db.query(ProjectMemberDetail.assigned_project).filter(ProjectMemberDetail.user_id == user.user_id).all()}
    return managed | membered
