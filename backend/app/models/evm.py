"""
WBS & EVM Models — Enhanced v2.0
"""
from sqlalchemy import (Column, Integer, String, Boolean, DateTime,
                        Text, ForeignKey, Numeric, Date, Enum as PgEnum)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from app.database import Base
import enum

class TaskStatus(str, enum.Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED   = "Completed"

class WBSTask(Base):
    __tablename__ = "wbs_tasks"

    task_id          = Column(Integer, primary_key=True, autoincrement=True)
    project_id       = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    parent_task_id   = Column(Integer, ForeignKey("wbs_tasks.task_id", ondelete="SET NULL"), nullable=True)
    task_name        = Column(String(200), nullable=False)
    description      = Column(Text, default='')
    planned_value    = Column(Numeric(15, 2), nullable=False, default=0)
    actual_cost      = Column(Numeric(15, 2), default=0)
    percent_complete = Column(Numeric(5, 2), default=0)
    status           = Column(String(50), default="Not Started")
    order_index      = Column(Integer, default=0)
    start_date       = Column(Date, nullable=True)
    end_date         = Column(Date, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project  = relationship("Project", back_populates="wbs_tasks")
    subtasks = relationship("WBSTask", backref=backref("parent", remote_side="WBSTask.task_id"))

    @property
    def earned_value(self) -> float:
        return float(self.planned_value or 0) * float(self.percent_complete or 0) / 100.0

    def __repr__(self):
        return f"<Task {self.task_name}>"

class EVMMetrics(Base):
    __tablename__ = "evm_metrics"

    evm_id             = Column(Integer, primary_key=True, autoincrement=True)
    project_id         = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"))

    bac = Column(Numeric(15, 2), default=0)
    pv  = Column(Numeric(15, 2), default=0)
    ev  = Column(Numeric(15, 2), default=0)
    ac  = Column(Numeric(15, 2), default=0)
    cv  = Column(Numeric(15, 2), default=0)
    sv  = Column(Numeric(15, 2), default=0)
    vac = Column(Numeric(15, 2), default=0)
    cpi = Column(Numeric(8, 4),  default=1)
    spi = Column(Numeric(8, 4),  default=1)
    eac = Column(Numeric(15, 2), default=0)
    etc = Column(Numeric(15, 2), default=0)
    is_over_budget     = Column(Boolean, default=False)
    is_behind_schedule = Column(Boolean, default=False)
    update_date        = Column(Date, server_default=func.current_date())

    project = relationship("Project", back_populates="evm_metrics")

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id      = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True)
    title           = Column(String(200), nullable=True)
    message         = Column(String(500), nullable=False)
    type            = Column(String(20), default="info")
    is_read         = Column(Boolean, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="notifications")

class ProjectComment(Base):
    __tablename__ = "project_comments"

    comment_id  = Column(Integer, primary_key=True, autoincrement=True)
    project_id  = Column(Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.user_id",    ondelete="CASCADE"), nullable=False)
    content     = Column(Text, nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="comments")
    author  = relationship("User")
