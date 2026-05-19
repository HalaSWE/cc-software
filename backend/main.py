"""
CC Software — Project Portfolio Management System
FastAPI Entry Point — Production Ready
"""
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from app.database import Base, engine
import app.models
from app.routes import auth, users, projects, selection, wbs_evm, reports, analytics, comments, members, pdf_reports, chatbot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cc_software")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CC Software API starting up...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables verified")
    yield
    logger.info("🛑 CC Software API shutting down...")

app = FastAPI(
    title="CC Software",
    description="Project Portfolio Management — Powered by EVM Analytics",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logger(request: Request, call_next):
    """Log every request with timing."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.1f}ms)"
    )
    response.headers["X-Process-Time"] = f"{elapsed:.2f}ms"
    response.headers["X-API-Version"] = "2.0.0"
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Please contact support."},
    )

for router in [auth.router, users.router, projects.router,
               selection.router, wbs_evm.router, reports.router,
               analytics.router, comments.router, members.router, pdf_reports.router,
               chatbot.router,
               ]:
    app.include_router(router)

@app.get("/", tags=["⚙️ System"], summary="API root — welcome message")
def root():
    return {
        "system": "CC Software",
        "version": "2.0.0",
        "description": "Project Portfolio Management System",
        "docs": "/docs",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.get("/health", tags=["⚙️ System"], summary="Health check")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
    }

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="CC Software API",
        version="2.0.0",
        description="""
## CC Software — Project Portfolio Management

A full-featured project management platform with:

- 🔐 **JWT Authentication** with Role-Based Access Control
- 📁 **Project CRUD** with member management
- 📊 **Project Selection & Scoring** (ROI, BCR, Payback, NPV)
- 🗂 **Work Breakdown Structure** (WBS) task management
- 📈 **Earned Value Management** (EVM) — CPI, SPI, EAC auto-calculation
- 🔔 **Smart Notifications** — auto-alerts for budget & schedule overruns
- 📄 **Reports** — CSV exports for all data
- 🧠 **Analytics** — portfolio health, risk scoring, trend analysis

### Roles
| Role | Permissions |
|------|------------|
| Admin | Full access |
| Project Manager | Create/manage projects, add tasks |
| Team Member | View + update task progress |
        """,
        routes=app.routes,
        tags=[
            {"name": "⚙️ System", "description": "Health, version, and system info"},
            {"name": "🔐 Authentication", "description": "Login, register, reset password"},
            {"name": "👤 User Management (Admin)", "description": "Admin-only user CRUD"},
            {"name": "📁 Project Management", "description": "Project CRUD + member management"},
            {"name": "📊 Project Selection & Scoring", "description": "Financial analysis and ranking"},
            {"name": "🗂 WBS & EVM", "description": "Tasks and Earned Value metrics"},
            {"name": "📈 Dashboard", "description": "Overview of all projects"},
            {"name": "🔔 Notifications", "description": "System alerts and notifications"},
            {"name": "📄 Reports", "description": "CSV / PDF export endpoints"},
            {"name": "🧠 Analytics", "description": "Portfolio analytics and risk intelligence"},
        ],
    )
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi
