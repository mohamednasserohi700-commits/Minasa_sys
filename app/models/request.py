import random
import string
from datetime import datetime, timezone
from app.models import db

STATUS_CHOICES = ["Pending", "Reviewing", "Approved", "In Progress", "Completed", "Rejected"]

STATUS_COLORS = {
    "Pending": "warning",
    "Reviewing": "info",
    "Approved": "primary",
    "In Progress": "accent",
    "Completed": "success",
    "Rejected": "danger",
}


def generate_ticket_number() -> str:
    """Generates a unique, human-friendly ticket number e.g. CF-2026-8K3F2A"""
    year = datetime.now(timezone.utc).year
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CF-{year}-{suffix}"


class ProjectRequest(db.Model):
    """A client project request / support ticket submitted via the public form."""
    __tablename__ = "project_requests"

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)

    # Optional link to a registered account
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Contact info
    full_name = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150))
    phone = db.Column(db.String(40), nullable=False)
    whatsapp = db.Column(db.String(40))
    email = db.Column(db.String(150), nullable=False)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    business_type = db.Column(db.String(150))

    # Project details
    project_name = db.Column(db.String(200), nullable=False)
    project_category = db.Column(db.String(100))
    platform = db.Column(db.String(100))  # Website, Mobile App, ERP, CRM, etc.
    description = db.Column(db.Text, nullable=False)
    expected_features = db.Column(db.Text)
    target_users = db.Column(db.String(200))
    budget = db.Column(db.String(100))
    delivery_time = db.Column(db.String(100))
    existing_system = db.Column(db.Text)
    preferred_contact = db.Column(db.String(50))  # Email, Phone, WhatsApp
    additional_notes = db.Column(db.Text)

    # Files (stored as JSON-ish comma separated relative paths)
    attachments = db.Column(db.Text)  # comma-separated filenames

    # Workflow
    status = db.Column(db.String(30), default="Pending", nullable=False)
    internal_notes = db.Column(db.Text)  # admin-only notes
    assigned_to = db.Column(db.String(150))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    messages = db.relationship("Message", backref="request", lazy="dynamic",
                                cascade="all, delete-orphan")

    def attachment_list(self):
        if not self.attachments:
            return []
        return [a for a in self.attachments.split(",") if a]

    @property
    def status_color(self):
        return STATUS_COLORS.get(self.status, "secondary")

    def __repr__(self):
        return f"<ProjectRequest {self.ticket_number}>"


class ActivityLog(db.Model):
    """Audit trail for important actions across the system."""
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor = db.Column(db.String(150))  # username or 'system' / 'guest'
    action = db.Column(db.String(255), nullable=False)
    target = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ActivityLog {self.action}>"
