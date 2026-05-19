"""
User Management Routes — Admin only (RBAC)
Admin can: create accounts, list users, update roles, deactivate users
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas import UserCreate, UserUpdate, UserResponse, MessageResponse
from app.utils.auth import hash_password, get_current_user, require_admin, require_pm

router = APIRouter(prefix="/api/users", tags=["👤 User Management (Admin)"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (Admin only)",
)
def create_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Admin creates a new account and assigns a role.
    Roles: Admin, Project Manager, Team Member
    """
    existing = db.query(User).filter(
        (User.username == request.username) | (User.email == request.email)
    ).first()

    if existing:
        field = "username" if existing.username == request.username else "email"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This {field} is already registered",
        )

    new_user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        role=UserRole(request.role.value),
        email=request.email,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
)
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Returns all registered users."""
    return db.query(User).order_by(User.user_id).all()

@router.get(
    "/directory",
    response_model=List[UserResponse],
    summary="List active users for member selection (Admin or Project Manager)",
)
def list_users_directory(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pm),
):
    """Returns users available for adding to projects.
    Admins see all active users; Project Managers see only Team Members."""
    query = db.query(User).filter(User.is_active == True)
    if current_user.role == UserRole.PROJECT_MANAGER:
        query = query.filter(User.role == UserRole.TEAM_MEMBER)
    return query.order_by(User.user_id).all()

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin only)",
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Returns a single user's details."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user details (Admin only)",
)
def update_user(
    user_id: int,
    request: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin can update username, role, email, or deactivate a user."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.username is not None:
        exists = db.query(User).filter(User.username == request.username, User.user_id != user_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already taken")
        user.username = request.username

    if request.email is not None:
        exists = db.query(User).filter(User.email == request.email, User.user_id != user_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Email already taken")
        user.email = request.email

    if request.role is not None:
        user.role = UserRole(request.role.value)

    if request.is_active is not None:
        user.is_active = request.is_active

    db.commit()
    db.refresh(user)

    return user

@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    summary="Deactivate a user account (Admin only)",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Soft-deletes a user by setting is_active = False.
    Does not remove data from the database.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.user_id == admin.user_id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    user.is_active = False
    db.commit()

    return MessageResponse(message=f"User '{user.username}' has been deactivated ✅")
