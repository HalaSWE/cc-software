"""
PDF Reports — Professional project reports using ReportLab
"""
import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.database import get_db
from app.models.project import Project, ProjectSelectionMetrics, ProjectScoring
from app.models.evm import WBSTask, EVMMetrics
from app.models.user import User
from app.utils.auth import require_any, check_project_access, visible_project_ids

router = APIRouter(prefix="/api/pdf", tags=["📑 PDF Reports"])

DARK   = colors.HexColor("#0d1220")
NAVY   = colors.HexColor("#111827")
BLUE   = colors.HexColor("#3b82f6")
GREEN  = colors.HexColor("#10b981")
AMBER  = colors.HexColor("#f59e0b")
ROSE   = colors.HexColor("#f43f5e")
GRAY   = colors.HexColor("#94a3b8")
LGRAY  = colors.HexColor("#1a2235")
WHITE  = colors.white

def _fmt(n, dec=2):
    if n is None: return "—"
    try:    return f"{float(n):,.{dec}f}"
    except: return "—"

def _fmtK(n):
    if n is None: return "—"
    v = float(n)
    if abs(v) >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:     return f"{v/1_000:.0f}K"
    return f"{v:.0f}"

def _status_color(status: str):
    m = {"In Progress": BLUE, "Completed": GREEN, "Cancelled": ROSE,
         "Selected": colors.HexColor("#8b5cf6"), "Pending": GRAY}
    return m.get(status, GRAY)

def _build_pdf_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold",
                                fontSize=22, textColor=WHITE, spaceAfter=4,
                                alignment=TA_LEFT),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica",
                                   fontSize=10, textColor=GRAY, spaceAfter=2,
                                   alignment=TA_LEFT),
        "section": ParagraphStyle("section", fontName="Helvetica-Bold",
                                  fontSize=12, textColor=BLUE, spaceBefore=14,
                                  spaceAfter=6, alignment=TA_LEFT),
        "body": ParagraphStyle("body", fontName="Helvetica",
                               fontSize=9, textColor=colors.HexColor("#cbd5e1"),
                               spaceAfter=4),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold",
                                fontSize=8, textColor=GRAY),
        "value": ParagraphStyle("value", fontName="Helvetica-Bold",
                                fontSize=14, textColor=WHITE),
        "mono": ParagraphStyle("mono", fontName="Courier",
                               fontSize=8, textColor=GRAY),
    }

def _kpi_table(kpis):
    """Build a row of KPI boxes: [(label, value, color), ...]"""
    labels = [Paragraph(k[0], ParagraphStyle("kl", fontName="Helvetica",
              fontSize=7, textColor=GRAY, alignment=TA_CENTER)) for k in kpis]
    values = [Paragraph(k[1], ParagraphStyle("kv", fontName="Helvetica-Bold",
              fontSize=13, textColor=k[2], alignment=TA_CENTER)) for k in kpis]

    t = Table([labels, values], colWidths=[3.8*cm]*len(kpis))
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), LGRAY),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[LGRAY, LGRAY]),
        ("BOX",          (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
        ("INNERGRID",    (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), 4),
    ]))
    return t

def _section_header(text, styles):
    return [Paragraph(text, styles["section"]),
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1a2235"), spaceAfter=6)]

@router.get("/project/{project_id}", summary="Full PDF report for a single project")
def project_pdf(project_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(require_any)):
    p = db.query(Project).filter(Project.project_id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_access(project_id, current_user, db)

    evm     = db.query(EVMMetrics).filter_by(project_id=project_id).first()
    metrics = db.query(ProjectSelectionMetrics).filter_by(project_id=project_id).first()
    scoring = db.query(ProjectScoring).filter_by(project_id=project_id).first()
    tasks   = db.query(WBSTask).filter(WBSTask.project_id == project_id).order_by(WBSTask.order_index).all()

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.8*cm, rightMargin=1.8*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = _build_pdf_styles()
    story  = []

    header_data = [[
        Paragraph(p.name, styles["title"]),
        Paragraph(f"Generated {date.today().strftime('%B %d, %Y')}", styles["subtitle"]),
    ]]
    header_tbl = Table(header_data, colWidths=[13*cm, 4*cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0), (1,0), "RIGHT"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    story += _section_header("📊 Project Overview", styles)
    cpi_color = GREEN if evm and float(evm.cpi or 1) >= 0.9 else ROSE
    spi_color = GREEN if evm and float(evm.spi or 1) >= 0.9 else ROSE
    kpis = [
        ("STATUS",   p.status.value,         _status_color(p.status.value)),
        ("BUDGET",   _fmtK(p.budget)+" SAR", WHITE),
        ("CPI",      _fmt(evm.cpi, 3) if evm else "—",  cpi_color),
        ("SPI",      _fmt(evm.spi, 3) if evm else "—",  spi_color),
    ]
    story.append(_kpi_table(kpis))
    story.append(Spacer(1, 0.3*cm))

    info_data = [
        ["Description", p.description or "—"],
        ["Start Date",  str(p.start_date) if p.start_date else "—"],
        ["End Date",    str(p.end_date)   if p.end_date   else "—"],
        ["Selected",    "Yes ★" if p.is_selected else "No"],
    ]
    info_tbl = Table(info_data, colWidths=[4*cm, 12.8*cm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LGRAY),
        ("BACKGROUND",    (1,0), (1,-1), NAVY),
        ("TEXTCOLOR",     (0,0), (0,-1), GRAY),
        ("TEXTCOLOR",     (1,0), (1,-1), WHITE),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#1f2b40")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
    ]))
    story.append(info_tbl)

    if evm:
        story += _section_header("📈 Earned Value Management (EVM)", styles)
        evm_kpis = [
            ("BAC",  _fmtK(evm.bac),  WHITE),
            ("PV",   _fmtK(evm.pv),   WHITE),
            ("EV",   _fmtK(evm.ev),   GREEN),
            ("AC",   _fmtK(evm.ac),   AMBER),
            ("EAC",  _fmtK(evm.eac),  WHITE),
            ("ETC",  _fmtK(evm.etc),  WHITE),
        ]
        story.append(_kpi_table(evm_kpis))
        story.append(Spacer(1, 0.2*cm))

        variance_data = [
            ["Cost Variance (CV)",     _fmt(evm.cv), "Positive = under budget"],
            ["Schedule Variance (SV)", _fmt(evm.sv), "Positive = ahead of schedule"],
            ["VAC (Variance at Compl.)",_fmt(evm.vac),"Positive = will finish under budget"],
        ]
        var_tbl = Table([["Metric","Value","Interpretation"]] + variance_data,
                        colWidths=[5.5*cm, 3*cm, 8.3*cm])
        var_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("BACKGROUND",    (0,1), (-1,-1), NAVY),
            ("TEXTCOLOR",     (0,1), (-1,-1), WHITE),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [NAVY, LGRAY]),
            ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#1f2b40")),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(var_tbl)

    if tasks:
        story += _section_header(f"📋 WBS Tasks ({len(tasks)} total)", styles)
        task_rows = [["#", "Task Name", "PV", "AC", "EV", "% Done", "Status"]]
        for i, t in enumerate(tasks, 1):
            ev = float(t.planned_value or 0) * float(t.percent_complete or 0) / 100
            task_rows.append([
                str(i),
                t.task_name[:40],
                _fmtK(t.planned_value),
                _fmtK(t.actual_cost),
                _fmtK(ev),
                f"{float(t.percent_complete or 0):.0f}%",
                t.status,
            ])
        task_tbl = Table(task_rows, colWidths=[0.8*cm, 5.5*cm, 2.2*cm, 2.2*cm, 2.2*cm, 1.8*cm, 2.5*cm])
        task_style = TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [NAVY, LGRAY]),
            ("TEXTCOLOR",     (0,1), (-1,-1), WHITE),
            ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#1f2b40")),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
            ("ALIGN",         (2,1), (-1,-1), "CENTER"),
        ])
        for i, t in enumerate(tasks, 1):
            if t.status == "Completed":
                task_style.add("TEXTCOLOR", (6,i), (6,i), GREEN)
            elif t.status == "In Progress":
                task_style.add("TEXTCOLOR", (6,i), (6,i), BLUE)
        task_tbl.setStyle(task_style)
        story.append(task_tbl)

    if metrics or scoring:
        story += _section_header("💰 Financial Analysis & Scoring", styles)
        fin_data = []
        if metrics:
            fin_data += [
                ["Initial Investment", _fmtK(metrics.initial_investment) + " SAR"],
                ["Annual Revenue",     _fmtK(metrics.annual_revenue)     + " SAR"],
                ["Annual Cost",        _fmtK(metrics.annual_cost)        + " SAR"],
                ["Project Lifetime",   str(metrics.project_lifetime)     + " years"],
                ["ROI",                _fmt(metrics.roi, 1)              + "%"],
                ["BCR",                _fmt(metrics.bcr, 3)],
                ["Payback Period",     _fmt(metrics.payback_period, 1)   + " years"],
                ["NPV",                _fmtK(metrics.npv)                + " SAR"],
            ]
        if scoring:
            fin_data.append(["Composite Score", f"{_fmt(scoring.total_score, 1)} / 100"])

        fin_tbl = Table(fin_data, colWidths=[6*cm, 10.8*cm])
        fin_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), LGRAY),
            ("BACKGROUND",    (1,0), (1,-1), NAVY),
            ("TEXTCOLOR",     (0,0), (0,-1), GRAY),
            ("TEXTCOLOR",     (1,0), (1,-1), WHITE),
            ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(1,0), (1,-1), [NAVY, LGRAY]),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#1f2b40")),
            ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
        ]))
        story.append(fin_tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LGRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"CC Software v2.0  ·  Generated by {current_user.username}  ·  {date.today()}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=7,
                       textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    filename = f"project_{project_id}_{p.name.replace(' ','_')[:30]}.pdf"
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/portfolio", summary="Portfolio summary PDF — all projects ranked")
def portfolio_pdf(db: Session = Depends(get_db), current_user: User = Depends(require_any)):
    ids = visible_project_ids(current_user, db)
    q = db.query(Project).order_by(Project.created_at.desc())
    if ids is not None:
        q = q.filter(Project.project_id.in_(ids))
    projects = q.all()
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=1.8*cm, rightMargin=1.8*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
    styles = _build_pdf_styles()
    story  = []

    header_data = [[Paragraph("CC Software — Portfolio Report", styles["title"]),
                    Paragraph(f"Generated {date.today().strftime('%B %d, %Y')}", styles["subtitle"])]]
    header_tbl = Table(header_data, colWidths=[13*cm, 4*cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING", (0,0), (-1,-1), 14), ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",(0,0), (-1,-1), 14), ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (1,0), (1,0), "RIGHT"),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.4*cm))

    total_budget = sum(float(p.budget or 0) for p in projects)
    selected     = sum(1 for p in projects if p.is_selected)
    all_evms     = db.query(EVMMetrics).all()
    avg_cpi = sum(float(e.cpi or 1) for e in all_evms) / len(all_evms) if all_evms else 1.0
    at_risk  = sum(1 for e in all_evms if float(e.cpi or 1) < 0.9 or float(e.spi or 1) < 0.9)

    story += _section_header("📊 Portfolio Summary", styles)
    story.append(_kpi_table([
        ("TOTAL PROJECTS", str(len(projects)), WHITE),
        ("TOTAL BUDGET",   _fmtK(total_budget)+" SAR", WHITE),
        ("SELECTED",       str(selected),  GREEN),
        ("AT RISK",        str(at_risk),   ROSE if at_risk else GREEN),
        ("AVG CPI",        f"{avg_cpi:.3f}", GREEN if avg_cpi >= 0.9 else ROSE),
    ]))
    story.append(Spacer(1, 0.4*cm))

    story += _section_header("📁 All Projects", styles)
    rows = [["#", "Project Name", "Status", "Budget", "CPI", "SPI", "Score"]]
    for i, p in enumerate(projects, 1):
        evm     = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        scoring = db.query(ProjectScoring).filter_by(project_id=p.project_id).first()
        rows.append([
            str(i),
            p.name[:32] + ("★" if p.is_selected else ""),
            p.status.value,
            _fmtK(p.budget),
            _fmt(evm.cpi, 3) if evm else "—",
            _fmt(evm.spi, 3) if evm else "—",
            _fmt(scoring.total_score, 1) if scoring else "—",
        ])

    tbl = Table(rows, colWidths=[0.8*cm, 5.8*cm, 2.5*cm, 2.5*cm, 1.8*cm, 1.8*cm, 1.6*cm])
    tbl_style = TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), BLUE),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [NAVY, LGRAY]),
        ("TEXTCOLOR",     (0,1), (-1,-1), WHITE),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#1f2b40")),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#1f2b40")),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ALIGN",         (3,1), (-1,-1), "CENTER"),
    ])
    for i, p in enumerate(projects, 1):
        evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
        if evm:
            if float(evm.cpi or 1) < 0.9: tbl_style.add("TEXTCOLOR", (4,i), (4,i), ROSE)
            else:                           tbl_style.add("TEXTCOLOR", (4,i), (4,i), GREEN)
            if float(evm.spi or 1) < 0.9: tbl_style.add("TEXTCOLOR", (5,i), (5,i), ROSE)
            else:                           tbl_style.add("TEXTCOLOR", (5,i), (5,i), GREEN)
    tbl.setStyle(tbl_style)
    story.append(tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LGRAY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"CC Software v2.0  ·  Generated by {current_user.username}  ·  {date.today()}",
        ParagraphStyle("footer", fontName="Helvetica", fontSize=7,
                       textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=cc_portfolio_report.pdf"})
