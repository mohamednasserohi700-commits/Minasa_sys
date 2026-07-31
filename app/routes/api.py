from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.models import db
from app.models.notification import Notification

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/notifications/unread-count")
@login_required
def unread_notifications_count():
    return jsonify({"count": current_user.unread_notifications_count})


@api_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    notif = Notification.query.get_or_404(notification_id)
    if notif.user_id != current_user.id:
        return jsonify({"error": "forbidden"}), 403
    notif.is_read = True
    db.session.commit()
    return jsonify({"success": True})


@api_bp.route("/messages/unread-count")
@login_required
def unread_messages_count():
    return jsonify({"count": current_user.unread_messages_count})
