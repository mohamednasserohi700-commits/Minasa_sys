from app.models import db
from app.models.request import ProjectRequest, generate_ticket_number, ActivityLog
from app.models.notification import Notification
from app.models.user import User


def create_unique_ticket_number() -> str:
    """Guarantees uniqueness against the database (retries on the rare collision)."""
    ticket = generate_ticket_number()
    while ProjectRequest.query.filter_by(ticket_number=ticket).first() is not None:
        ticket = generate_ticket_number()
    return ticket


def log_activity(actor: str, action: str, target: str = ""):
    entry = ActivityLog(actor=actor, action=action, target=target)
    db.session.add(entry)


def notify_all_admins(title: str, body: str, link: str = "", icon: str = "bi-bell"):
    admins = User.query.filter_by(role="admin").all()
    for admin in admins:
        db.session.add(Notification(user_id=admin.id, title=title, body=body, link=link, icon=icon))


def notify_user(user_id: int, title: str, body: str, link: str = "", icon: str = "bi-bell"):
    db.session.add(Notification(user_id=user_id, title=title, body=body, link=link, icon=icon))
