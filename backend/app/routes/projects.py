"""
Project Management Routes — Sprint 2
CRUD operations for projects + member management
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectMemberDetail, ProjectStatus
from app.models.user import User
from app.schemas import (ProjectCreate, ProjectUpdate, ProjectResponse,
                         ProjectDetailResponse, ProjectMemberAdd,
                         ProjectMemberResponse, MessageResponse)
from app.utils.auth import get_current_user, require_pm, require_any, check_project_access
from app.utils.notify import notify

router = APIRouter(prefix="/api/projects", tags=["📁 Project Management"])

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/", response_model=ProjectResponse, status_code=201,
             summary="Create a new project (PM or Admin)")
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pm),
):
    project = Project(
        name=data.name,
        description=data.description,
        budget=data.budget,
        start_date=data.start_date,
        end_date=data.end_date,
        created_by=current_user.user_id,
        manager_id=data.manager_id,
        status=ProjectStatus.PENDING,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    notify(db, project.project_id,
           "Project Created",
           f"Project '{project.name}' was created by {current_user.username}.",
           "info")
    db.commit()
    return _project_response(project, db)

def _project_response(project: Project, db: Session) -> ProjectResponse:
    mgr_name = None
    if project.manager_id:
        u = db.query(User).filter(User.user_id == project.manager_id).first()
        mgr_name = u.username if u else None
    data = {c.name: getattr(project, c.name) for c in project.__table__.columns}
    data['manager_name'] = mgr_name
    return ProjectResponse.model_validate(data)

@router.get("/", response_model=List[ProjectResponse],
            summary="List visible projects")
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    from app.models.user import UserRole
    if current_user.role == UserRole.ADMIN:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
    else:
        member_project_ids = db.query(ProjectMemberDetail.assigned_project).filter(
            ProjectMemberDetail.user_id == current_user.user_id
        ).subquery()
        projects = db.query(Project).filter(
            (Project.manager_id == current_user.user_id) |
            (Project.project_id.in_(member_project_ids))
        ).order_by(Project.created_at.desc()).all()
    return [_project_response(p, db) for p in projects]

@router.get("/{project_id}", response_model=ProjectDetailResponse,
            summary="Get project details with members")
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    project = _get_project_or_404(project_id, db)
    check_project_access(project_id, current_user, db)
    members = []
    for m in project.members:
        u = db.query(User).filter(User.user_id == m.user_id).first()
        resp = ProjectMemberResponse.model_validate(m)
        resp.username = u.username if u else ""
        members.append(resp)
    detail = ProjectDetailResponse.model_validate(project)
    detail.members = members
    return detail

@router.put("/{project_id}", response_model=ProjectResponse,
            summary="Update project (PM or Admin)")
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pm),
):
    project = _get_project_or_404(project_id, db)

    old_status = project.status.value
    if data.name        is not None: project.name        = data.name
    if data.description is not None: project.description = data.description
    if data.budget      is not None: project.budget      = data.budget
    if data.start_date  is not None: project.start_date  = data.start_date
    if data.end_date    is not None: project.end_date    = data.end_date
    if data.manager_id  is not None: project.manager_id  = data.manager_id
    if data.status      is not None:
        from app.models.project import ProjectStatus as PS
        project.status = PS(data.status.value)

    db.commit()
    db.refresh(project)

    if data.status is not None and data.status.value != old_status:
        notify(db, project_id,
               "Project Status Changed",
               f"Project '{project.name}' status changed from {old_status} to {data.status.value} by {current_user.username}.",
               "info")
    else:
        notify(db, project_id,
               "Project Updated",
               f"Project '{project.name}' details were updated by {current_user.username}.",
               "info")
    db.commit()
    return _project_response(project, db)

@router.delete("/{project_id}", response_model=MessageResponse,
               summary="Delete project (Admin only)")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.user import UserRole
    project = _get_project_or_404(project_id, db)
    is_admin = current_user.role == UserRole.ADMIN
    is_owner_pm = (current_user.role == UserRole.PROJECT_MANAGER and project.manager_id == current_user.user_id)
    if not is_admin and not is_owner_pm:
        raise HTTPException(status_code=403, detail="Admin or project owner only")
    db.delete(project)
    db.commit()
    return MessageResponse(message=f"Project '{project.name}' deleted ✅")

@router.post("/{project_id}/members", response_model=MessageResponse, status_code=201,
             summary="Add member to project (PM or Admin)")
def add_member(
    project_id: int,
    data: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pm),
):
    _get_project_or_404(project_id, db)
    user = db.query(User).filter(User.user_id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(ProjectMemberDetail).filter_by(
        assigned_project=project_id, user_id=data.user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already in project")

    project = _get_project_or_404(project_id, db)
    member = ProjectMemberDetail(
        assigned_project=project_id,
        user_id=data.user_id,
        role_in_project=data.role_in_project,
    )
    db.add(member)
    notify(db, project_id,
           "Member Added",
           f"{user.username} was added to project '{project.name}' by {current_user.username}.",
           "info")
    db.commit()
    return MessageResponse(message=f"User '{user.username}' added to project ✅")

@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse,
               summary="Remove member from project (PM or Admin)")
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_pm),
):
    project = _get_project_or_404(project_id, db)
    member = db.query(ProjectMemberDetail).filter_by(
        assigned_project=project_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in project")
    removed_user = db.query(User).filter(User.user_id == user_id).first()
    db.delete(member)
    notify(db, project_id,
           "Member Removed",
           f"{removed_user.username if removed_user else 'A member'} was removed from project '{project.name}' by {current_user.username}.",
           "warning")
    db.commit()
    return MessageResponse(message="Member removed ✅")
