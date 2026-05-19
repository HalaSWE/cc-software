"""
Seed script — creates the initial admin user.
Run once: python seed_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.utils.auth import hash_password

def seed():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            print("Admin user already exists — skipping.")
            return

        admin = User(
            username="admin",
            email="admin@ccsoft.local",
            password_hash=hash_password("Admin@1234"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Admin user created: username=admin  password=Admin@1234")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
