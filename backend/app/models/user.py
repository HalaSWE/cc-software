"""
SQLAlchemy Models — maps to the tables already created in Supabase
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as PgEnum
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    PROJECT_MANAGER = "Project Manager"
    TEAM_MEMBER = "Team Member"

class User(Base):
    __tablename__ = "users"

    user_id       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username      = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(
                        PgEnum(UserRole, name="user_role", create_type=False,
                               values_callable=lambda e: [x.value for x in e]),
                        nullable=False, default=UserRole.TEAM_MEMBER
                    )
    email         = Column(String(100), unique=True, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)
    full_name     = Column(String(200), nullable=True)
    bio           = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"