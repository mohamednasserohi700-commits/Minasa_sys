from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, send_from_directory, session
from flask_login import login_required, current_user

from app.models import db
from app.models.request import ProjectRequest
from app.models.message import Message
from app.models.notification import Notification
from app.forms.auth_forms import ProfileForm, ChangePasswordForm
from app.services.file_service import save_uploaded_files
from app.translations import get_translator
from app.utils.helpers import localize_form_labels

client_bp = Blueprint("client", __name__, url_prefix="/client")


def _t():
    return get_translator(session.get("lang", "en"))


@client_bp.before_request
@login_required
def require_client():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))


@client_bp.route("/dashboard")
def dashboard():
    requests_qs = current_user.requests.order_by(ProjectRequest.created_at.desc())
    total = requests_qs.count()
    stats = {
        "total": total,
        "pending": requests_qs.filter(ProjectRequest.status == "Pending").count(),
        "in_progress": requests_qs.filter(ProjectRequest.status == "In Progress").count(),
        "completed": requests_qs.filter(ProjectRequest.status == "Completed").count(),
    }
    recent_requests = requests_qs.limit(5).all()
    recent_notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(5).all()
    return render_template("client/dashboard.html", stats=stats, recent_requests=recent_requests,
                            recent_notifications=recent_notifications)


@client_bp.route("/requests")
def my_requests():
    status_filter = request.args.get("status", "")
    query = current_user.requests
    if status_filter:
        query = query.filter(ProjectRequest.status == status_filter)
    requests_list = query.order_by(ProjectRequest.created_at.desc()).all()
    return render_template("client/my_requests.html", requests=requests_list, status_filter=status_filter)


@client_bp.route("/requests/<int:request_id>")
def request_detail(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    if ticket.user_id != current_user.id:
        abort(403)
    messages = ticket.messages.order_by(Message.created_at.asc()).all()
    for m in messages:
        if m.is_from_admin and not m.is_read:
            m.is_read = True
    db.session.commit()
    return render_template("client/request_detail.html", ticket=ticket, messages=messages)


@client_bp.route("/requests/<int:request_id>/reply", methods=["POST"])
def reply_to_request(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    if ticket.user_id != current_user.id:
        abort(403)
    body = request.form.get("body", "").strip()
    if body:
        msg = Message(request_id=ticket.id, sender_id=current_user.id, sender_name=current_user.full_name,
                       sender_email=current_user.email, body=body, is_from_admin=False)
        db.session.add(msg)
        from app.services.ticket_service import notify_all_admins
        notify_all_admins("New Client Reply", f"{current_user.full_name} replied on {ticket.ticket_number}",
                           link=f"/admin/requests/{ticket.id}", icon="bi-chat-dots-fill")
        db.session.commit()
        flash("Your message has been sent.", "success")
    return redirect(url_for("client.request_detail", request_id=ticket.id))


@client_bp.route("/messages")
def messages():
    threads = current_user.requests.order_by(ProjectRequest.created_at.desc()).all()
    return render_template("client/messages.html", threads=threads)


@client_bp.route("/notifications")
def notifications():
    items = current_user.notifications.order_by(Notification.created_at.desc()).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template("client/notifications.html", notifications=items)


@client_bp.route("/files")
def files():
    requests_with_files = [r for r in current_user.requests.order_by(ProjectRequest.created_at.desc()).all()
                            if r.attachment_list()]
    return render_template("client/files.html", requests=requests_with_files)


@client_bp.route("/profile", methods=["GET", "POST"])
def profile():
    form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()
    t = _t()
    localize_form_labels(form, t, {
        "full_name": "field_full_name", "phone": "field_phone", "company": "field_company",
        "submit": "field_profile_submit",
    })
    localize_form_labels(password_form, t, {
        "current_password": "field_current_password", "new_password": "field_new_password",
        "confirm_password": "field_confirm_new_password", "submit": "field_password_submit",
    })
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data.strip()
        current_user.phone = form.phone.data
        current_user.company = form.company.data
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("client.profile"))
    return render_template("client/profile.html", form=form, password_form=password_form)


@client_bp.route("/profile/password", methods=["POST"])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Password updated successfully.", "success")
    else:
        for errs in form.errors.values():
            for e in errs:
                flash(e, "danger")
    return redirect(url_for("client.profile"))


@client_bp.route("/profile/avatar", methods=["POST"])
def upload_avatar():
    file = request.files.get("avatar")
    if file and file.filename:
        saved = save_uploaded_files([file], subfolder="avatars")
        if saved:
            current_user.avatar_url = saved[0]
            db.session.commit()
            flash("Profile picture updated.", "success")
        else:
            flash("Unsupported file type for avatar.", "danger")
    return redirect(url_for("client.profile"))


@client_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve an uploaded file only if the current client owns the request it belongs to."""
    owns_file = any(filename in r.attachment_list() for r in current_user.requests.all())
    is_own_avatar = filename == current_user.avatar_url
    if not (owns_file or is_own_avatar):
        abort(403)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
