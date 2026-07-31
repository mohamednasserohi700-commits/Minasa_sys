from datetime import datetime, timezone
from app.models import db


class Message(db.Model):
    """Internal messaging between client and admin, optionally tied to a request/ticket."""
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("project_requests.id"), nullable=True)

    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # For guest (non-account) senders replying via email link, we still store name/email
    sender_name = db.Column(db.String(150))
    sender_email = db.Column(db.String(150))

    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_from_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Message {self.id} req={self.request_id}>"
