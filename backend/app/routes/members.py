"""
Project Members Management Routes
Add, list, and remove members from projects
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectMemberDetail
from app.models.user import User
from app.schemas import ProjectMemberAdd, ProjectMemberResponse, MessageResponse
from app.utils.auth import require_pm, require_any, check_project_access

router = APIRouter(prefix="/api/projects", tags=["👥 Member Management"])

@router.get("/{project_id}/members", response_model=List[ProjectMemberResponse],
            summary="List all members of a project")
def list_members(project_id: int, db: Session = Depends(get_db),
                 current_user: User = Depends(require_any)):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)
    members = db.query(ProjectMemberDetail).filter(
        ProjectMemberDetail.assigned_project == project_id
    ).all()
    result = []
    member_user_ids = set()
    for m in members:
        u = db.query(User).filter(User.user_id == m.user_id).first()
        r = ProjectMemberResponse.model_validate(m)
        r.username = u.username if u else ""
        result.append(r)
        member_user_ids.add(m.user_id)
    # Include the project manager at the top if not already in the member list
    if project.manager_id and project.manager_id not in member_user_ids:
        pm_user = db.query(User).filter(User.user_id == project.manager_id).first()
        if pm_user:
            pm_entry = ProjectMemberResponse(
                detail_id=0,
                assigned_project=project_id,
                user_id=pm_user.user_id,
                username=pm_user.username,
                role_in_project="Project Manager",
                assigned_at=project.created_at,
                is_manager=True,
            )
            result.insert(0, pm_entry)
    return result

@router.post("/{project_id}/members", response_model=MessageResponse, status_code=201,
             summary="Add a member to a project (PM or Admin)")
def add_member(project_id: int, data: ProjectMemberAdd,
               db: Session = Depends(get_db), current_user: User = Depends(require_pm)):
    if not db.query(Project).filter(Project.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)
    user = db.query(User).filter(User.user_id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(ProjectMemberDetail).filter_by(
        assigned_project=project_id, user_id=data.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this project")
    member = ProjectMemberDetail(
        assigned_project=project_id,
        user_id=data.user_id,
        role_in_project=data.role_in_project,
    )
    db.add(member)
    db.commit()
    return MessageResponse(message=f"'{user.username}' added to project ✅")

@router.delete("/{project_id}/members/{user_id}", response_model=MessageResponse,
               summary="Remove a member from a project (PM or Admin)")
def remove_member(project_id: int, user_id: int,
                  db: Session = Depends(get_db), current_user: User = Depends(require_pm)):
    check_project_access(project_id, current_user, db)
    member = db.query(ProjectMemberDetail).filter_by(
        assigned_project=project_id, user_id=user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found in this project")
    db.delete(member)
    db.commit()
    return MessageResponse(message="Member removed ✅")
