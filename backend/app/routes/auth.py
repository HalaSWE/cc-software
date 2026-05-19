"""
Auth Routes — Login & Reset Password
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas import LoginRequest, TokenResponse, ResetPasswordRequest, UserResponse, MessageResponse, UserCreate, ProfileUpdate
from app.models.user import UserRole
from app.utils.auth import verify_password, hash_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["🔐 Authentication"])

@router.post("/login", response_model=TokenResponse, summary="Login and get JWT token")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with username & password.
    Returns a JWT token for accessing protected endpoints.
    """
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact admin.",
        )

    token = create_access_token(data={
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role.value,
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )

@router.post("/register", response_model=TokenResponse, summary="Register a new account")
def register(request: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.
    Default role is Team Member.
    """
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
        role=UserRole.TEAM_MEMBER,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={
        "user_id": new_user.user_id,
        "username": new_user.username,
        "role": new_user.role.value,
    })

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(new_user),
    )

@router.get("/me", response_model=UserResponse, summary="Get current logged-in user")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently authenticated user."""
    return current_user

@router.put("/reset-password", response_model=MessageResponse, summary="Reset your password")
def reset_password(
    request: ResetPasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Allows a logged-in user to change their password.
    Requires the current password for verification.
    """
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(request.new_password)
    db.commit()

    return MessageResponse(message="Password updated successfully ✅")

@router.put("/profile", response_model=UserResponse, summary="Update your profile")
def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.bio is not None:
        current_user.bio = data.bio
    if data.email is not None:
        existing = db.query(User).filter(User.email == data.email, User.user_id != current_user.user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        current_user.email = data.email
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/my-projects", summary="Get all projects I'm enrolled in")
def my_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.project import Project, ProjectMemberDetail
    from app.models.evm import WBSTask, TaskStatus
    managed = db.query(Project).filter(Project.manager_id == current_user.user_id).all()
    member_ids = {r[0] for r in db.query(ProjectMemberDetail.assigned_project).filter(
        ProjectMemberDetail.user_id == current_user.user_id).all()}
    member_projects = db.query(Project).filter(
        Project.project_id.in_(member_ids),
        Project.manager_id != current_user.user_id
    ).all() if member_ids else []

    def _proj(p, relation):
        tasks = db.query(WBSTask).filter(WBSTask.project_id == p.project_id).all()
        done  = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        return {
            "project_id": p.project_id,
            "name": p.name,
            "status": p.status.value,
            "budget": float(p.budget),
            "start_date": str(p.start_date) if p.start_date else None,
            "end_date": str(p.end_date) if p.end_date else None,
            "relation": relation,
            "task_total": len(tasks),
            "task_done": done,
        }

    return {
        "managed":  [_proj(p, "manager") for p in managed],
        "member":   [_proj(p, "member")  for p in member_projects],
        "stats": {
            "total_projects": len(managed) + len(member_projects),
            "managing": len(managed),
            "member_of": len(member_projects),
        }
    }
