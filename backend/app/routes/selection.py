"""
Project Selection & Scoring Routes — v2.0
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectSelectionMetrics, ProjectScoring, ProjectStatus
from app.models.user import User
from app.schemas import (SelectionMetricsCreate, SelectionMetricsResponse,
                         ProjectScoringResponse, ProjectRankingItem, MessageResponse)
from app.utils.auth import require_pm, require_any, check_project_access, visible_project_ids
from app.utils.notify import notify

router = APIRouter(prefix="/api/projects", tags=["📊 Project Selection & Scoring"])

DISCOUNT_RATE = 0.10

def _calculate_metrics(data: SelectionMetricsCreate):
    annual_profit = data.annual_revenue - data.annual_cost
    total_benefit = annual_profit * data.project_lifetime

    roi = (total_benefit - data.initial_investment) / data.initial_investment * 100

    total_cost = data.initial_investment + (data.annual_cost * data.project_lifetime)
    bcr = (data.annual_revenue * data.project_lifetime) / total_cost if total_cost > 0 else 0

    payback = data.initial_investment / annual_profit if annual_profit > 0 else float('inf')

    npv = -data.initial_investment
    for year in range(1, data.project_lifetime + 1):
        npv += annual_profit / ((1 + DISCOUNT_RATE) ** year)

    return round(roi, 4), round(bcr, 4), round(payback, 4), round(npv, 2)

def _compute_score(roi, bcr, payback, npv) -> float:
    roi_score     = min(roi / 200 * 40, 40) if roi > 0 else 0
    bcr_score     = min((bcr - 1) / 2 * 30, 30) if bcr > 1 else 0
    payback_score = max((10 - payback) / 10 * 20, 0) if payback < 10 else 0
    npv_score     = 10 if npv > 0 else 0
    return round(roi_score + bcr_score + payback_score + npv_score, 2)

@router.post("/{project_id}/metrics", response_model=SelectionMetricsResponse, status_code=201,
             summary="Enter financial data — auto-calculates ROI, BCR, Payback, NPV")
def set_metrics(project_id: int, data: SelectionMetricsCreate,
                db: Session = Depends(get_db), current_user: User = Depends(require_pm)):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)

    roi, bcr, payback, npv = _calculate_metrics(data)

    metrics = db.query(ProjectSelectionMetrics).filter_by(project_id=project_id).first()
    if not metrics:
        metrics = ProjectSelectionMetrics(project_id=project_id)
        db.add(metrics)

    metrics.initial_investment = data.initial_investment
    metrics.annual_revenue     = data.annual_revenue
    metrics.annual_cost        = data.annual_cost
    metrics.project_lifetime   = data.project_lifetime
    metrics.roi            = roi
    metrics.bcr            = bcr
    metrics.payback_period = payback
    metrics.npv            = npv

    score = _compute_score(roi, bcr, payback, npv)
    scoring = db.query(ProjectScoring).filter_by(project_id=project_id).first()
    if not scoring:
        scoring = ProjectScoring(project_id=project_id)
        db.add(scoring)

    scoring.total_score   = score
    scoring.roi_score     = round(min(roi / 200 * 40, 40) if roi > 0 else 0, 2)
    scoring.bcr_score     = round(min((bcr - 1) / 2 * 30, 30) if bcr > 1 else 0, 2)
    scoring.payback_score = round(max((10 - payback) / 10 * 20, 0) if payback < 10 else 0, 2)
    scoring.eva_score     = 10.0 if npv > 0 else 0.0

    db.commit()
    db.refresh(metrics)
    return metrics

@router.get("/{project_id}/metrics", response_model=SelectionMetricsResponse,
            summary="Get financial metrics for a project")
def get_metrics(project_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    metrics = db.query(ProjectSelectionMetrics).filter_by(project_id=project_id).first()
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics — enter financial data first")
    return metrics

@router.get("/{project_id}/scoring", response_model=ProjectScoringResponse,
            summary="Get scoring breakdown for a project")
def get_scoring(project_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(require_any)):
    check_project_access(project_id, current_user, db)
    scoring = db.query(ProjectScoring).filter_by(project_id=project_id).first()
    if not scoring:
        raise HTTPException(status_code=404, detail="No scoring — set metrics first")
    return scoring

@router.get("/selection/ranking", response_model=List[ProjectRankingItem],
            tags=["📊 Project Selection & Scoring"],
            summary="Rank all projects by composite score")
def get_ranking(db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    items = []
    for p in projects:
        m = db.query(ProjectSelectionMetrics).filter_by(project_id=p.project_id).first()
        s = db.query(ProjectScoring).filter_by(project_id=p.project_id).first()
        items.append(ProjectRankingItem(
            project_id     = p.project_id,
            name           = p.name,
            budget         = float(p.budget),
            total_score    = float(s.total_score)   if s and s.total_score   else None,
            roi            = float(m.roi)            if m and m.roi            else None,
            bcr            = float(m.bcr)            if m and m.bcr            else None,
            payback_period = float(m.payback_period) if m and m.payback_period else None,
            npv            = float(m.npv)            if m and m.npv            else None,
            priority_rank  = s.priority_rank         if s else None,
            is_selected    = p.is_selected,
        ))

    items.sort(key=lambda x: x.total_score or 0, reverse=True)
    for rank, item in enumerate(items, 1):
        item.priority_rank = rank
        s = db.query(ProjectScoring).filter_by(project_id=item.project_id).first()
        if s:
            s.priority_rank = rank
    db.commit()
    return items

@router.post("/selection/select/{project_id}", response_model=MessageResponse,
             tags=["📊 Project Selection & Scoring"],
             summary="Mark project as selected")
def select_project(project_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(require_pm)):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.query(Project).update({"is_selected": False})
    project.is_selected = True
    project.status = ProjectStatus.SELECTED
    db.commit()
    return MessageResponse(message=f"Project '{project.name}' selected ✅")
