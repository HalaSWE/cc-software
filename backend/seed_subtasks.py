"""
Adds subtasks and richer descriptions to all 6 example projects.
Run: python seed_subtasks.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.project import Project
from app.models.evm import WBSTask, EVMMetrics

db = SessionLocal()

# ── Helpers ──────────────────────────────────────────────────────────────────
def sub(parent_id, project_id, name, desc, pv, ac, pct, order):
    status = "Completed" if pct == 100 else ("In Progress" if pct > 0 else "Not Started")
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
    return t

def recalc(pid):
    tasks = db.query(WBSTask).filter(WBSTask.project_id == pid).all()
    if not tasks:
        return
    bac = sum(float(t.planned_value or 0) for t in tasks)
    pv  = bac
    ev  = sum(float(t.planned_value or 0) * float(t.percent_complete or 0) / 100 for t in tasks)
    ac  = sum(float(t.actual_cost or 0) for t in tasks)
    cpi = ev / ac if ac > 0 else 1.0
    spi = ev / pv if pv > 0 else 1.0
    eac = bac / cpi if cpi > 0 else bac
    evm = db.query(EVMMetrics).filter_by(project_id=pid).first()
    if not evm:
        evm = EVMMetrics(project_id=pid)
        db.add(evm)
    evm.bac = round(bac, 2); evm.pv = round(pv, 2); evm.ev = round(ev, 2)
    evm.ac  = round(ac, 2);  evm.cv = round(ev-ac,2); evm.sv = round(ev-pv,2)
    evm.cpi = round(cpi, 4); evm.spi = round(spi, 4)
    evm.eac = round(eac, 2); evm.etc = round(eac-ac,2); evm.vac = round(bac-eac,2)
    evm.is_over_budget     = cpi < 0.9
    evm.is_behind_schedule = spi < 0.9

# ── Remove any previously seeded subtasks ────────────────────────────────────
# (any task with a parent_task_id that belongs to projects 13-18)
existing_subs = db.query(WBSTask).filter(
    WBSTask.project_id >= 13,
    WBSTask.parent_task_id != None
).all()
for t in existing_subs:
    db.delete(t)
db.flush()

# Also update parent task descriptions
def desc_update(task_id, new_desc):
    t = db.query(WBSTask).filter(WBSTask.task_id == task_id).first()
    if t:
        t.description = new_desc


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 13 — Smart City Traffic Management System
# ════════════════════════════════════════════════════════════════════════════
# Task 13 – Requirements (100%)
desc_update(13, "Engage all stakeholders: municipality, traffic police, emergency services, and citizens. Define KPIs, compliance requirements, and data-sharing protocols.")
sub(13,13,"Stakeholder Workshop & Interview Series","Facilitate 6 workshops with municipality depts, traffic police, and emergency services to capture operational pain points.",60000,58500,100,11)
sub(13,13,"Functional Requirements Document","Draft and sign off FR document covering 120-intersection adaptive control, real-time analytics, and override capability.",120000,118000,100,12)
sub(13,13,"Non-Functional & Compliance Requirements","Define latency (<200ms signal update), uptime (99.95%), cybersecurity (ISO 27001), and data-privacy requirements.",100000,98500,100,13)

# Task 14 – Site Survey (100%)
desc_update(14, "Physical survey of all 120 intersections across 6 districts. Identify power availability, cabinet space, fibre duct routes, and cellular coverage gaps.")
sub(14,13,"Intersection Condition Assessment","On-site inspection of existing signal cabinets, power supply, and structural condition at all 120 sites.",70000,68000,100,21)
sub(14,13,"Fibre & Network Coverage Mapping","Map existing city fibre infrastructure; identify 34 sites needing new duct installation or wireless bridge.",80000,79000,100,22)
sub(14,13,"Survey Report & Site Design Package","Compile geo-tagged survey data, produce AutoCAD site layout drawings and bill of quantities per intersection.",40000,41000,100,23)

# Task 15 – AI Engine (100%)
desc_update(15, "Develop, train, and validate the adaptive traffic signal control AI using 2 years of historical detector data and reinforcement learning.")
sub(15,13,"Data Pipeline & Feature Engineering","Ingest 2-year historical loop detector, CCTV, and incident data; build ML feature store.",200000,196000,100,31)
sub(15,13,"Reinforcement Learning Model Training","Train and benchmark RL agent (PPO algorithm) against SUMO traffic simulation; achieve >30% throughput gain.",480000,472000,100,32)
sub(15,13,"Model Validation & Safety Testing","Red-team the AI for edge cases (emergency vehicles, special events); validate with real signal controller hardware-in-loop.",240000,237000,100,33)

# Task 16 – Hardware (100%)
desc_update(16, "Procure and quality-inspect all field hardware: radar/LiDAR sensors, edge compute units, fibre optic cables, managed PoE switches, and weatherproof cabinets.")
sub(16,13,"Radar Sensor & Edge Compute Procurement","Order 240 dual-radar sensor units and 120 NVIDIA Jetson edge nodes from approved vendor list; factory acceptance test.",350000,355000,100,41)
sub(16,13,"Network Hardware & Cabling Materials","Procure 85 km single-mode fibre, 480 managed PoE switches, 120 weatherproof outdoor cabinets.",320000,327000,100,42)
sub(16,13,"Hardware Staging & Pre-Configuration","Receive, inspect, firmware-flash, and pre-configure all hardware at staging warehouse before site dispatch.",180000,180000,100,43)

# Task 17 – Network Deployment (80%)
desc_update(17, "Install fibre backbone at 86 sites (complete) and wireless fallback at 120 sites. Remaining 14 sites pending permits for duct crossing under Ring Road.")
sub(17,13,"Fibre Duct Installation (86 sites)","Trench, install conduit, and blow fibre at 86 intersections; splice and test each link to <0.3 dB/km.",220000,211000,100,51)
sub(17,13,"Wireless Backhaul Deployment (120 sites)","Mount and align 120 pairs of licensed-band wireless units as fallback; achieve >99.5% link availability.",180000,167000,80,52)
sub(17,13,"Fibre Duct Installation (14 pending sites)","Awaiting NOC from Roads Authority for Ring Road duct crossing; mobilise upon approval.",120000,120000,40,53)

# Task 18 – Control Centre (45%)
desc_update(18, "Integrate field units into central NOC dashboard; develop real-time map view, alert engine, and manual override interface. Backend API integration 45% complete.")
sub(18,13,"NOC Dashboard Development","Build Angular-based real-time traffic map with heat-maps, incident overlays, and KPI panels.",180000,160000,80,61)
sub(18,13,"Alert Engine & Escalation Workflow","Implement rule-based alert engine triggering SMS/email for incidents, CPI anomalies, and sensor failures.",140000,50000,30,62)
sub(18,13,"Manual Override & CCTV Integration","Connect 120 PTZ CCTV feeds into NOC; implement signal override and emergency-green-wave capability.",110000,0,0,63)


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 14 — Hospital Information System Upgrade
# ════════════════════════════════════════════════════════════════════════════
# Task 22 – Legacy Audit (100%)
desc_update(22, "Full technical and data audit of 7 legacy HIS modules across 3 hospitals. Produces data-migration runbook and rollback strategy.")
sub(22,14,"Legacy Code & Schema Reverse Engineering","Document undocumented stored procedures, triggers, and data structures across 7 legacy modules.",120000,130000,100,11)
sub(22,14,"Data Quality Assessment","Profile 10 years of patient records; identify duplicates, format inconsistencies, and orphaned records.",140000,150000,100,12)
sub(22,14,"Migration Runbook & Rollback Plan","Define migration sequences, cutover windows, and tested rollback steps for each module.",120000,130000,100,13)

# Task 23 – EMR (100%)
desc_update(23, "Cloud-native EMR with HL7 FHIR R4 compliance, role-based access (10 clinician roles), offline-sync for ward use, and audit trail for regulatory compliance.")
sub(23,14,"FHIR Data Model & API Layer","Design and implement HL7 FHIR R4 REST API for patient demographics, encounters, observations, and documents.",380000,430000,100,21)
sub(23,14,"Clinician Workflow Screens","Build 24 clinical screens: patient timeline, vital signs charting, order entry, e-prescribing, and discharge summary.",460000,515000,100,22)
sub(23,14,"Offline Sync & Mobile Client","Progressive web app with IndexedDB offline sync for ward rounds and ICU use; tested for 500 concurrent users.",260000,295000,100,23)

# Task 24 – LIS (100%)
desc_update(24, "Full laboratory information system: sample barcode tracking, instrument integration (6 analyser brands), result validation, and critical value auto-alerting.")
sub(24,14,"Sample Lifecycle & Barcode Tracking","Track specimen from collection through processing, analysis, and archival; integrate with Brother label printers.",240000,260000,100,31)
sub(24,14,"Instrument Interface Layer (6 brands)","Build HL7 v2 interfaces for Roche Cobas, Abbott Alinity, Sysmex, Beckman, Ortho, and Bio-Rad analysers.",280000,300000,100,32)
sub(24,14,"Result Validation & Critical Value Alerts","Automated delta-check, reference-range validation, and WhatsApp/SMS alerting for critical lab values.",200000,220000,100,33)

# Task 25 – Pharmacy (95%)
desc_update(25, "Smart pharmacy covering inpatient dispensing, outpatient retail, drug-drug interaction alerts (using Micromedex), and automated reorder via SAP MM integration.")
sub(25,14,"Drug Formulary & Interaction Engine","Integrate Micromedex drug database; implement real-time DDI, allergy, and renal-dose alerts at prescribing.",200000,193000,100,41)
sub(25,14,"Automated Dispensing Cabinet Integration","Interface with Omnicell ADC units in 12 wards; real-time inventory sync and controlled-substance audit.",220000,212000,100,42)
sub(25,14,"Retail Pharmacy & Reorder Automation","Outpatient POS, patient medication counselling module, and SAP MM integration for auto-replenishment.",160000,152000,80,43)

# Task 26 – Billing (85%)
desc_update(26, "Claims processing for self-pay, corporate, and NPHIES national insurance. Automated eligibility checks, claims submission, and denial management workflow.")
sub(26,14,"NPHIES Eligibility & Pre-Auth Integration","Real-time eligibility check and pre-authorisation via NPHIES API for all insurance encounters.",160000,172000,100,51)
sub(26,14,"Claims Generation & Submission Engine","Auto-generate NPHIES-compliant claim bundles; submit, track, and reconcile up to 8,000 claims/day.",200000,212000,90,52)
sub(26,14,"Denial Management & Appeals Workflow","Dashboard for denied claims, root-cause classification, appeal letter generation, and resubmission tracking.",130000,136000,60,53)

# Task 27 – Appointments (60%)
desc_update(27, "Patient-facing web and mobile booking portal with specialty-based slot management, SMS/WhatsApp reminders, and no-show prediction model.")
sub(27,14,"Slot Management & Scheduling Engine","Configure specialty-level appointment templates; integrate with resource calendars for 180 consultants.",130000,118000,100,61)
sub(27,14,"Patient Web & Mobile Portal","React PWA + native iOS/Android apps: appointment booking, prescription refill requests, and results access.",150000,102000,60,62)
sub(27,14,"Reminder Engine & No-Show Prediction","Twilio-based SMS/WhatsApp reminders; ML model reducing no-show rate from 28% to under 12%.",80000,70000,30,63)


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 15 — Renewable Energy Grid Integration
# ════════════════════════════════════════════════════════════════════════════
# Task 31 – Feasibility (100%)
desc_update(31, "Grid stability modelling under full 700 MW renewable injection using PSS/E and PSCAD. Identifies 14 transmission bottlenecks and recommends 8 capacitor bank upgrades.")
sub(31,15,"Load Flow & Short Circuit Studies","Model N-1 and N-2 contingencies under maximum renewable output; validate thermal and voltage limits.",220000,219000,100,11)
sub(31,15,"Dynamic Stability & Frequency Analysis","PSCAD transient stability studies; quantify inertia deficit and recommend grid-forming inverter settings.",250000,249000,100,12)
sub(31,15,"Feasibility Report & Investment Case","Consolidate findings into bankable feasibility report with 20-year financial model and sensitivity analysis.",180000,180000,100,13)

# Task 32 – Permits (100%)
desc_update(32, "Coordinate all regulatory approvals: SEC grid connection agreement, ECRA generation licence, environmental permit (NCBE), and land-use approvals from 4 authorities.")
sub(32,15,"SEC Grid Connection Application","Submit technical application package; negotiate connection agreement terms and protection settings.",80000,79000,100,21)
sub(32,15,"ECRA Generation Licence & EIA","File generation licence application; coordinate Environmental Impact Assessment with NCBE certification.",90000,89000,100,22)
sub(32,15,"Land Use & Municipal Permits","Obtain land allocation, access-road construction permits, and aviation obstruction clearances.",50000,47000,100,23)

# Task 33 – Solar Phase 1 (65%)
desc_update(33, "EPC delivery of first 250 MW solar PV cluster. Civil works complete (90%), module installation 75% complete, string inverter commissioning ongoing.")
sub(33,15,"Civil & Piling Works (250 MW)","Ground preparation, piling, and galvanised racking structure installation across 5 km² site.",1800000,1820000,90,31)
sub(33,15,"Module & Inverter Installation","Install 620,000 bifacial modules (535 W) on single-axis trackers; string and wire 148 central inverters.",2800000,2100000,65,32)
sub(33,15,"MV Collector Network & Substation","Install 33 kV underground collection cables, ring-main units, and 250 MVA step-up transformer.",1200000,180000,20,33)

# Task 34 – Wind Farm (35%)
desc_update(34, "EPC for 80-turbine 2.5 MW wind farm. Foundation construction 60% done; tower sections and nacelles delivered to site; blade installation not yet started.")
sub(34,15,"Foundation Engineering & Construction","Bored-pile and gravity foundations for 80 turbines; concrete pours 60% complete.",1500000,1260000,60,41)
sub(34,15,"Tower & Nacelle Erection","Erect 80 steel towers (95m hub height) and install Vestas V150 nacelles using 600-tonne crawler cranes.",1800000,540000,20,42)
sub(34,15,"Blade Installation & Electrical Commissioning","Install 240 blades; connect 33 kV underground cables; individual turbine commissioning tests.",900000,0,0,43)

# Task 35 – BESS (0%)
desc_update(35, "200 MWh grid-scale battery energy storage using LFP cell chemistry. To be procured via international tender; delivery expected Q3 2026.")
sub(35,15,"BESS Technical Specification & Tender","Develop performance specification; issue international tender to CATL, BYD, Fluence, and Tesla.",400000,0,0,51)
sub(35,15,"BESS Civil Works & Infrastructure","Foundation, HV switchgear building, fire suppression, and HVAC for battery containers.",900000,0,0,52)
sub(35,15,"BESS Supply, Erection & Commissioning","Deliver, install, and commission 40 x 5 MWh battery containers; factory and site acceptance tests.",1800000,0,0,53)

# Task 36 – SCADA (0%)
desc_update(36, "Upgrade national SCADA to GE OSIsoft PI + OSIsoft Vision platform for real-time renewable generation monitoring, dispatch optimisation, and forecasting.")
sub(36,15,"SCADA Platform Procurement & Licensing","Procure GE OSIsoft PI Data Archive, Asset Framework, and 500-point renewable monitoring licences.",350000,0,0,61)
sub(36,15,"RTU & Communication Infrastructure","Install 140 RTUs at wind, solar, and BESS sites; configure DNP3 and IEC 61850 communication.",600000,0,0,62)
sub(36,15,"Forecasting & Dispatch Optimisation Module","AI-based 72-hour generation forecast integrated with SEC dispatch; wind/solar curtailment logic.",450000,0,0,63)


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 16 — E-Government Digital Transformation (ALL COMPLETED)
# ════════════════════════════════════════════════════════════════════════════
# Task 40 – Service Inventory (100%)
desc_update(40, "Catalogue all 240 government services across 14 ministries. Score each service by citizen impact (1-5) and digitisation complexity (1-5) to produce a prioritised roadmap.")
sub(40,16,"Service Mapping Workshops (14 Ministries)","Run 28 workshops (2 per ministry) to inventory services; build unified service taxonomy.",60000,58000,100,11)
sub(40,16,"Impact vs. Complexity Scoring Matrix","Score all 240 services; identify top 50 high-impact/low-complexity 'quick-win' services.",70000,67000,100,12)
sub(40,16,"Digital Transformation Roadmap","Produce phased 24-month roadmap with sprint plan, resource requirements, and measurable KPIs.",50000,47000,100,13)

# Task 41 – NIC Integration (100%)
desc_update(41, "REST API integration with NIC (National Information Centre) and Absher for real-time Saudi ID verification, biometric consent, and digital signature binding.")
sub(41,16,"NIC API Integration & Identity Verification","Implement real-time ID verification via NIC SOAP/REST gateway; test with all 9 ID types.",100000,97000,100,21)
sub(41,16,"Absher OTP & Biometric Consent","Integrate Absher two-factor authentication and biometric consent capture for high-assurance transactions.",110000,106000,100,22)
sub(41,16,"Digital Signature & Non-Repudiation","Implement PKI-based digital signing using NCA-certified certificates; integrate with Nafath.",80000,78000,100,23)

# Task 42 – Payment (100%)
desc_update(42, "Unified payment layer integrating SADAD government payment gateway, STC Pay, and Mada debit cards. Handles 50,000+ daily transactions across all ministries.")
sub(42,16,"SADAD Government Gateway Integration","Implement SADAD Bill Payment API for all government fees; real-time payment confirmation and receipt.",80000,78000,100,31)
sub(42,16,"STC Pay & Mada Card Integration","Integrate STC Pay wallet and Mada POS-emulation for debit transactions; PCI-DSS Level 1 compliance.",90000,88000,100,32)
sub(42,16,"Refund & Reconciliation Engine","Automated reconciliation of all payment channels; refund workflow with ministry approval chain.",70000,69000,100,33)

# Task 43 – Batch 1 Portals (100%)
desc_update(43, "Deploy citizen-facing departmental portals for MOI, MOH, MOE, MOF, MISA, MOJ, and MOT. Each ministry migrated 15-22 services averaging 4.2-hour delivery time.")
sub(43,16,"MOI & MOH Service Portals","Residency, national ID, birth registration, health appointments, and medical record request services.",280000,271000,100,41)
sub(43,16,"MOE, MOF & MISA Portals","Student enrolment, scholarship applications, tax registration, business licensing, and investor services.",280000,271000,100,42)
sub(43,16,"MOJ & MOT Portals","Court scheduling, legal entity registration, traffic fines payment, driving licence renewal, and vehicle registration.",280000,270000,100,43)

# Task 44 – Batch 2 Portals (100%)
desc_update(44, "Seven additional ministry portals: MOMRA, MWE, MCIT, MCI, MFA, MND, and Presidency. Completed 10 days ahead of schedule due to reusable component library from Batch 1.")
sub(44,16,"MOMRA, MWE & MCIT Portals","Building permits, utility connections, broadband applications, spectrum licensing, and postal services.",280000,266000,100,51)
sub(44,16,"MCI, MFA & MND Portals","Commercial registration, export certificates, visa applications, consular services, and procurement portals.",280000,266000,100,52)
sub(44,16,"Presidency & Integration Testing","General Authority portals; cross-ministry integration testing and end-to-end UAT with 500 pilot citizens.",280000,266000,100,53)

# Task 45 – Chatbot (100%)
desc_update(45, "Arabic-English NLP chatbot handling 80% of citizen queries without human escalation. Achieves 94% intent accuracy and 4.6/5.0 citizen satisfaction score.")
sub(45,16,"Arabic NLP Model Training","Fine-tune CAMeL BERT and AraBERT on 2M citizen query samples; achieve 94% intent classification accuracy.",110000,107000,100,61)
sub(45,16,"Chatbot Integration & Escalation Logic","Embed chatbot across all 14 ministry portals; build escalation to live agent with context handoff.",120000,116000,100,62)
sub(45,16,"Continuous Learning & Quality Assurance","A/B testing framework, fallback monitoring, and bi-weekly model retraining pipeline.",90000,85000,100,63)


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 17 — National Education Platform
# ════════════════════════════════════════════════════════════════════════════
# Task 49 – Architecture (100%)
desc_update(49, "Design microservices architecture on AWS KSA region: 22 services, PostgreSQL + Elasticsearch data layer, GraphQL federation API, and Kubernetes orchestration.")
sub(49,17,"Cloud Infrastructure Blueprint","AWS Well-Architected review; design multi-AZ VPC, EKS cluster, and RDS Aurora for 6.2M concurrent users.",100000,99000,100,11)
sub(49,17,"API Design & Service Contracts","Define GraphQL federation schema and REST API contracts for 22 microservices; publish OpenAPI specs.",110000,109000,100,12)
sub(49,17,"Security & Data Architecture","Design end-to-end encryption, student data privacy (PDPL compliance), and zero-trust network policies.",90000,90000,100,13)

# Task 50 – Core LMS (100%)
desc_update(50, "Assignment management, grade book, attendance tracking, timetabling, and curriculum mapping modules. Handles 6.2M students and 420,000 teachers across 21,000 schools.")
sub(50,17,"Assignment & Grade Book Module","Digital assignment submission, automated plagiarism detection (Turnitin API), and multi-rubric grading.",280000,277000,100,21)
sub(50,17,"Attendance & Timetabling Engine","Biometric and QR-code attendance capture; conflict-free automated timetable generation for 21,000 schools.",320000,317000,100,22)
sub(50,17,"Curriculum Mapping & Standards Alignment","Map 85,000 learning objectives to Saudi national curriculum standards; gap analysis dashboards for teachers.",280000,276000,100,23)

# Task 51 – AI Learning Engine (50%)
desc_update(51, "Adaptive learning engine that adjusts content difficulty, pacing, and format based on 47 learner features. Currently in beta with 12,000 pilot students.")
sub(51,17,"Learner Profiling & Feature Engineering","Build real-time learner feature store: performance history, engagement patterns, and learning style indicators.",240000,230000,100,31)
sub(51,17,"Adaptive Content Recommendation Model","Transformer-based recommendation engine; A/B tested on pilot cohort showing 23% improved learning outcomes.",280000,145000,50,32)
sub(51,17,"AI Dashboard & Teacher Override UI","Explainable AI dashboard showing why each student received specific content; teacher intervention tools.",200000,115000,20,33)

# Task 52 – Content Repository (35%)
desc_update(52, "85,000 curriculum-aligned digital resources: interactive simulations, videos, e-books, and assessments. Content ingestion pipeline 35% complete; priority on Maths and Science.")
sub(52,17,"Content Ingestion & Metadata Pipeline","Automated tagging pipeline using NLP; map each resource to subject, grade, and learning objective.",160000,130000,70,41)
sub(52,17,"Interactive Simulation Library (STEM)","600 PhET-style interactive simulations for Physics, Chemistry, and Biology grades 7-12.",180000,90000,30,42)
sub(52,17,"Arabic Video Production & Captioning","Commission 2,000 curriculum-aligned instructional videos; Arabic closed-captions and transcripts.",120000,60000,10,43)

# Task 53 – Video & Virtual Classroom (25%)
desc_update(53, "Live and recorded lecture delivery using Agora.io SDK. Adaptive bitrate streaming ensures HD video even at 256 kbps (typical rural connectivity).")
sub(53,17,"Video CDN & Adaptive Streaming","CloudFront CDN with HLS adaptive bitrate; tested down to 128 kbps with <3s start latency.",130000,95000,60,51)
sub(53,17,"Live Virtual Classroom (Agora.io)","Integrate Agora.io SDK for 40-student virtual classes; whiteboard, polls, breakout rooms, and recording.",150000,70000,20,52)
sub(53,17,"Bandwidth Optimisation for Rural Schools","Progressive video loading, pre-caching for scheduled lessons, and offline download for poor connectivity.",100000,30000,5,53)

# Task 54 – Teacher Dashboard (10%)
desc_update(54, "Professional development tracking, lesson planning assistant, and class analytics. Early design phase; wireframes approved by MoE.")
sub(54,17,"Class Performance Analytics Dashboard","Visual analytics: cohort heatmaps, at-risk student flags, and learning outcome attainment charts.",120000,28000,20,61)
sub(54,17,"AI Lesson Planning Assistant","GPT-4-based lesson plan generator aligned to Saudi curriculum; stores and shares teacher-created plans.",130000,10000,5,62)
sub(54,17,"Professional Development & CPD Tracking","CPD hour logging, MOOC integration, and automatic certification for completed training pathways.",90000,6000,3,63)


# ════════════════════════════════════════════════════════════════════════════
#  PROJECT 18 — Port Logistics Automation
# ════════════════════════════════════════════════════════════════════════════
# Task 58 – Simulation Study (100%)
desc_update(58, "Discrete-event simulation of current Jeddah Port operations using AnyLogic. Models 12,000 vessel calls/year, identifies 8 bottlenecks, and quantifies 60% throughput gain from automation.")
sub(58,18,"As-Is Process Mapping & Data Collection","Time-motion studies across all port gates, quays, and yard zones; 90-day operational data collection.",140000,139000,100,11)
sub(58,18,"AnyLogic Discrete-Event Simulation Model","Build calibrated simulation of current operations; validate against 12 months of throughput KPIs.",180000,180000,100,12)
sub(58,18,"Automation Scenario Analysis & ROI Model","Model 6 automation scenarios; recommend optimal AGV/ARMG configuration and produce 15-year NPV model.",100000,99000,100,13)

# Task 59 – Technology Selection (100%)
desc_update(59, "Evaluated 6 AGV vendors and 4 ARMG suppliers via structured RFP and site visits to Rotterdam, Shanghai, and Singapore automated terminals.")
sub(59,18,"RFP Development & Vendor Shortlisting","Issue RFP to 12 vendors; evaluate technical proposals; shortlist top 3 AGV and top 2 ARMG suppliers.",90000,88000,100,21)
sub(59,18,"Reference Site Visits & Demos","Technical delegation visits to ECT Rotterdam, APMT Shanghai, and PSA Singapore; benchmark KPIs.",110000,107000,100,22)
sub(59,18,"Vendor Selection & Contract Negotiation","Score vendors on technology maturity, local support, and total cost; negotiate LSTK contracts.",80000,76000,100,23)

# Task 60 – Civil Works (20%)
desc_update(60, "Quay extension (180m berth), reinforced concrete yard for AGV operation, power substation, and control building. Piling 40% complete; superstructure not yet started.")
sub(60,18,"Quay Extension & Marine Works","Dredge and extend quay by 180m; install new quay crane rails and rubber fender system.",1400000,560000,35,31)
sub(60,18,"AGV Hardstand & Yard Infrastructure","Reinforced concrete hardstand for AGV operation; install guidance induction loops and wireless mesh.",1600000,220000,12,32)
sub(60,18,"Power Substation & Control Building","33/11 kV substation for 8 MW AGV charging; HVAC and cable management for control centre.",800000,70000,5,33)

# Task 61 – ARMG Cranes (0%)
desc_update(61, "8 automated rail-mounted gantry cranes: span 35 containers wide, 1-over-8 stacking, automated spreader with twin-lift capability. Delivery scheduled Q2 2027.")
sub(61,18,"ARMG Civil Foundation & Rail Works","Install 2.4 km crane rail foundation; precision levelling to <2 mm tolerance across 400m runway.",900000,0,0,41)
sub(61,18,"ARMG Supply & Factory Acceptance Test","Manufacture, factory-test, and sea-freight 8 ARMG structures from Konecranes Finland facility.",1500000,0,0,42)
sub(61,18,"ARMG Erection & Site Commissioning","Erect crane structures; install electrical, anti-collision, and automation systems; site acceptance test.",500000,0,0,43)

# Task 62 – AGVs (0%)
desc_update(62, "32 battery-electric automated guided vehicles. 70-tonne capacity, LiDAR navigation, 4-hour charge time, 20-hour operational cycle. Delivery Q3 2027.")
sub(62,18,"AGV Procurement & Factory Acceptance","Order 32 KION Dematic AGVs; witness factory acceptance tests including obstacle detection and emergency stop.",700000,0,0,51)
sub(62,18,"AGV Traffic Management System","Deploy KION FTS fleet management; configure route planning, collision avoidance, and charging sequencing.",600000,0,0,52)
sub(62,18,"AGV Site Commissioning & Integration","Commission AGVs in live yard; integrate with ARMG and POS; conduct 72-hour reliability run at design capacity.",500000,0,0,53)

# Task 63 – POS Development (0%)
desc_update(63, "AI-powered Terminal Operating System replacing legacy Navis N4. Real-time berth allocation, dynamic yard planning, and predictive vessel ETA integration via AIS.")
sub(63,18,"POS Core Engine & Data Model","Develop berth planning, vessel scheduling, and container tracking core using event-sourcing architecture.",500000,0,0,61)
sub(63,18,"Yard Optimisation & AGV/ARMG Interface","AI-based container placement optimisation; real-time command dispatch to AGVs and ARMGs via OPC-UA.",580000,0,0,62)
sub(63,18,"Gate & Customs Integration","OCR gate automation, truck appointment system, and FASAH customs integration for paperless clearance.",420000,0,0,63)


# ── Commit & Recalculate EVM ─────────────────────────────────────────────────
db.flush()
for pid in [13, 14, 15, 16, 17, 18]:
    recalc(pid)

db.commit()
print("Subtasks seeded and EVM recalculated.")

for pid in [13, 14, 15, 16, 17, 18]:
    tasks = db.query(WBSTask).filter(WBSTask.project_id == pid).all()
    parents = [t for t in tasks if t.parent_task_id is None]
    subs    = [t for t in tasks if t.parent_task_id is not None]
    evm = db.query(EVMMetrics).filter_by(project_id=pid).first()
    p   = db.query(Project).filter(Project.project_id == pid).first()
    print(f"  [{pid}] {p.name[:45]:<45} parents={len(parents)} subs={len(subs)} CPI={float(evm.cpi):.3f} SPI={float(evm.spi):.3f}")

db.close()
