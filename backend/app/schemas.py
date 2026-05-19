"""
Pydantic Schemas v2.0 — request & response validation
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class RoleEnum(str, Enum):
    Admin = "Admin"
    Project_Manager = "Project Manager"
    Team_Member = "Team Member"

class ProjectStatusEnum(str, Enum):
    PENDING     = "Pending"
    CANDIDATE   = "Candidate"
    DRAFT       = "Draft"
    SELECTED    = "Selected"
    IN_PROGRESS = "In Progress"
    COMPLETED   = "Completed"
    CANCELLED   = "Cancelled"

class TaskStatusEnum(str, Enum):
    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    COMPLETED   = "Completed"

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"

class ResetPasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6, max_length=100)

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    role: RoleEnum = Field(default=RoleEnum.Team_Member)
    email: EmailStr

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    role: Optional[RoleEnum] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    user_id: int
    username: str
    role: RoleEnum
    email: str
    is_active: bool
    full_name: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=1000)
    email: Optional[EmailStr] = None

class MessageResponse(BaseModel):
    message: str

TokenResponse.model_rebuild()

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    budget: float = Field(..., gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    manager_id: Optional[int] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    budget: Optional[float] = Field(None, gt=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ProjectStatusEnum] = None
    manager_id: Optional[int] = None

class ProjectResponse(BaseModel):
    project_id: int
    name: str
    description: Optional[str]
    budget: float
    start_date: Optional[date]
    end_date: Optional[date]
    status: ProjectStatusEnum
    created_by: int
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    is_selected: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectMemberAdd(BaseModel):
    user_id: int
    role_in_project: Optional[str] = None

class ProjectMemberResponse(BaseModel):
    detail_id: int
    assigned_project: int
    user_id: int
    username: Optional[str] = None
    role_in_project: Optional[str] = None
    assigned_at: datetime
    is_manager: bool = False

    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    members: List[ProjectMemberResponse] = []

    class Config:
        from_attributes = True

class SelectionMetricsCreate(BaseModel):
    initial_investment: float = Field(..., gt=0)
    annual_revenue: float = Field(..., gt=0)
    annual_cost: float = Field(..., gt=0)
    project_lifetime: int = Field(..., gt=0, le=50)

class SelectionMetricsResponse(BaseModel):
    selection_id: int
    project_id: int
    initial_investment: Optional[float] = None
    annual_revenue: Optional[float] = None
    annual_cost: Optional[float] = None
    project_lifetime: Optional[int] = None
    roi: Optional[float] = None
    bcr: Optional[float] = None
    payback_period: Optional[float] = None
    npv: Optional[float] = None
    score_result: Optional[float] = None
    selection_date: Optional[date] = None

    class Config:
        from_attributes = True

class ProjectScoringResponse(BaseModel):
    score_id: int
    project_id: int
    total_score: Optional[float] = None
    roi_score: Optional[float] = None
    bcr_score: Optional[float] = None
    payback_score: Optional[float] = None
    eva_score: Optional[float] = None
    priority_rank: Optional[int] = None
    scored_at: datetime

    class Config:
        from_attributes = True

class ProjectRankingItem(BaseModel):
    project_id: int
    name: str
    budget: float
    total_score: Optional[float] = None
    roi: Optional[float] = None
    bcr: Optional[float] = None
    payback_period: Optional[float] = None
    npv: Optional[float] = None
    priority_rank: Optional[int] = None
    is_selected: bool

    class Config:
        from_attributes = True

class WBSTaskCreate(BaseModel):
    task_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    planned_value: float = Field(..., ge=0)
    order_index: int = Field(default=0, ge=0)

class WBSTaskUpdate(BaseModel):
    task_name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    planned_value: Optional[float] = Field(None, ge=0)
    actual_cost: Optional[float] = Field(None, ge=0)
    percent_complete: Optional[float] = Field(None, ge=0, le=100)
    order_index: Optional[int] = Field(None, ge=0)
    status: Optional[TaskStatusEnum] = None

class WBSTaskResponse(BaseModel):
    task_id: int
    project_id: int
    task_name: str
    description: Optional[str]
    planned_value: float
    actual_cost: Optional[float]
    percent_complete: Optional[float]
    earned_value: Optional[float] = None
    status: TaskStatusEnum
    order_index: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EVMMetricsResponse(BaseModel):
    evm_id: int
    project_id: int
    bac: Optional[float] = None
    pv:  Optional[float] = None
    ev:  Optional[float] = None
    ac:  Optional[float] = None
    cv:  Optional[float] = None
    sv:  Optional[float] = None
    vac: Optional[float] = None
    cpi: Optional[float] = None
    spi: Optional[float] = None
    eac: Optional[float] = None
    etc: Optional[float] = None
    is_over_budget:     Optional[bool] = None
    is_behind_schedule: Optional[bool] = None
    update_date: Optional[date] = None

    class Config:
        from_attributes = True

class DashboardResponse(BaseModel):
    project_id: int
    project_name: str
    budget: float
    status: ProjectStatusEnum
    evm: Optional[EVMMetricsResponse]
    tasks_total: int
    tasks_done: int
    progress_pct: float

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    notification_id: int
    project_id: int
    user_id: Optional[int]
    title: Optional[str] = None
    message: str
    type: Optional[str] = "info"
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CommentResponse(BaseModel):
    comment_id: int
    project_id: int
    user_id: int
    author_username: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
