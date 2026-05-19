"""
Project Comments Routes
Full CRUD — any authenticated user can comment, only author/admin can edit/delete
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.evm import ProjectComment
from app.models.user import User, UserRole
from app.schemas import CommentCreate, CommentUpdate, CommentResponse, MessageResponse
from app.utils.auth import require_any, get_current_user, check_project_access
from app.utils.notify import notify

router = APIRouter(prefix="/api/projects", tags=["💬 Comments"])

@router.post("/{project_id}/comments", response_model=CommentResponse, status_code=201,
             summary="Post a comment on a project")
def create_comment(project_id: int, data: CommentCreate,
                   db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    if not db.query(Project).filter(Project.project_id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)
    comment = ProjectComment(
        project_id=project_id,
        user_id=current_user.user_id,
        content=data.content,
    )
    db.add(comment)
    project = db.query(Project).filter(Project.project_id == project_id).first()
    preview = data.content[:80] + ('…' if len(data.content) > 80 else '')
    notify(db, project_id,
           "New Comment",
           f"{current_user.username} commented on '{project.name if project else project_id}': \"{preview}\"",
           "info")
    db.commit()
    db.refresh(comment)
    resp = CommentResponse.model_validate(comment)
    resp.author_username = current_user.username
    return resp

@router.get("/{project_id}/comments", response_model=List[CommentResponse],
            summary="Get all comments for a project")
def list_comments(project_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    comments = db.query(ProjectComment).filter(
        ProjectComment.project_id == project_id
    ).order_by(ProjectComment.created_at.asc()).all()
    result = []
    for c in comments:
        r = CommentResponse.model_validate(c)
        r.author_username = c.author.username if c.author else "Unknown"
        result.append(r)
    return result

@router.put("/{project_id}/comments/{comment_id}", response_model=CommentResponse,
            summary="Edit a comment (author or admin only)")
def update_comment(project_id: int, comment_id: int, data: CommentUpdate,
                   db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    comment = db.query(ProjectComment).filter(
        ProjectComment.comment_id == comment_id,
        ProjectComment.project_id == project_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    comment.content = data.content
    db.commit()
    db.refresh(comment)
    resp = CommentResponse.model_validate(comment)
    resp.author_username = comment.author.username if comment.author else "Unknown"
    return resp

@router.delete("/{project_id}/comments/{comment_id}", response_model=MessageResponse,
               summary="Delete a comment (author or admin only)")
def delete_comment(project_id: int, comment_id: int,
                   db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    comment = db.query(ProjectComment).filter(
        ProjectComment.comment_id == comment_id,
        ProjectComment.project_id == project_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    db.delete(comment)
    db.commit()
    return MessageResponse(message="Comment deleted ✅")
