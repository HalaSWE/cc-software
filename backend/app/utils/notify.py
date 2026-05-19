"""
Shared notification helper — call from any route to create a notification.
"""
from app.models.evm import Notification

def notify(db, project_id: int, title: str, message: str, type_: str = "info"):
    """
    Create a notification record for a project.
    type_: 'info' | 'warning' | 'danger'
    """
    db.add(Notification(
        project_id=project_id,
        title=title,
        message=message,
        type=type_,
    ))
