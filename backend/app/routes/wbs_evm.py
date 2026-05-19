"""
WBS & EVM Routes — v2.0
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.models.evm import WBSTask, EVMMetrics, Notification, TaskStatus
from app.models.user import User
from app.schemas import (WBSTaskCreate, WBSTaskUpdate, WBSTaskResponse,
                         EVMMetricsResponse, DashboardResponse, MessageResponse,
                         ProjectStatusEnum)
from app.utils.auth import require_pm, require_any, check_project_access, visible_project_ids
from app.utils.notify import notify

router = APIRouter(tags=["🗂 WBS & EVM"])

def _recalculate_evm(project_id: int, db: Session):
    tasks = db.query(WBSTask).filter(WBSTask.project_id == project_id).all()
    if not tasks:
        return None

    bac = sum(float(t.planned_value or 0) for t in tasks)
    pv  = bac
    ev  = sum(t.earned_value for t in tasks)
    ac  = sum(float(t.actual_cost or 0) for t in tasks)

    cv  = ev - ac
    sv  = ev - pv
    cpi = ev / ac if ac > 0 else 1.0
    spi = ev / pv if pv > 0 else 1.0
    eac = bac / cpi if cpi > 0 else bac
    etc = eac - ac
    vac = bac - eac

    is_over_budget     = cpi < 0.9
    is_behind_schedule = spi < 0.9

    evm = db.query(EVMMetrics).filter_by(project_id=project_id).first()
    if not evm:
        evm = EVMMetrics(project_id=project_id)
        db.add(evm)

    evm.bac = round(bac, 2)
    evm.pv  = round(pv, 2)
    evm.ev  = round(ev, 2)
    evm.ac  = round(ac, 2)
    evm.cv  = round(cv, 2)
    evm.sv  = round(sv, 2)
    evm.cpi = round(cpi, 4)
    evm.spi = round(spi, 4)
    evm.eac = round(eac, 2)
    evm.etc = round(etc, 2)
    evm.vac = round(vac, 2)
    evm.is_over_budget     = is_over_budget
    evm.is_behind_schedule = is_behind_schedule

    db.commit()
    return evm

@router.post("/api/projects/{project_id}/tasks",
             response_model=WBSTaskResponse, status_code=201,
             summary="Add WBS task to project")
def create_task(project_id: int, data: WBSTaskCreate,
                db: Session = Depends(get_db), current_user: User = Depends(require_pm)):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)

    task = WBSTask(
        project_id=project_id,
        task_name=data.task_name,
        description=data.description,
        planned_value=data.planned_value,
        order_index=data.order_index,
        status=TaskStatus.NOT_STARTED.value,
        actual_cost=0.0,
        percent_complete=0.0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    notify(db, project_id,
           "Task Added",
           f"New task '{data.task_name}' added to project '{project.name}' by {current_user.username}.",
           "info")
    db.commit()
    _recalculate_evm(project_id, db)
    resp = WBSTaskResponse.model_validate(task)
    resp.earned_value = task.earned_value
    return resp

@router.get("/api/projects/{project_id}/tasks",
            response_model=List[WBSTaskResponse],
            summary="Get all WBS tasks for a project")
def list_tasks(project_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    tasks = db.query(WBSTask).filter(
        WBSTask.project_id == project_id
    ).order_by(WBSTask.order_index).all()
    result = []
    for t in tasks:
        r = WBSTaskResponse.model_validate(t)
        r.earned_value = t.earned_value
        result.append(r)
    return result

@router.put("/api/projects/{project_id}/tasks/{task_id}",
            response_model=WBSTaskResponse,
            summary="Update task progress, actual cost, status")
def update_task(project_id: int, task_id: int, data: WBSTaskUpdate,
                db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    task = db.query(WBSTask).filter(
        WBSTask.task_id == task_id, WBSTask.project_id == project_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if data.task_name        is not None: task.task_name        = data.task_name
    if data.description      is not None: task.description      = data.description
    if data.planned_value    is not None: task.planned_value    = data.planned_value
    if data.actual_cost      is not None: task.actual_cost      = data.actual_cost
    if data.percent_complete is not None: task.percent_complete = data.percent_complete
    if data.order_index      is not None: task.order_index      = data.order_index
    if data.status           is not None: task.status           = data.status.value

    was_completed = task.status == TaskStatus.COMPLETED.value
    if data.percent_complete == 100:
        task.status = TaskStatus.COMPLETED.value
    elif data.percent_complete and data.percent_complete > 0:
        task.status = TaskStatus.IN_PROGRESS.value

    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not was_completed and task.status == TaskStatus.COMPLETED.value:
        notify(db, project_id,
               "Task Completed",
               f"Task '{task.task_name}' in project '{project.name}' marked as completed by {current_user.username}.",
               "info")

    db.commit()
    db.refresh(task)
    _recalculate_evm(project_id, db)
    resp = WBSTaskResponse.model_validate(task)
    resp.earned_value = task.earned_value
    return resp

@router.delete("/api/projects/{project_id}/tasks/{task_id}",
               response_model=MessageResponse,
               summary="Delete a WBS task")
def delete_task(project_id: int, task_id: int,
                db: Session = Depends(get_db), current_user: User = Depends(require_pm)):
    check_project_access(project_id, current_user, db)
    task = db.query(WBSTask).filter(
        WBSTask.task_id == task_id, WBSTask.project_id == project_id
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    project = db.query(Project).filter(Project.project_id == project_id).first()
    task_name = task.task_name
    db.delete(task)
    notify(db, project_id,
           "Task Removed",
           f"Task '{task_name}' was removed from project '{project.name}' by {current_user.username}.",
           "warning")
    db.commit()
    _recalculate_evm(project_id, db)
    return MessageResponse(message="Task deleted ✅")

@router.get("/api/projects/{project_id}/evm",
            response_model=EVMMetricsResponse,
            summary="Get auto-calculated EVM metrics")
def get_evm(project_id: int, db: Session = Depends(get_db),
            current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    evm = _recalculate_evm(project_id, db)
    if not evm:
        evm = db.query(EVMMetrics).filter_by(project_id=project_id).first()
    if not evm:
        raise HTTPException(status_code=404, detail="No EVM data — add WBS tasks first")
    return evm

@router.get("/api/dashboard",
            response_model=List[DashboardResponse],
            tags=["📈 Dashboard"],
            summary="Dashboard overview for all projects")
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    ids = visible_project_ids(current_user, db)
    q = db.query(Project).order_by(Project.created_at.desc())
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    result = []
    for p in projects:
        tasks = db.query(WBSTask).filter(WBSTask.project_id == p.project_id).all()
        tasks_total = len(tasks)
        tasks_done  = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)
        progress    = (tasks_done / tasks_total * 100) if tasks_total > 0 else 0

        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        result.append(DashboardResponse(
            project_id   = p.project_id,
            project_name = p.name,
            budget       = float(p.budget),
            status       = ProjectStatusEnum(p.status.value),
            evm          = EVMMetricsResponse.model_validate(evm) if evm else None,
            tasks_total  = tasks_total,
            tasks_done   = tasks_done,
            progress_pct = round(progress, 1),
        ))
    return result

@router.get("/api/notifications",
            tags=["🔔 Notifications"],
            summary="Get all notifications")
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    ids = visible_project_ids(current_user, db)
    q = db.query(Notification).order_by(Notification.created_at.desc())
    if ids is not None:
        q = q.filter(Notification.project_id.in_(ids))
    return q.limit(50).all()

@router.put("/api/notifications/{notif_id}/read",
            tags=["🔔 Notifications"],
            response_model=MessageResponse,
            summary="Mark notification as read")
def mark_read(notif_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(require_any)):
    notif = db.query(Notification).filter(Notification.notification_id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return MessageResponse(message="Marked as read ✅")


@router.delete("/api/notifications",
               tags=["🔔 Notifications"],
               response_model=MessageResponse,
               summary="Delete all notifications visible to current user")
def delete_all_notifications(db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    ids = visible_project_ids(current_user, db)
    q = db.query(Notification)
    if ids is not None:
        q = q.filter(Notification.project_id.in_(ids))
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return MessageResponse(message=f"Deleted {deleted} notification(s) ✅")
