"""
Seed detailed WBS tasks + subtasks for projects 1, 2, 3
"""
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

from app.database import SessionLocal
from app.models.project import Project, ProjectSelectionMetrics, ProjectScoring
from app.models.evm import WBSTask, EVMMetrics, TaskStatus, Notification

db = SessionLocal()


def recalc(project_id):
    tasks = db.query(WBSTask).filter(WBSTask.project_id == project_id).all()
    if not tasks:
        return
    bac = sum(float(t.planned_value or 0) for t in tasks)
    pv  = bac
    ev  = sum(float(t.planned_value or 0) * float(t.percent_complete or 0) / 100 for t in tasks)
    ac  = sum(float(t.actual_cost or 0) for t in tasks)
    cpi = ev / ac if ac > 0 else 1.0
    spi = ev / pv if pv > 0 else 1.0
    eac = bac / cpi if cpi > 0 else bac
    etc = eac - ac
    cv  = ev - ac
    sv  = ev - pv
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
    db.commit()
    return evm


def add_task(project_id, name, desc, pv, ac, pct, order, parent_id=None):
    status = TaskStatus.COMPLETED.value if pct == 100 else (
             TaskStatus.IN_PROGRESS.value if pct > 0 else TaskStatus.NOT_STARTED.value)
    t = WBSTask(
        project_id=project_id,
        parent_task_id=parent_id,
        task_name=name,
        description=desc,
        planned_value=pv,
        actual_cost=ac,
        percent_complete=pct,
        order_index=order,
        status=status,
    )
    db.add(t)
    db.flush()
    return t.task_id


# ── Clear existing tasks for projects 1, 2, 3 ─────────────────────────────────
for pid in [1, 2, 3]:
    db.query(WBSTask).filter(WBSTask.project_id == pid).delete()
db.commit()

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT 1 — E-Commerce Platform (budget 150,000 SAR)
# ══════════════════════════════════════════════════════════════════════════════
p1 = 1
# Parent tasks
t = add_task(p1, "Requirements & Analysis",
    "Gather functional and non-functional requirements from stakeholders. Document user stories, "
    "define acceptance criteria, and create a detailed project scope document. Includes competitive "
    "analysis and market research for e-commerce features.",
    12000, 11800, 100, 1)
add_task(p1, "Stakeholder Interviews",
    "Conduct structured interviews with business owners, marketing, and end-users to capture needs.",
    4000, 3900, 100, 2, t)
add_task(p1, "Requirements Documentation",
    "Write formal SRS document covering all functional modules: catalog, cart, checkout, and admin.",
    4000, 3950, 100, 3, t)
add_task(p1, "Feasibility & Risk Analysis",
    "Assess technical feasibility, budget risks, and third-party integration constraints.",
    4000, 3950, 100, 4, t)

t = add_task(p1, "UI/UX Design",
    "Create wireframes, high-fidelity mockups, and interactive prototypes for all major flows. "
    "Includes mobile-responsive design for product listing, product detail, cart, and checkout pages. "
    "Conduct usability testing with 10 target users.",
    18000, 17500, 100, 5)
add_task(p1, "Wireframes & Prototypes",
    "Develop low-fidelity wireframes for all 12 key screens using Figma.",
    6000, 5800, 100, 6, t)
add_task(p1, "Visual Design System",
    "Build a consistent design system: typography, color palette, components, and icons.",
    6000, 5900, 100, 7, t)
add_task(p1, "Usability Testing",
    "Run moderated usability tests, collect feedback, and iterate on design.",
    6000, 5800, 100, 8, t)

t = add_task(p1, "Backend Development",
    "Build RESTful API services using Node.js and PostgreSQL. Implement product catalog, user "
    "authentication (JWT), order management, payment gateway integration (Stripe/Mada), and "
    "inventory sync. Target 99.9% uptime with Redis caching.",
    45000, 32000, 65, 9)
add_task(p1, "API Architecture & Auth",
    "Design API structure, implement JWT auth, role-based access control, and API versioning.",
    15000, 10500, 70, 10, t)
add_task(p1, "Product & Order Services",
    "Implement catalog CRUD, shopping cart, order placement, and order tracking endpoints.",
    15000, 11000, 65, 11, t)
add_task(p1, "Payment & Notifications",
    "Integrate Stripe/Mada payment gateway, implement webhook handlers, and email/SMS notifications.",
    15000, 10500, 60, 12, t)

t = add_task(p1, "Frontend Development",
    "Develop the React.js single-page application with server-side rendering (Next.js). "
    "Implement all user-facing pages: home, category browsing, product detail, cart, checkout, "
    "and user account dashboard. Ensure WCAG 2.1 accessibility compliance.",
    35000, 21000, 55, 13)
add_task(p1, "Core Pages & Navigation",
    "Build home page, category pages, search results, and navigation components.",
    12000, 7200, 60, 14, t)
add_task(p1, "Product & Cart Flows",
    "Implement product detail page, add-to-cart, wishlist, and checkout multi-step flow.",
    12000, 7100, 55, 15, t)
add_task(p1, "User Account & Dashboard",
    "Build user registration, login, profile management, and order history pages.",
    11000, 6700, 50, 16, t)

t = add_task(p1, "Testing & QA",
    "Execute comprehensive testing: unit tests (Jest), integration tests, end-to-end tests (Playwright), "
    "performance load testing (k6), and security penetration testing. Target 90%+ code coverage.",
    25000, 6000, 18, 17)
add_task(p1, "Unit & Integration Tests",
    "Write and run unit tests for all backend services and React components.",
    9000, 2200, 20, 18, t)
add_task(p1, "E2E & Performance Testing",
    "Automate end-to-end user journeys and run load tests simulating 1,000 concurrent users.",
    9000, 2100, 18, 19, t)
add_task(p1, "Security & UAT",
    "Conduct penetration testing, fix vulnerabilities, and run user acceptance testing sessions.",
    7000, 1700, 15, 20, t)

t = add_task(p1, "Deployment & DevOps",
    "Set up CI/CD pipeline (GitHub Actions), containerize application with Docker, deploy on AWS "
    "(ECS Fargate + RDS), configure CloudFront CDN, SSL certificates, and monitoring (Datadog).",
    15000, 1500, 8, 21)
add_task(p1, "Infrastructure & CI/CD",
    "Provision AWS infrastructure with Terraform, configure GitHub Actions pipeline.",
    5000, 800, 10, 22, t)
add_task(p1, "Containerization & Deployment",
    "Dockerize all services, push to ECR, deploy to ECS with auto-scaling.",
    5000, 400, 5, 23, t)
add_task(p1, "Monitoring & Handover",
    "Configure Datadog dashboards, alerting, runbooks, and deliver handover documentation.",
    5000, 300, 5, 24, t)

evm1 = recalc(p1)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT 2 — HR Management System (budget 95,000 SAR)
# ══════════════════════════════════════════════════════════════════════════════
p2 = 2

t = add_task(p2, "HR System Requirements",
    "Define comprehensive HR system requirements covering employee records, payroll, leave management, "
    "performance appraisal, and recruitment modules. Align with Saudi Labor Law and GOSI regulations.",
    10000, 9800, 100, 1)
add_task(p2, "Process Mapping",
    "Document existing HR workflows and identify automation opportunities across all departments.",
    3500, 3400, 100, 2, t)
add_task(p2, "Compliance & Legal Review",
    "Review all requirements against Saudi Labor Law, GOSI, and Nitaqat compliance requirements.",
    3500, 3450, 100, 3, t)
add_task(p2, "Technical Specification",
    "Write detailed technical spec for system architecture, integrations, and data migration plan.",
    3000, 2950, 100, 4, t)

t = add_task(p2, "Database Design & Architecture",
    "Design normalized PostgreSQL schema for employee master data, organizational hierarchy, "
    "payroll records, leave balances, and audit trails. Implement row-level security for HR data.",
    12000, 11200, 95, 5)
add_task(p2, "Entity-Relationship Design",
    "Create ERD covering 35+ tables including employees, departments, grades, and payroll.",
    4000, 3700, 95, 6, t)
add_task(p2, "Data Migration Plan",
    "Design ETL pipeline to migrate legacy HR data from Excel/old system to new database.",
    4000, 3800, 95, 7, t)
add_task(p2, "Security & Access Control",
    "Implement role-based access: HR Admin, Department Manager, Employee self-service.",
    4000, 3700, 95, 8, t)

t = add_task(p2, "Employee Management Module",
    "Build complete employee lifecycle management: onboarding, profile management, document storage, "
    "org chart visualization, and offboarding workflows. Supports Arabic and English interfaces.",
    18000, 13000, 68, 9)
add_task(p2, "Employee Records & Onboarding",
    "Implement employee profile CRUD, document upload (Iqama, contract, certificates), and onboarding checklist.",
    6000, 4400, 72, 10, t)
add_task(p2, "Org Chart & Departments",
    "Build interactive org chart, department management, and reporting-line configuration.",
    6000, 4300, 68, 11, t)
add_task(p2, "Leave & Attendance",
    "Implement leave request workflow, balance tracking, and attendance integration.",
    6000, 4300, 65, 12, t)

t = add_task(p2, "Payroll Processing Module",
    "Develop automated payroll calculation engine supporting basic salary, allowances, deductions, "
    "GOSI contributions, end-of-service calculation (ESB), and WPS-compliant payroll export.",
    20000, 11000, 52, 13)
add_task(p2, "Salary & Allowances Engine",
    "Build configurable payroll engine with salary grades, housing, transport, and custom allowances.",
    7000, 3900, 55, 14, t)
add_task(p2, "GOSI & Deductions",
    "Implement GOSI contribution calculator, income tax (for expats), and loan deductions.",
    7000, 3700, 50, 15, t)
add_task(p2, "Payslips & WPS Export",
    "Generate PDF payslips, produce WPS SIF file for Sadad bank transfers.",
    6000, 3400, 50, 16, t)

t = add_task(p2, "Performance & Recruitment",
    "Build 360-degree performance appraisal system with KPI tracking and automated review cycles. "
    "Includes recruitment pipeline: job posting, CV screening, interview scheduling, and offer management.",
    20000, 7000, 32, 17)
add_task(p2, "KPI & Appraisal Module",
    "Create KPI library, goal-setting workflows, mid-year and annual review forms.",
    7000, 2500, 35, 18, t)
add_task(p2, "Recruitment Pipeline",
    "Build job requisition, job board posting, applicant tracking, and interview scheduling.",
    7000, 2400, 30, 19, t)
add_task(p2, "Reports & Analytics",
    "Implement HR analytics dashboard: headcount, turnover rate, cost per hire, and payroll summary.",
    6000, 2100, 30, 20, t)

t = add_task(p2, "Testing, Training & Go-Live",
    "Conduct system testing, UAT with HR team, data migration validation, and user training. "
    "Execute phased go-live with parallel payroll run for 2 months.",
    15000, 2500, 12, 21)
add_task(p2, "System Testing & Bug Fixes",
    "Run full regression testing, fix critical bugs, and validate payroll calculations.",
    5000, 900, 15, 22, t)
add_task(p2, "User Training",
    "Deliver training sessions for HR admins, managers, and employee self-service portal.",
    5000, 800, 12, 23, t)
add_task(p2, "Go-Live & Hypercare",
    "Execute go-live plan, monitor system for 30 days, and provide dedicated support.",
    5000, 800, 8, 24, t)

evm2 = recalc(p2)

# ══════════════════════════════════════════════════════════════════════════════
# PROJECT 3 — Inventory Tracker (budget 60,000 SAR)
# ══════════════════════════════════════════════════════════════════════════════
p3 = 3

t = add_task(p3, "Inventory Requirements & Planning",
    "Define inventory management requirements: multi-warehouse support, barcode/RFID scanning, "
    "reorder-point automation, supplier management, and real-time stock visibility. "
    "Map integration points with existing ERP and accounting system.",
    7000, 6800, 100, 1)
add_task(p3, "Warehouse Process Analysis",
    "Document receiving, putaway, picking, packing, and dispatch workflows for 3 warehouses.",
    2500, 2400, 100, 2, t)
add_task(p3, "Integration Mapping",
    "Identify ERP, accounting, and e-commerce integration points and define API contracts.",
    2500, 2450, 100, 3, t)
add_task(p3, "System Specification",
    "Write technical specification covering data model, barcode schema, and reporting requirements.",
    2000, 1950, 100, 4, t)

t = add_task(p3, "Database & Backend Core",
    "Design and implement PostgreSQL schema for products, SKUs, warehouses, stock movements, "
    "and supplier records. Build FastAPI backend with real-time WebSocket stock updates.",
    14000, 10500, 72, 5)
add_task(p3, "Product & SKU Management",
    "Implement product catalog with multi-variant SKU support, categories, and UOM.",
    5000, 3700, 75, 6, t)
add_task(p3, "Stock Movement Engine",
    "Build stock-in, stock-out, transfer, and adjustment transaction engine with full audit trail.",
    5000, 3800, 75, 7, t)
add_task(p3, "Supplier & PO Management",
    "Implement supplier profiles, purchase order creation, and goods receipt matching.",
    4000, 3000, 65, 8, t)

t = add_task(p3, "Barcode & RFID Integration",
    "Integrate Zebra barcode scanner SDK and Impinj RFID reader. Build mobile scanning app "
    "(React Native) for warehouse staff. Support GS1-128 and QR code formats.",
    12000, 7000, 55, 9)
add_task(p3, "Scanner SDK Integration",
    "Integrate Zebra DataWedge SDK, implement scan-to-receive and scan-to-pick flows.",
    4500, 2600, 60, 10, t)
add_task(p3, "Mobile Scanning App",
    "Build React Native app for iOS/Android with offline mode and sync-on-connect.",
    4500, 2600, 55, 11, t)
add_task(p3, "RFID Bulk Counting",
    "Implement RFID tunnel reader integration for bulk stock counting and discrepancy alerts.",
    3000, 1800, 48, 12, t)

t = add_task(p3, "Reporting & Alerts Dashboard",
    "Build real-time inventory dashboard with low-stock alerts, slow-moving item analysis, "
    "stock valuation (FIFO/WAC), and supplier performance reports. Export to Excel and PDF.",
    12000, 5000, 38, 13)
add_task(p3, "Real-Time Dashboard",
    "Implement live stock level charts, expiry tracking, and warehouse utilization heatmap.",
    4500, 1900, 42, 14, t)
add_task(p3, "Automated Alerts & Reorder",
    "Configure reorder-point rules, auto-generate PO drafts, and send low-stock email/SMS alerts.",
    4000, 1700, 38, 15, t)
add_task(p3, "Financial & Supplier Reports",
    "Build stock valuation report (FIFO), dead-stock analysis, and supplier on-time delivery scorecard.",
    3500, 1400, 32, 16, t)

t = add_task(p3, "ERP Integration & Testing",
    "Integrate with SAP B1 via REST adapter for automatic PO sync and financial posting. "
    "Conduct full system testing, performance testing with 50,000 SKU dataset, and user training.",
    15000, 3200, 18, 17)
add_task(p3, "SAP B1 Integration",
    "Build bi-directional sync adapter: purchase orders, GRN, and stock valuation postings.",
    6000, 1400, 20, 18, t)
add_task(p3, "Performance & Load Testing",
    "Test system with 50,000 SKU dataset, 20 concurrent scanners, and peak season simulation.",
    5000, 1000, 18, 19, t)
add_task(p3, "User Training & Go-Live",
    "Train warehouse team, run parallel operations for 3 weeks, then cut over to new system.",
    4000, 800, 15, 20, t)

evm3 = recalc(p3)

# ── Metrics for projects 2 & 3 (project 1 already had some) ───────────────────
from decimal import Decimal

def upsert_metrics(pid, inv, rev, cost, life):
    m = db.query(ProjectSelectionMetrics).filter_by(project_id=pid).first()
    if not m:
        m = ProjectSelectionMetrics(project_id=pid)
        db.add(m)
    m.initial_investment = inv
    m.annual_revenue = rev
    m.annual_cost = cost
    m.project_lifetime = life
    roi = ((rev - cost) * life - inv) / inv * 100
    bcr = (rev * life) / (inv + cost * life)
    npv_val = sum((rev - cost) / (1.1 ** y) for y in range(1, life + 1)) - inv
    pb = inv / (rev - cost) if (rev - cost) > 0 else 999
    m.roi = round(roi, 4)
    m.bcr = round(bcr, 4)
    m.npv = round(npv_val, 2)
    m.payback_period = round(pb, 4)
    db.commit()

upsert_metrics(1, 150000, 80000, 20000, 5)
upsert_metrics(2, 95000,  60000, 15000, 6)
upsert_metrics(3, 60000,  40000, 10000, 5)

db.commit()

# ── Print summary ──────────────────────────────────────────────────────────────
print("Projects 1, 2, 3 seeded successfully!\n")
for pid, evm in [(1, evm1), (2, evm2), (3, evm3)]:
    p = db.query(Project).filter(Project.project_id == pid).first()
    tasks = db.query(WBSTask).filter(WBSTask.project_id == pid).all()
    parents = [t for t in tasks if t.parent_task_id is None]
    subs = [t for t in tasks if t.parent_task_id is not None]
    evm = db.query(EVMMetrics).filter_by(project_id=pid).first()
    print(f"  [{pid}] {p.name}")
    print(f"       Tasks: {len(parents)} parent, {len(subs)} subtasks | Total: {len(tasks)}")
    if evm:
        print(f"       BAC={evm.bac:,.0f} EV={evm.ev:,.0f} AC={evm.ac:,.0f} CPI={evm.cpi} SPI={evm.spi}")
    print()

db.close()
