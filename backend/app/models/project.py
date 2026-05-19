"""
Project Models — Enhanced v2.0
"""
from sqlalchemy import (Column, Integer, String, Boolean, DateTime,
                        Text, ForeignKey, Enum as PgEnum, Date, Numeric)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ProjectStatus(str, enum.Enum):
    PENDING     = "Pending"
    CANDIDATE   = "Candidate"
    DRAFT       = "Draft"
    SELECTED    = "Selected"
    IN_PROGRESS = "In Progress"
    COMPLETED   = "Completed"
    CANCELLED   = "Cancelled"

class Project(Base):
    __tablename__ = "projects"

    project_id    = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name          = Column(String(150), nullable=False)
    description   = Column(Text, nullable=True)
    budget        = Column(Numeric(15, 2), nullable=False)
    start_date    = Column(Date, nullable=True)
    end_date      = Column(Date, nullable=True)
    status        = Column(
                        PgEnum(ProjectStatus, name="project_status", create_type=False,
                               values_callable=lambda e: [x.value for x in e]),
                        nullable=False, default=ProjectStatus.PENDING
                    )
    created_by    = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    manager_id    = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    is_selected   = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator           = relationship("User", foreign_keys=[created_by])
    manager           = relationship("User", foreign_keys=[manager_id])
    members           = relationship("ProjectMemberDetail", back_populates="project", cascade="all, delete-orphan")
    scoring           = relationship("ProjectScoring", back_populates="project", uselist=False, cascade="all, delete-orphan")
    selection_metrics = relationship("ProjectSelectionMetrics", back_populates="project", uselist=False, cascade="all, delete-orphan")
    wbs_tasks         = relationship("WBSTask", back_populates="project", cascade="all, delete-orphan")
    evm_metrics       = relationship("EVMMetrics", back_populates="project", cascade="all, delete-orphan")
    notifications     = relationship("Notification", back_populates="project", cascade="all, delete-orphan")
    comments          = relationship("ProjectComment", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project {self.name}>"

class ProjectMemberDetail(Base):
    __tablename__ = "project_member_details"

    detail_id        = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    assigned_project = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    role_in_project  = Column(String(100), nullable=True)
    assigned_at      = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="members", foreign_keys=[assigned_project])
    user    = relationship("User")

class ProjectScoring(Base):
    __tablename__ = "project_scoring"

    score_id        = Column(Integer, primary_key=True, autoincrement=True)
    project_id      = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), unique=True)
    total_score     = Column(Numeric(12, 4), default=0)
    roi_score       = Column(Numeric(12, 4), default=0)
    bcr_score       = Column(Numeric(12, 4), default=0)
    payback_score   = Column(Numeric(12, 4), default=0)
    eva_score       = Column(Numeric(12, 4), default=0)
    priority_rank   = Column(Integer, nullable=True)
    scored_at       = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="scoring")

class ProjectSelectionMetrics(Base):
    __tablename__ = "project_selection_metrics"

    selection_id       = Column(Integer, primary_key=True, autoincrement=True)
    project_id         = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"))
    initial_investment = Column(Numeric(15, 2), default=0)
    annual_revenue     = Column(Numeric(15, 2), default=0)
    annual_cost        = Column(Numeric(15, 2), default=0)
    project_lifetime   = Column(Integer, default=1)
    roi                = Column(Numeric(12, 4), default=0)
    bcr                = Column(Numeric(12, 4), default=0)
    payback_period     = Column(Numeric(12, 4), default=0)
    npv                = Column(Numeric(15, 2), default=0)
    score_result       = Column(Numeric(12, 4), default=0)
    selection_date     = Column(Date, server_default=func.current_date())

    project = relationship("Project", back_populates="selection_metrics")
