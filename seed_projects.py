"""
Seed script — adds 6 realistic example projects with WBS tasks, EVM, and financial scoring.
Run: python seed_projects.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from datetime import date, timedelta
from app.database import SessionLocal
from app.models.project import (
    Project, ProjectStatus, ProjectSelectionMetrics,
    ProjectScoring, ProjectMemberDetail
)
from app.models.evm import WBSTask, EVMMetrics
from app.models.user import User, UserRole

db = SessionLocal()

ADMIN_ID = db.query(User).filter(User.username == "admin").first().user_id
PM_ID    = db.query(User).filter(User.role == UserRole.PROJECT_MANAGER).first()
PM_ID    = PM_ID.user_id if PM_ID else ADMIN_ID


def make_project(name, desc, budget, start, end, status, is_selected=False):
    p = Project(
        name=name,
        description=desc,
        budget=budget,
        start_date=start,
        end_date=end,
        status=status,
        created_by=ADMIN_ID,
        is_selected=is_selected,
    )
    db.add(p)
    db.flush()
    return p


def make_task(project_id, name, desc, pv, ac, pct, order, status=None):
    if status is None:
        if pct == 100:
            status = "Completed"
        elif pct > 0:
            status = "In Progress"
        else:
            status = "Not Started"
    t = WBSTask(
        project_id=project_id,
        task_name=name,
        description=desc,
        planned_value=pv,
        actual_cost=ac,
        percent_complete=pct,
        order_index=order,
        status=status,
    )
    db.add(t)
    return t


def recalc_evm(project_id):
    tasks = db.query(WBSTask).filter(WBSTask.project_id == project_id).all()
    if not tasks:
        return
    bac = sum(float(t.planned_value or 0) for t in tasks)
    pv  = bac
    ev  = sum(float(t.planned_value or 0) * float(t.percent_complete or 0) / 100 for t in tasks)
    ac  = sum(float(t.actual_cost or 0) for t in tasks)
    cv  = ev - ac
    sv  = ev - pv
    cpi = ev / ac if ac > 0 else 1.0
    spi = ev / pv if pv > 0 else 1.0
    eac = bac / cpi if cpi > 0 else bac
    etc = eac - ac
    vac = bac - eac

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
    evm.is_over_budget     = cpi < 0.9
    evm.is_behind_schedule = spi < 0.9


def make_metrics(project_id, invest, rev, cost, life):
    annual_profit = rev - cost
    total_benefit = annual_profit * life
    roi = (total_benefit - invest) / invest * 100
    total_cost = invest + cost * life
    bcr = (rev * life) / total_cost if total_cost > 0 else 0
    payback = invest / annual_profit if annual_profit > 0 else 99.0
    npv = -invest
    for yr in range(1, life + 1):
        npv += annual_profit / (1.10 ** yr)

    roi     = round(roi,  4)
    bcr     = round(bcr,  4)
    payback = round(payback, 4)
    npv     = round(npv, 2)

    m = db.query(ProjectSelectionMetrics).filter_by(project_id=project_id).first()
    if not m:
        m = ProjectSelectionMetrics(project_id=project_id)
        db.add(m)

    m.initial_investment = invest
    m.annual_revenue     = rev
    m.annual_cost        = cost
    m.project_lifetime   = life
    m.roi            = roi
    m.bcr            = bcr
    m.payback_period = payback
    m.npv            = npv

    # Scoring
    roi_score     = min(roi / 200 * 40, 40) if roi > 0 else 0
    bcr_score     = min((bcr - 1) / 2 * 30, 30) if bcr > 1 else 0
    payback_score = max((10 - payback) / 10 * 20, 0) if payback < 10 else 0
    npv_score     = 10.0 if npv > 0 else 0.0
    total_score   = round(roi_score + bcr_score + payback_score + npv_score, 2)

    s = db.query(ProjectScoring).filter_by(project_id=project_id).first()
    if not s:
        s = ProjectScoring(project_id=project_id)
        db.add(s)

    s.total_score   = total_score
    s.roi_score     = round(roi_score, 2)
    s.bcr_score     = round(bcr_score, 2)
    s.payback_score = round(payback_score, 2)
    s.eva_score     = npv_score


# ── Remove old demo projects if any ──────────────────────────────────────────
demo_names = [
    "Smart City Traffic Management System",
    "Hospital Information System Upgrade",
    "Renewable Energy Grid Integration",
    "E-Government Digital Transformation",
    "National Education Platform",
    "Port Logistics Automation",
]
for name in demo_names:
    existing = db.query(Project).filter(Project.name == name).first()
    if existing:
        db.delete(existing)
db.flush()


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 1 — Smart City Traffic Management System
#  Status: In Progress · On budget · On schedule
# ═══════════════════════════════════════════════════════════════════════
p1 = make_project(
    "Smart City Traffic Management System",
    "AI-powered adaptive traffic signal control across 120 intersections, reducing congestion by 35% and cutting average commute time by 18 minutes.",
    4_800_000,
    date(2024, 3, 1),
    date(2026, 8, 31),
    ProjectStatus.IN_PROGRESS,
)
make_task(p1.project_id, "Requirements & Stakeholder Analysis", "Gather functional and non-functional requirements from municipality, traffic police, and citizens.", 280_000, 275_000, 100, 1)
make_task(p1.project_id, "Infrastructure Site Survey", "Field survey of 120 intersections; identify sensor placement and network coverage gaps.", 190_000, 188_000, 100, 2)
make_task(p1.project_id, "AI Traffic Control Engine Development", "Train and validate adaptive signal control AI using 2 years of historical traffic data.", 920_000, 905_000, 100, 3)
make_task(p1.project_id, "Sensor & IoT Hardware Procurement", "Procure radar sensors, edge compute units, fibre optic cables, and PoE switches.", 850_000, 862_000, 100, 4)
make_task(p1.project_id, "Network Infrastructure Deployment", "Install fibre backbone and wireless fallback links at all 120 sites.", 520_000, 498_000, 80, 5)
make_task(p1.project_id, "Control Centre Integration", "Connect field units to central NOC dashboard; real-time monitoring and override capability.", 430_000, 210_000, 45, 6)
make_task(p1.project_id, "Pilot Corridor Testing (10 intersections)", "End-to-end live testing on Ring Road pilot corridor; KPI measurement.", 310_000, 0, 0, 7)
make_task(p1.project_id, "City-Wide Rollout & Go-Live", "Phased rollout across all 120 intersections with handover training.", 620_000, 0, 0, 8)
make_task(p1.project_id, "Post-Deployment Monitoring & Optimisation", "6-month performance review and AI model retraining based on live data.", 180_000, 0, 0, 9)
recalc_evm(p1.project_id)
make_metrics(p1.project_id, invest=2_000_000, rev=1_200_000, cost=350_000, life=10)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 2 — Hospital Information System Upgrade
#  Status: In Progress · Over budget (CPI ~0.88)
# ═══════════════════════════════════════════════════════════════════════
p2 = make_project(
    "Hospital Information System Upgrade",
    "Replace 7 legacy HIS modules with integrated cloud-native platform covering EMR, lab, pharmacy, billing, and appointment scheduling across 3 regional hospitals.",
    6_200_000,
    date(2023, 9, 1),
    date(2025, 12, 31),
    ProjectStatus.IN_PROGRESS,
)
make_task(p2.project_id, "Legacy System Audit & Data Migration Plan", "Full audit of existing HIS data structures; define migration strategy and rollback plan.", 380_000, 410_000, 100, 1)
make_task(p2.project_id, "EMR Module Development", "Build electronic medical records module with HL7 FHIR compliance and role-based access.", 1_100_000, 1_240_000, 100, 2)
make_task(p2.project_id, "Laboratory Information System", "Develop LIS with barcode tracking, instrument integration, and result validation workflows.", 720_000, 780_000, 100, 3)
make_task(p2.project_id, "Pharmacy & Inventory Management", "Smart pharmacy system with drug interaction alerts, auto-reorder, and dispensing workflow.", 580_000, 645_000, 95, 4)
make_task(p2.project_id, "Billing & Insurance Integration", "Claims processing with NPHIES integration for Saudi national insurance scheme.", 490_000, 520_000, 85, 5)
make_task(p2.project_id, "Appointment & Scheduling Portal", "Patient-facing web and mobile portal with SMS/WhatsApp reminders.", 360_000, 290_000, 60, 6)
make_task(p2.project_id, "Staff Training Programme", "Train 800+ clinical and admin staff across 3 hospitals on new system.", 280_000, 120_000, 30, 7)
make_task(p2.project_id, "Data Migration & UAT", "Migrate 10 years of historical patient data; user acceptance testing.", 820_000, 0, 0, 8)
make_task(p2.project_id, "Go-Live & Hypercare Support", "Phased go-live with 90-day hypercare support team on-site.", 470_000, 0, 0, 9)
recalc_evm(p2.project_id)
make_metrics(p2.project_id, invest=3_500_000, rev=2_400_000, cost=600_000, life=8)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 3 — Renewable Energy Grid Integration
#  Status: Selected · Large scale · Great financials
# ═══════════════════════════════════════════════════════════════════════
p3 = make_project(
    "Renewable Energy Grid Integration",
    "Integration of 500 MW solar and 200 MW wind capacity into the national grid with battery storage and SCADA upgrades across the Western Region.",
    18_500_000,
    date(2025, 1, 1),
    date(2028, 6, 30),
    ProjectStatus.SELECTED,
    is_selected=True,
)
make_task(p3.project_id, "Feasibility Study & Grid Impact Assessment", "Model grid stability under full renewable load; identify upgrade requirements.", 650_000, 648_000, 100, 1)
make_task(p3.project_id, "Regulatory Approval & Permits", "Obtain NOCS and environmental approvals from SEC, ECRA, and Ministry of Energy.", 220_000, 215_000, 100, 2)
make_task(p3.project_id, "Solar Farm EPC — Phase 1 (250 MW)", "Engineering, procurement, and construction of first 250 MW solar cluster.", 5_800_000, 4_100_000, 65, 3)
make_task(p3.project_id, "Wind Farm EPC (200 MW)", "Construction of 80 wind turbines with foundation, cabling, and collection substation.", 4_200_000, 1_800_000, 35, 4)
make_task(p3.project_id, "Battery Energy Storage System (200 MWh)", "Procure and commission grid-scale BESS for peak-shaving and frequency regulation.", 3_100_000, 0, 0, 5)
make_task(p3.project_id, "SCADA & Energy Management System", "Upgrade national SCADA to support variable renewable generation dispatch.", 1_400_000, 0, 0, 6)
make_task(p3.project_id, "Transmission Line Upgrades (380 kV)", "Upgrade 140 km of transmission corridors to handle increased renewable export.", 2_600_000, 0, 0, 7)
make_task(p3.project_id, "Solar Farm EPC — Phase 2 (250 MW)", "Second solar cluster construction and commissioning.", 5_800_000, 0, 0, 8)
make_task(p3.project_id, "Grid Integration Testing & Commissioning", "Full system testing, protection relay coordination, and black-start capability verification.", 480_000, 0, 0, 9)
recalc_evm(p3.project_id)
make_metrics(p3.project_id, invest=8_000_000, rev=6_500_000, cost=800_000, life=20)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 4 — E-Government Digital Transformation
#  Status: Completed · Finished on time and under budget
# ═══════════════════════════════════════════════════════════════════════
p4 = make_project(
    "E-Government Digital Transformation",
    "Digitalise 240 government services across 14 ministries onto a unified citizen portal, reducing average service delivery time from 12 days to under 4 hours.",
    3_400_000,
    date(2022, 6, 1),
    date(2024, 5, 31),
    ProjectStatus.COMPLETED,
)
make_task(p4.project_id, "Service Inventory & Prioritisation", "Catalogue all 240 services; score by citizen impact and digitisation complexity.", 180_000, 172_000, 100, 1)
make_task(p4.project_id, "National Identity API Integration", "Connect citizen portal to NIC and Absher for digital identity verification.", 290_000, 281_000, 100, 2)
make_task(p4.project_id, "Payment Gateway Integration", "Integrate SADAD, STC Pay, and Mada for seamless fee collection.", 240_000, 235_000, 100, 3)
make_task(p4.project_id, "Ministry Portal Development (Batch 1 — 7 ministries)", "Build and deploy department portals for MOI, MOH, MOE, MOF, MISA, MOJ, MOT.", 840_000, 812_000, 100, 4)
make_task(p4.project_id, "Ministry Portal Development (Batch 2 — 7 ministries)", "Second batch covering MOMRA, MWE, MCIT, MCI, MFA, MND, and Presidency.", 840_000, 798_000, 100, 5)
make_task(p4.project_id, "Arabic NLP Chatbot for Citizen Support", "AI assistant handling 80% of common service enquiries in Arabic and English.", 320_000, 308_000, 100, 6)
make_task(p4.project_id, "Accessibility & Mobile App (iOS + Android)", "WCAG 2.1 AA compliant design; native mobile apps for iOS and Android.", 280_000, 261_000, 100, 7)
make_task(p4.project_id, "Security Audit & Penetration Testing", "ISO 27001 assessment, OWASP pen testing, and NCA Essential Cybersecurity Controls.", 190_000, 183_000, 100, 8)
make_task(p4.project_id, "Citizen Awareness Campaign & Go-Live", "National media campaign; onboarding training for government staff.", 220_000, 198_000, 100, 9)
recalc_evm(p4.project_id)
make_metrics(p4.project_id, invest=1_500_000, rev=2_200_000, cost=280_000, life=7)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 5 — National Education Platform
#  Status: In Progress · Behind schedule (SPI ~0.82)
# ═══════════════════════════════════════════════════════════════════════
p5 = make_project(
    "National Education Platform",
    "Unified K-12 learning management system serving 6.2 million students, 420,000 teachers, and 21,000 schools with personalised AI-driven learning paths.",
    5_600_000,
    date(2024, 8, 1),
    date(2026, 7, 31),
    ProjectStatus.IN_PROGRESS,
)
make_task(p5.project_id, "Platform Architecture Design", "Define microservices architecture, data model, API contract, and cloud infrastructure blueprint.", 300_000, 298_000, 100, 1)
make_task(p5.project_id, "Core LMS Engine", "Build assignment, grading, attendance, and curriculum management core modules.", 880_000, 870_000, 100, 2)
make_task(p5.project_id, "AI Personalised Learning Engine", "Develop adaptive learning algorithms based on student performance and engagement data.", 720_000, 490_000, 50, 3)
make_task(p5.project_id, "Content Repository & OER Library", "Build repository for 85,000 curriculum-aligned digital resources in Arabic.", 460_000, 280_000, 35, 4)
make_task(p5.project_id, "Video Streaming & Virtual Classroom", "Integrate live and recorded lecture delivery with bandwidth optimisation for rural schools.", 380_000, 195_000, 25, 5)
make_task(p5.project_id, "Teacher Dashboard & Analytics", "Professional development tracking, class performance analytics, and lesson planning tools.", 340_000, 80_000, 10, 6)
make_task(p5.project_id, "Parent Engagement Portal", "Real-time progress visibility, messaging with teachers, and attendance notifications for parents.", 260_000, 0, 0, 7)
make_task(p5.project_id, "National Rollout — Pilot (500 schools)", "Controlled rollout to 500 schools; performance and adoption measurement.", 680_000, 0, 0, 8)
make_task(p5.project_id, "Full National Rollout (21,000 schools)", "Complete system deployment with offline-sync capability for low-connectivity regions.", 1_580_000, 0, 0, 9)
recalc_evm(p5.project_id)
make_metrics(p5.project_id, invest=2_800_000, rev=1_800_000, cost=420_000, life=12)


# ═══════════════════════════════════════════════════════════════════════
#  PROJECT 6 — Port Logistics Automation
#  Status: Candidate · Planning stage · Strong ROI
# ═══════════════════════════════════════════════════════════════════════
p6 = make_project(
    "Port Logistics Automation",
    "Deploy automated container handling systems — AGVs, automated cranes, and AI port operating system — at Jeddah Islamic Port to increase throughput by 60%.",
    12_300_000,
    date(2025, 10, 1),
    date(2028, 3, 31),
    ProjectStatus.CANDIDATE,
)
make_task(p6.project_id, "Port Operational Analysis & Simulation", "Discrete-event simulation of current port operations; identify bottlenecks and automation ROI.", 420_000, 418_000, 100, 1)
make_task(p6.project_id, "Technology Selection & Vendor RFP", "Evaluate AGV, ARMG, and port OS vendors; finalise procurement strategy.", 280_000, 271_000, 100, 2)
make_task(p6.project_id, "Civil & Infrastructure Works", "Prepare quay extensions, power infrastructure, and AGV guideway installation.", 3_800_000, 850_000, 20, 3)
make_task(p6.project_id, "Automated Rail-Mounted Gantry Cranes (8 units)", "Supply and install 8 ARMG cranes with automated spreader and anti-collision systems.", 2_900_000, 0, 0, 4)
make_task(p6.project_id, "Automated Guided Vehicles (32 units)", "Procure and commission 32 battery-electric AGVs with fleet management integration.", 1_800_000, 0, 0, 5)
make_task(p6.project_id, "Port Operating System (POS) Development", "AI-powered terminal operating system for real-time berth, yard, and gate management.", 1_500_000, 0, 0, 6)
make_task(p6.project_id, "System Integration & Digital Twin", "Integrate POS with customs, shipping lines, and inland freight; build digital twin for planning.", 920_000, 0, 0, 7)
make_task(p6.project_id, "Operator Training & Parallel Running", "Train 300 port operators; run automated and manual systems in parallel for 3 months.", 380_000, 0, 0, 8)
make_task(p6.project_id, "Full Commissioning & Performance Acceptance", "Verify throughput KPIs; formal handover to port authority.", 300_000, 0, 0, 9)
recalc_evm(p6.project_id)
make_metrics(p6.project_id, invest=5_500_000, rev=5_200_000, cost=700_000, life=15)


db.commit()
print("6 projects seeded successfully:")
for p in [p1, p2, p3, p4, p5, p6]:
    evm = db.query(EVMMetrics).filter_by(project_id=p.project_id).first()
    print(f"  [{p.project_id}] {p.name}")
    print(f"       Budget: {float(p.budget):,.0f} SAR | Status: {p.status.value}")
    if evm:
        print(f"       EVM: CPI={float(evm.cpi):.3f} SPI={float(evm.spi):.3f} EAC={float(evm.eac):,.0f}")

db.close()
