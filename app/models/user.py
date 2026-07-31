import secrets
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db


class User(UserMixin, db.Model):
    """Represents both administrator(s) and client accounts.
    role: 'admin' or 'client'. Account creation for clients is fully optional.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(40))
    company = db.Column(db.String(150))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="client")  # admin | client
    avatar_url = db.Column(db.String(255), default="")
    is_active_account = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    requests = db.relationship("ProjectRequest", backref="owner", lazy="dynamic",
                                foreign_keys="ProjectRequest.user_id")
    sent_messages = db.relationship("Message", backref="sender", lazy="dynamic",
                                     foreign_keys="Message.sender_id")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    # Flask-Login required property
    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_account

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now(timezone.utc)
        return self.reset_token

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def unread_notifications_count(self) -> int:
        return self.notifications.filter_by(is_read=False).count()

    @property
    def unread_messages_count(self) -> int:
        from app.models.message import Message
        return Message.query.filter_by(recipient_id=self.id, is_read=False).count()

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
