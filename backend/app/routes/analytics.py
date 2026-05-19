"""
Analytics Routes — Sprint 6+
Advanced portfolio analytics, risk scoring, trend analysis, executive summary
"""
from typing import List, Optional
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.project import Project, ProjectScoring, ProjectSelectionMetrics, ProjectStatus
from app.models.evm import WBSTask, EVMMetrics, TaskStatus
from app.models.user import User, UserRole
from app.utils.auth import require_any, require_pm, visible_project_ids, check_project_access

router = APIRouter(prefix="/api/analytics", tags=["🧠 Analytics"])

@router.get("/portfolio/summary", summary="Executive portfolio summary")
def portfolio_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """High-level KPIs for the project portfolio visible to the current user."""
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    all_projects = q.all()
    total = len(all_projects)

    status_counts = {}
    for p in all_projects:
        s = p.status.value
        status_counts[s] = status_counts.get(s, 0) + 1

    total_budget = sum(float(p.budget) for p in all_projects)
    selected_projects = [p for p in all_projects if p.is_selected]

    project_ids = [p.project_id for p in all_projects]
    evm_q = db.query(EVMMetrics).filter(EVMMetrics.project_id.in_(project_ids)) if project_ids else db.query(EVMMetrics).filter(False)
    all_evms = evm_q.all()
    healthy = sum(1 for e in all_evms if float(e.cpi or 0) >= 0.9 and float(e.spi or 0) >= 0.9)
    at_risk = sum(1 for e in all_evms if float(e.cpi or 0) < 0.9 or float(e.spi or 0) < 0.9)
    avg_cpi = round(sum(float(e.cpi or 1) for e in all_evms) / len(all_evms), 3) if all_evms else None
    avg_spi = round(sum(float(e.spi or 1) for e in all_evms) / len(all_evms), 3) if all_evms else None

    task_q = db.query(WBSTask).filter(WBSTask.project_id.in_(project_ids)) if project_ids else db.query(WBSTask).filter(False)
    all_tasks = task_q.all()
    tasks_done = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED)
    task_completion_rate = round(tasks_done / len(all_tasks) * 100, 1) if all_tasks else 0

    total_ac = sum(float(e.ac or 0) for e in all_evms)
    total_ev = sum(float(e.ev or 0) for e in all_evms)
    total_pv = sum(float(e.pv or 0) for e in all_evms)

    return {
        "total_projects": total,
        "total_budget": round(total_budget, 2),
        "selected_projects": len(selected_projects),
        "status_distribution": status_counts,
        "evm": {
            "healthy_projects": healthy,
            "at_risk_projects": at_risk,
            "avg_cpi": avg_cpi,
            "avg_spi": avg_spi,
            "total_pv": round(total_pv, 2),
            "total_ev": round(total_ev, 2),
            "total_ac": round(total_ac, 2),
        },
        "tasks": {
            "total": len(all_tasks),
            "completed": tasks_done,
            "completion_rate_pct": task_completion_rate,
        },
        "users": {
            "total": db.query(User).count(),
            "active": db.query(User).filter(User.is_active == True).count(),
            "admins": db.query(User).filter(User.role == UserRole.ADMIN).count(),
            "project_managers": db.query(User).filter(User.role == UserRole.PROJECT_MANAGER).count(),
            "team_members": db.query(User).filter(User.role == UserRole.TEAM_MEMBER).count(),
        },
    }

@router.get("/portfolio/risk", summary="Risk assessment for all projects")
def portfolio_risk(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """Risk score per project based on EVM indicators."""
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    results = []

    for p in projects:
        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        tasks = db.query(WBSTask).filter(WBSTask.project_id == p.project_id).all()

        risk_score = 0
        risk_flags = []

        if evm:
            cpi = float(evm.cpi or 1)
            spi = float(evm.spi or 1)
            if cpi < 0.75:
                risk_score += 40
                risk_flags.append("Critical cost overrun (CPI < 0.75)")
            elif cpi < 0.9:
                risk_score += 20
                risk_flags.append("Cost overrun warning (CPI < 0.9)")

            if spi < 0.75:
                risk_score += 40
                risk_flags.append("Critical schedule delay (SPI < 0.75)")
            elif spi < 0.9:
                risk_score += 20
                risk_flags.append("Schedule delay warning (SPI < 0.9)")

        if p.end_date:
            days_remaining = (p.end_date - date.today()).days
            if days_remaining < 0 and p.status not in [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]:
                risk_score += 30
                risk_flags.append(f"Project overdue by {abs(days_remaining)} days")
            elif days_remaining < 30:
                risk_score += 10
                risk_flags.append(f"Deadline in {days_remaining} days")

        if not tasks and p.status == ProjectStatus.IN_PROGRESS:
            risk_score += 20
            risk_flags.append("No WBS tasks defined")

        risk_level = "Critical" if risk_score >= 60 else \
                     "High"     if risk_score >= 40 else \
                     "Medium"   if risk_score >= 20 else "Low"

        results.append({
            "project_id": p.project_id,
            "project_name": p.name,
            "status": p.status.value,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "cpi": float(evm.cpi) if evm and evm.cpi else None,
            "spi": float(evm.spi) if evm and evm.spi else None,
            "days_remaining": (p.end_date - date.today()).days if p.end_date else None,
        })

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results

@router.get("/portfolio/budget", summary="Budget utilisation across portfolio")
def portfolio_budget(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """Budget vs actual spend breakdown for visible projects."""
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    items = []

    for p in projects:
        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        budget = float(p.budget)
        ac = float(evm.ac or 0) if evm else 0
        ev = float(evm.ev or 0) if evm else 0
        utilisation = round(ac / budget * 100, 1) if budget > 0 else 0
        variance = round(budget - ac, 2)

        items.append({
            "project_id": p.project_id,
            "project_name": p.name,
            "budget": budget,
            "actual_cost": ac,
            "earned_value": ev,
            "utilisation_pct": utilisation,
            "budget_variance": variance,
            "status": p.status.value,
            "is_over_budget": ac > budget,
        })

    items.sort(key=lambda x: x["utilisation_pct"], reverse=True)
    return items

@router.get("/projects/{project_id}/evm/trend", summary="EVM trend data for a project")
def evm_trend(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """
    Returns simulated EVM trend snapshots for charting.
    In a full implementation this would pull from historical snapshots table.
    """
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        return {"error": "Project not found"}
    check_project_access(project_id, current_user, db)
    tasks = db.query(WBSTask).filter(WBSTask.project_id == project_id).all()
    evm   = db.query(EVMMetrics).filter_by(project_id=project_id).first()

    sorted_tasks = sorted(tasks, key=lambda t: t.order_index)
    cumulative_pv, cumulative_ev, cumulative_ac = 0.0, 0.0, 0.0
    trend = []

    for i, t in enumerate(sorted_tasks):
        cumulative_pv += float(t.planned_value or 0)
        cumulative_ev += t.earned_value
        cumulative_ac += float(t.actual_cost or 0)
        trend.append({
            "period": f"T{i+1}: {t.task_name[:20]}",
            "pv": round(cumulative_pv, 2),
            "ev": round(cumulative_ev, 2),
            "ac": round(cumulative_ac, 2),
            "cpi": round(cumulative_ev / cumulative_ac, 3) if cumulative_ac > 0 else 1.0,
            "spi": round(cumulative_ev / cumulative_pv, 3) if cumulative_pv > 0 else 1.0,
        })

    return {
        "project_id": project_id,
        "project_name": project.name,
        "current_evm": {
            "pv":  float(evm.pv  or 0) if evm else 0,
            "ev":  float(evm.ev  or 0) if evm else 0,
            "ac":  float(evm.ac  or 0) if evm else 0,
            "cpi": float(evm.cpi or 1) if evm else 1,
            "spi": float(evm.spi or 1) if evm else 1,
            "eac": float(evm.eac or 0) if evm else 0,
            "etc": float(evm.etc or 0) if evm else 0,
        },
        "trend": trend,
    }

@router.get("/selection/leaderboard", summary="Full scoring leaderboard with all metrics")
def selection_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    """Detailed leaderboard combining scoring + EVM health."""
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    items = []

    for p in projects:
        m = db.query(ProjectSelectionMetrics).filter_by(project_id=p.project_id).first()
        s = db.query(ProjectScoring).filter_by(project_id=p.project_id).first()
        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()

        items.append({
            "project_id": p.project_id,
            "name": p.name,
            "budget": float(p.budget),
            "status": p.status.value,
            "is_selected": p.is_selected,
            "scoring": {
                "total_score":   float(s.total_score)   if s and s.total_score   else None,
                "roi_score":     float(s.roi_score)     if s and s.roi_score     else None,
                "bcr_score":     float(s.bcr_score)     if s and s.bcr_score     else None,
                "payback_score": float(s.payback_score) if s and s.payback_score else None,
                "eva_score":     float(s.eva_score)     if s and s.eva_score     else None,
            },
            "financials": {
                "roi":            float(m.roi)            if m and m.roi            else None,
                "bcr":            float(m.bcr)            if m and m.bcr            else None,
                "npv":            float(m.npv)            if m and m.npv            else None,
                "payback_period": float(m.payback_period) if m and m.payback_period else None,
            },
            "evm_health": {
                "cpi": float(evm.cpi) if evm and evm.cpi else None,
                "spi": float(evm.spi) if evm and evm.spi else None,
            },
        })

    items.sort(key=lambda x: x["scoring"]["total_score"] or 0, reverse=True)
    for i, item in enumerate(items, 1):
        item["rank"] = i

    return items
