from sqlalchemy.orm import Session
from .. import models

def log_action(db: Session, user_id: int, action: str, message_id: int = None):
    log = models.AuditLog(user_id=user_id, action=action, message_id=message_id)
    db.add(log); db.commit()
    return log

def get_logs(db: Session, limit: int = 100):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(limit).all()

def query_logs(project_id: str, query: str) -> str:
    # Placeholder: could filter by project once we join audit logs to project context
    return "Analytics query handled."