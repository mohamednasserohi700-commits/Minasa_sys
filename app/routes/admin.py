import os
import shutil
from datetime import datetime, timedelta, timezone
from flask import (Blueprint, render_template, redirect, url_for, flash, request,
                    abort, send_file, current_app, jsonify, send_from_directory)
from flask_login import login_required, current_user
from sqlalchemy import func

from app.models import db
from app.models.user import User
from app.models.request import ProjectRequest, ActivityLog, STATUS_CHOICES
from app.models.message import Message
from app.models.notification import Notification
from app.models.content import Service, PricingPlan, FAQ, Testimonial, SiteSetting, PortfolioItem
from app.utils.decorators import admin_required
from app.services.export_service import requests_to_excel, requests_to_pdf, single_request_to_pdf
from app.services.file_service import save_public_image
from app.services.ticket_service import notify_user, log_activity

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
@admin_required
def require_admin():
    pass


# ------------------------------------------------------------------ DASHBOARD
@admin_bp.route("/dashboard")
def dashboard():
    total_requests = ProjectRequest.query.count()
    total_clients = User.query.filter_by(role="client").count()
    pending = ProjectRequest.query.filter_by(status="Pending").count()
    in_progress = ProjectRequest.query.filter_by(status="In Progress").count()
    completed = ProjectRequest.query.filter_by(status="Completed").count()

    status_breakdown = dict(
        db.session.query(ProjectRequest.status, func.count(ProjectRequest.id))
        .group_by(ProjectRequest.status).all()
    )
    status_data = [status_breakdown.get(s, 0) for s in STATUS_CHOICES]

    # Compute request volume for the last 6 calendar months
    today = datetime.now(timezone.utc)
    months, month_counts = [], []
    cursor = datetime(today.year, today.month, 1)
    buckets = []
    for i in range(5, -1, -1):
        y, m = cursor.year, cursor.month - i
        while m <= 0:
            m += 12
            y -= 1
        buckets.append((y, m))
    for (y, m) in buckets:
        start = datetime(y, m, 1)
        end = datetime(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1)
        count = ProjectRequest.query.filter(ProjectRequest.created_at >= start,
                                             ProjectRequest.created_at < end).count()
        months.append(start.strftime("%b %Y"))
        month_counts.append(count)

    platform_breakdown = dict(
        db.session.query(ProjectRequest.platform, func.count(ProjectRequest.id))
        .group_by(ProjectRequest.platform).all()
    )

    recent_requests = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).limit(6).all()
    recent_activity = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render_template(
        "admin/dashboard.html",
        total_requests=total_requests, total_clients=total_clients, pending=pending,
        in_progress=in_progress, completed=completed,
        status_labels=STATUS_CHOICES, status_data=status_data,
        month_labels=months, month_data=month_counts,
        platform_labels=list(platform_breakdown.keys()), platform_data=list(platform_breakdown.values()),
        recent_requests=recent_requests, recent_activity=recent_activity,
    )


# ------------------------------------------------------------------ REQUESTS
@admin_bp.route("/requests")
def requests_list():
    query = ProjectRequest.query

    status = request.args.get("status", "")
    country = request.args.get("country", "")
    category = request.args.get("category", "")
    budget = request.args.get("budget", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    q = request.args.get("q", "")

    if status:
        query = query.filter(ProjectRequest.status == status)
    if country:
        query = query.filter(ProjectRequest.country.ilike(f"%{country}%"))
    if category:
        query = query.filter(ProjectRequest.project_category.ilike(f"%{category}%"))
    if budget:
        query = query.filter(ProjectRequest.budget == budget)
    if date_from:
        query = query.filter(ProjectRequest.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
    if date_to:
        query = query.filter(ProjectRequest.created_at <= datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1))
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(
            ProjectRequest.full_name.ilike(like), ProjectRequest.email.ilike(like),
            ProjectRequest.project_name.ilike(like), ProjectRequest.ticket_number.ilike(like),
        ))

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(ProjectRequest.created_at.desc()).paginate(page=page, per_page=15, error_out=False)

    countries = [c[0] for c in db.session.query(ProjectRequest.country).distinct() if c[0]]

    return render_template("admin/requests_list.html", pagination=pagination, requests=pagination.items,
                            statuses=STATUS_CHOICES, countries=countries, filters=request.args)


@admin_bp.route("/requests/<int:request_id>")
def request_detail(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    messages = ticket.messages.order_by(Message.created_at.asc()).all()
    for m in messages:
        if not m.is_from_admin and not m.is_read:
            m.is_read = True
    db.session.commit()
    return render_template("admin/request_detail.html", ticket=ticket, messages=messages, statuses=STATUS_CHOICES)


@admin_bp.route("/requests/<int:request_id>/status", methods=["POST"])
def update_status(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    new_status = request.form.get("status")
    if new_status in STATUS_CHOICES:
        old_status = ticket.status
        ticket.status = new_status
        log_activity(actor=current_user.username, action=f"Changed status {old_status} -> {new_status}",
                      target=ticket.ticket_number)
        if ticket.user_id:
            notify_user(ticket.user_id, "Request Status Updated",
                        f"Your request {ticket.ticket_number} is now '{new_status}'.",
                        link=f"/client/requests/{ticket.id}", icon="bi-arrow-repeat")
        db.session.commit()
        flash(f"Status updated to '{new_status}'.", "success")
    return redirect(url_for("admin.request_detail", request_id=ticket.id))


@admin_bp.route("/requests/<int:request_id>/notes", methods=["POST"])
def update_notes(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    ticket.internal_notes = request.form.get("internal_notes", "")
    ticket.assigned_to = request.form.get("assigned_to", "")
    db.session.commit()
    flash("Internal notes saved.", "success")
    return redirect(url_for("admin.request_detail", request_id=ticket.id))


@admin_bp.route("/requests/<int:request_id>/reply", methods=["POST"])
def reply_to_client(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    body = request.form.get("body", "").strip()
    if body:
        msg = Message(request_id=ticket.id, sender_id=current_user.id, recipient_id=ticket.user_id,
                       sender_name=current_user.full_name, sender_email=current_user.email,
                       body=body, is_from_admin=True)
        db.session.add(msg)
        if ticket.user_id:
            notify_user(ticket.user_id, "New Reply from Support",
                        f"You have a new reply on {ticket.ticket_number}.",
                        link=f"/client/requests/{ticket.id}", icon="bi-chat-dots-fill")
        db.session.commit()
        flash("Reply sent to client.", "success")
    return redirect(url_for("admin.request_detail", request_id=ticket.id))


@admin_bp.route("/requests/<int:request_id>/delete", methods=["POST"])
def delete_request(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    log_activity(actor=current_user.username, action="Deleted project request", target=ticket.ticket_number)
    db.session.delete(ticket)
    db.session.commit()
    flash("Request deleted.", "info")
    return redirect(url_for("admin.requests_list"))


@admin_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve uploaded files to authenticated admins (and owners, handled in client bp separately)."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


# ------------------------------------------------------------------ USERS (CLIENTS)
@admin_bp.route("/users")
def users_list():
    q = request.args.get("q", "")
    query = User.query.filter_by(role="client")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.email.ilike(like),
                                     User.username.ilike(like)))
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/users_list.html", users=users, q=q)


@admin_bp.route("/users/<int:user_id>")
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    requests_list = user.requests.order_by(ProjectRequest.created_at.desc()).all()
    return render_template("admin/user_detail.html", user=user, requests=requests_list)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active_account = not user.is_active_account
    log_activity(actor=current_user.username,
                 action=f"{'Activated' if user.is_active_account else 'Deactivated'} client account",
                 target=user.username)
    db.session.commit()
    flash(f"Account {'activated' if user.is_active_account else 'deactivated'}.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
def admin_reset_user_password(user_id):
    """Let an administrator set a brand-new password for a client who forgot theirs."""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "").strip()

    if len(new_password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.set_password(new_password)
    log_activity(actor=current_user.username, action="Reset client password", target=user.username)
    notify_user(user.id, "Password Changed",
                "Your password was reset by our support team. If this wasn't expected, please contact us.",
                icon="bi-shield-lock-fill")
    db.session.commit()
    flash(f"Password for {user.full_name} has been updated.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@admin_bp.route("/users/create-admin", methods=["GET", "POST"])
def create_admin():
    """Allow the existing administrator to create additional admin accounts."""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([full_name, username, email, password]):
            flash("All fields are required.", "danger")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "danger")
        else:
            admin_user = User(full_name=full_name, username=username, email=email, role="admin",
                               email_verified=True)
            admin_user.set_password(password)
            db.session.add(admin_user)
            log_activity(actor=current_user.username, action="Created new admin account", target=username)
            db.session.commit()
            flash("Administrator account created.", "success")
            return redirect(url_for("admin.users_list"))

    return render_template("admin/create_admin.html")


# ------------------------------------------------------------------ MESSAGES
@admin_bp.route("/messages")
def messages_list():
    tickets_with_messages = (
        db.session.query(ProjectRequest)
        .join(Message, Message.request_id == ProjectRequest.id)
        .distinct()
        .order_by(ProjectRequest.updated_at.desc())
        .all()
    )
    return render_template("admin/messages_list.html", tickets=tickets_with_messages)


# ------------------------------------------------------------------ NOTIFICATIONS
@admin_bp.route("/notifications")
def notifications():
    items = current_user.notifications.order_by(Notification.created_at.desc()).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template("admin/notifications.html", notifications=items)


# ------------------------------------------------------------------ EXPORTS / REPORTS
@admin_bp.route("/reports")
def reports():
    total = ProjectRequest.query.count()
    by_status = dict(db.session.query(ProjectRequest.status, func.count(ProjectRequest.id))
                      .group_by(ProjectRequest.status).all())
    by_country = dict(db.session.query(ProjectRequest.country, func.count(ProjectRequest.id))
                       .group_by(ProjectRequest.country).all())
    by_platform = dict(db.session.query(ProjectRequest.platform, func.count(ProjectRequest.id))
                        .group_by(ProjectRequest.platform).all())
    return render_template("admin/reports.html", total=total, by_status=by_status,
                            by_country=by_country, by_platform=by_platform)


@admin_bp.route("/export/excel")
def export_excel():
    query = ProjectRequest.query
    status = request.args.get("status", "")
    if status:
        query = query.filter_by(status=status)
    requests_data = query.order_by(ProjectRequest.created_at.desc()).all()
    buffer = requests_to_excel(requests_data)
    log_activity(actor=current_user.username, action="Exported requests to Excel")
    db.session.commit()
    return send_file(buffer, as_attachment=True, download_name="project_requests.xlsx",
                      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@admin_bp.route("/export/pdf")
def export_pdf():
    query = ProjectRequest.query
    status = request.args.get("status", "")
    if status:
        query = query.filter_by(status=status)
    requests_data = query.order_by(ProjectRequest.created_at.desc()).all()
    buffer = requests_to_pdf(requests_data)
    log_activity(actor=current_user.username, action="Exported requests to PDF")
    db.session.commit()
    return send_file(buffer, as_attachment=True, download_name="project_requests.pdf", mimetype="application/pdf")


@admin_bp.route("/requests/<int:request_id>/export/pdf")
def export_single_pdf(request_id):
    ticket = ProjectRequest.query.get_or_404(request_id)
    buffer = single_request_to_pdf(ticket)
    return send_file(buffer, as_attachment=True, download_name=f"{ticket.ticket_number}.pdf",
                      mimetype="application/pdf")


# ------------------------------------------------------------------ CONTENT MANAGEMENT
@admin_bp.route("/content/services", methods=["GET", "POST"])
def manage_services():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        icon = request.form.get("icon", "bi-stars").strip()
        if title and description:
            db.session.add(Service(title=title, description=description, icon=icon,
                                    order=Service.query.count()))
            db.session.commit()
            flash("Service added.", "success")
        return redirect(url_for("admin.manage_services"))
    services = Service.query.order_by(Service.order).all()
    return render_template("admin/manage_services.html", services=services)


@admin_bp.route("/content/services/<int:service_id>/delete", methods=["POST"])
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    db.session.delete(service)
    db.session.commit()
    flash("Service removed.", "info")
    return redirect(url_for("admin.manage_services"))


@admin_bp.route("/content/services/<int:service_id>/toggle", methods=["POST"])
def toggle_service(service_id):
    service = Service.query.get_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()
    return redirect(url_for("admin.manage_services"))


@admin_bp.route("/content/pricing", methods=["GET", "POST"])
def manage_pricing():
    if request.method == "POST":
        plan = PricingPlan(
            name_en=request.form.get("name_en", "").strip(),
            name_ar=request.form.get("name_ar", "").strip(),
            price_en=request.form.get("price_en", "").strip(),
            price_ar=request.form.get("price_ar", "").strip(),
            description_en=request.form.get("description_en", ""),
            description_ar=request.form.get("description_ar", ""),
            features_en=request.form.get("features_en", ""),
            features_ar=request.form.get("features_ar", ""),
            is_featured=bool(request.form.get("is_featured")),
            order=PricingPlan.query.count(),
        )
        db.session.add(plan)
        db.session.commit()
        flash("Pricing plan added.", "success")
        return redirect(url_for("admin.manage_pricing"))
    plans = PricingPlan.query.order_by(PricingPlan.order).all()
    return render_template("admin/manage_pricing.html", plans=plans)


@admin_bp.route("/content/pricing/<int:plan_id>/delete", methods=["POST"])
def delete_pricing(plan_id):
    plan = PricingPlan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    flash("Pricing plan removed.", "info")
    return redirect(url_for("admin.manage_pricing"))


@admin_bp.route("/content/faqs", methods=["GET", "POST"])
def manage_faqs():
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        if question and answer:
            db.session.add(FAQ(question=question, answer=answer, order=FAQ.query.count()))
            db.session.commit()
            flash("FAQ added.", "success")
        return redirect(url_for("admin.manage_faqs"))
    faqs = FAQ.query.order_by(FAQ.order).all()
    return render_template("admin/manage_faqs.html", faqs=faqs)


@admin_bp.route("/content/faqs/<int:faq_id>/delete", methods=["POST"])
def delete_faq(faq_id):
    faq = FAQ.query.get_or_404(faq_id)
    db.session.delete(faq)
    db.session.commit()
    flash("FAQ removed.", "info")
    return redirect(url_for("admin.manage_faqs"))


@admin_bp.route("/content/testimonials", methods=["GET", "POST"])
def manage_testimonials():
    if request.method == "POST":
        testimonial = Testimonial(
            client_name=request.form.get("client_name", "").strip(),
            client_role=request.form.get("client_role", ""),
            content=request.form.get("content", "").strip(),
            rating=int(request.form.get("rating", 5)),
            order=Testimonial.query.count(),
        )
        if testimonial.client_name and testimonial.content:
            db.session.add(testimonial)
            db.session.commit()
            flash("Testimonial added.", "success")
        return redirect(url_for("admin.manage_testimonials"))
    testimonials = Testimonial.query.order_by(Testimonial.order).all()
    return render_template("admin/manage_testimonials.html", testimonials=testimonials)


@admin_bp.route("/content/testimonials/<int:testimonial_id>/delete", methods=["POST"])
def delete_testimonial(testimonial_id):
    t = Testimonial.query.get_or_404(testimonial_id)
    db.session.delete(t)
    db.session.commit()
    flash("Testimonial removed.", "info")
    return redirect(url_for("admin.manage_testimonials"))


@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        for key in ["contact_email", "contact_phone", "contact_address", "whatsapp_number",
                    "facebook_url", "twitter_url", "linkedin_url", "instagram_url"]:
            SiteSetting.set(key, request.form.get(key, ""))
        log_activity(actor=current_user.username, action="Updated site settings")
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("admin.settings"))

    keys = ["contact_email", "contact_phone", "contact_address", "whatsapp_number",
            "facebook_url", "twitter_url", "linkedin_url", "instagram_url"]
    current_settings = {k: SiteSetting.get(k, "") for k in keys}
    return render_template("admin/settings.html", settings=current_settings)


@admin_bp.route("/settings/backup")
def backup_database():
    """Download the current SQLite database file as a backup (SQLite dev environments only)."""
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite"):
        flash("Direct backup download is only available for SQLite. "
              "For PostgreSQL on Railway, use `railway db backup` or pg_dump.", "warning")
        return redirect(url_for("admin.settings"))
    db_path = db_uri.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        flash("Database file not found.", "danger")
        return redirect(url_for("admin.settings"))
    log_activity(actor=current_user.username, action="Downloaded database backup")
    db.session.commit()
    return send_file(db_path, as_attachment=True,
                      download_name=f"clientflow_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db")


@admin_bp.route("/settings/restore", methods=["POST"])
def restore_database():
    """Restore the database from an uploaded SQLite backup file (SQLite dev environments only).

    Safety measures:
    - Only allowed when running on SQLite (PostgreSQL must be restored via pg_dump/psql).
    - Requires the admin to explicitly confirm via a checkbox.
    - Validates the uploaded file is a genuine SQLite database (checks the file header).
    - Automatically snapshots the CURRENT database to a private backups/ folder before
      overwriting anything, so an admin can always recover from a bad restore.
    """
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite"):
        flash("Restore from a file is only available for SQLite. "
              "For PostgreSQL on Railway, restore using `psql $DATABASE_URL < backup.sql`.", "warning")
        return redirect(url_for("admin.settings"))

    if not request.form.get("confirm_restore"):
        flash("You must confirm the restore checkbox before proceeding.", "danger")
        return redirect(url_for("admin.settings"))

    upload = request.files.get("backup_file")
    if not upload or not upload.filename:
        flash("Please choose a .db backup file to restore.", "danger")
        return redirect(url_for("admin.settings"))
    if not upload.filename.lower().endswith((".db", ".sqlite", ".sqlite3")):
        flash("Invalid file type. Please upload a .db/.sqlite/.sqlite3 backup file.", "danger")
        return redirect(url_for("admin.settings"))

    header = upload.stream.read(16)
    upload.stream.seek(0)
    if header != b"SQLite format 3\x00":
        flash("This file does not look like a valid SQLite database. Restore aborted.", "danger")
        return redirect(url_for("admin.settings"))

    db_path = db_uri.replace("sqlite:///", "")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backups_dir = os.path.join(base_dir, "backups")
    os.makedirs(backups_dir, exist_ok=True)

    try:
        db.session.remove()
        db.engine.dispose()

        # Automatic safety snapshot of the current database before it gets replaced.
        if os.path.exists(db_path):
            snapshot_name = f"pre_restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, os.path.join(backups_dir, snapshot_name))

        upload.save(db_path)
    except Exception as exc:
        current_app.logger.exception("Database restore failed")
        flash(f"Restore failed: {exc}", "danger")
        return redirect(url_for("admin.settings"))

    flash("Database restored successfully. A safety snapshot of the previous database was kept in "
          "the /backups folder. Please restart the application for all changes to take full effect.",
          "success")
    return redirect(url_for("admin.settings"))


@admin_bp.route("/activity-logs")
def activity_logs():
    page = request.args.get("page", 1, type=int)
    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False)
    return render_template("admin/activity_logs.html", pagination=pagination, logs=pagination.items)


@admin_bp.route("/content/portfolio", methods=["GET", "POST"])
def manage_portfolio():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if title and description:
            image_path = save_public_image(request.files.get("image"), subfolder="portfolio")
            item = PortfolioItem(
                tag=request.form.get("tag", "").strip(),
                title=title,
                description=description,
                image=image_path or "",
                demo_url=request.form.get("demo_url", "").strip(),
                demo_username=request.form.get("demo_username", "").strip(),
                demo_password=request.form.get("demo_password", "").strip(),
                order=PortfolioItem.query.count(),
            )
            db.session.add(item)
            log_activity(actor=current_user.username, action="Added portfolio item", target=title)
            db.session.commit()
            flash("Portfolio item added.", "success")
        else:
            flash("Title and description are required.", "danger")
        return redirect(url_for("admin.manage_portfolio"))

    items = PortfolioItem.query.order_by(PortfolioItem.order).all()
    return render_template("admin/manage_portfolio.html", items=items)


@admin_bp.route("/content/portfolio/<int:item_id>/update-demo", methods=["POST"])
def update_portfolio_demo(item_id):
    """Update (or clear) the live demo link and demo credentials for a portfolio item."""
    item = PortfolioItem.query.get_or_404(item_id)
    item.demo_url = request.form.get("demo_url", "").strip()
    item.demo_username = request.form.get("demo_username", "").strip()
    item.demo_password = request.form.get("demo_password", "").strip()
    log_activity(actor=current_user.username, action="Updated portfolio demo link", target=item.title)
    db.session.commit()
    flash("Demo link updated.", "success")
    return redirect(url_for("admin.manage_portfolio"))


@admin_bp.route("/content/portfolio/<int:item_id>/delete", methods=["POST"])
def delete_portfolio(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Portfolio item removed.", "info")
    return redirect(url_for("admin.manage_portfolio"))


@admin_bp.route("/content/portfolio/<int:item_id>/toggle", methods=["POST"])
def toggle_portfolio(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    item.is_active = not item.is_active
    db.session.commit()
    return redirect(url_for("admin.manage_portfolio"))
