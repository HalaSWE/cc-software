"""
Reports Routes — Sprint 6
Export project data as CSV
"""
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project, ProjectSelectionMetrics
from app.models.evm import WBSTask, EVMMetrics
from app.models.user import User
from app.utils.auth import require_any, visible_project_ids, check_project_access

router = APIRouter(prefix="/api/reports", tags=["📄 Reports"])

@router.get("/dashboard/csv", summary="Export dashboard data as CSV")
def export_dashboard_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Project ID", "Name", "Budget", "Status", "Is Selected",
                     "CPI", "SPI", "EV", "AC", "EAC", "BAC",
                     "Over Budget", "Behind Schedule"])

    for p in projects:
        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        writer.writerow([
            p.project_id, p.name, p.budget, p.status.value, p.is_selected,
            round(evm.cpi, 4) if evm else "",
            round(evm.spi, 4) if evm else "",
            round(evm.ev, 2)  if evm else "",
            round(evm.ac, 2)  if evm else "",
            round(evm.eac, 2) if evm else "",
            round(evm.bac, 2) if evm else "",
            evm.is_over_budget       if evm else "",
            evm.is_behind_schedule   if evm else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cc_dashboard_report.csv"}
    )

@router.get("/project/{project_id}/wbs/csv", summary="Export WBS tasks as CSV")
def export_wbs_csv(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    check_project_access(project_id, current_user, db)
    tasks = db.query(WBSTask).filter(WBSTask.project_id == project_id).order_by(WBSTask.order_index).all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["#", "Task Name", "Description", "Planned Value (PV)", "Actual Cost (AC)",
                     "% Complete", "Earned Value (EV)", "Status"])

    for i, t in enumerate(tasks, 1):
        ev = t.planned_value * (t.percent_complete or 0) / 100
        writer.writerow([i, t.task_name, t.description or "", t.planned_value,
                         t.actual_cost or 0, t.percent_complete or 0, round(ev, 2), t.status])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=wbs_project_{project_id}.csv"}
    )

@router.get("/selection/csv", summary="Export project selection ranking as CSV")
def export_selection_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any),
):
    ids = visible_project_ids(current_user, db)
    q = db.query(Project)
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Rank", "Project", "Budget", "Is Selected",
                     "Initial Investment", "Annual Revenue", "Annual Cost", "Lifetime (yrs)",
                     "ROI %", "BCR", "Payback Period (yrs)", "NPV"])

    from app.models.project import ProjectScoring
    ranked = []
    for p in projects:
        m = db.query(ProjectSelectionMetrics).filter_by(project_id=p.project_id).first()
        s = db.query(ProjectScoring).filter_by(project_id=p.project_id).first()
        ranked.append((p, m, s))

    ranked.sort(key=lambda x: (x[2].total_score if x[2] else 0), reverse=True)

    for rank, (p, m, s) in enumerate(ranked, 1):
        writer.writerow([
            rank, p.name, p.budget, p.is_selected,
            m.initial_investment if m else "", m.annual_revenue if m else "",
            m.annual_cost if m else "", m.project_lifetime if m else "",
            round(m.roi, 2) if m else "", round(m.bcr, 2) if m else "",
            round(m.payback_period, 2) if m else "", round(m.npv, 2) if m else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cc_selection_report.csv"}
    )
