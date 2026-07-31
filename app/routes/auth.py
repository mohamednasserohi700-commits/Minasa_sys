from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app.models import db
from app.models.user import User
from app.forms.auth_forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from app.services.ticket_service import log_activity
from app.translations import get_translator
from app.utils.helpers import localize_form_labels

auth_bp = Blueprint("auth", __name__)


def _t():
    return get_translator(session.get("lang", "en"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RegisterForm()
    localize_form_labels(form, _t(), {
        "full_name": "field_full_name", "username": "field_username", "email": "field_email",
        "phone": "field_phone", "company": "field_company_optional", "password": "field_password",
        "confirm_password": "field_confirm_password", "submit": "field_register_submit",
    })
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip().lower(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data,
            company=form.company.data,
            role="client",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        log_activity(actor=user.username, action="Created a new client account")
        db.session.commit()

        login_user(user)
        flash("Welcome! Your account has been created successfully.", "success")
        return redirect(url_for("client.dashboard"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard") if current_user.is_admin else url_for("client.dashboard"))

    form = LoginForm()
    localize_form_labels(form, _t(), {
        "username": "field_username_or_email", "password": "field_password",
        "remember": "field_remember", "submit": "field_login_submit",
    })
    if form.validate_on_submit():
        identifier = form.username.data.strip().lower()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and user.check_password(form.password.data):
            if not user.is_active_account:
                flash("Your account has been deactivated. Please contact support.", "danger")
                return render_template("auth/login.html", form=form)

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            return redirect(url_for("admin.dashboard") if user.is_admin else url_for("client.dashboard"))

        flash("Invalid username/email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    form = ForgotPasswordForm()
    localize_form_labels(form, _t(), {"email": "field_email", "submit": "field_forgot_submit"})
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            # Email delivery is ready-to-wire (see services) — for now we surface the link directly
            # so the flow is fully functional without SMTP configured.
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            flash(f"A password reset link has been generated. (Demo mode — link: {reset_link})", "info")
        else:
            flash("If that email exists in our system, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("This password reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    localize_form_labels(form, _t(), {
        "password": "field_password", "confirm_password": "field_confirm_password",
        "submit": "field_reset_submit",
    })
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form, token=token)
