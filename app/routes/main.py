from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import current_user
from app.models import db
from app.models.request import ProjectRequest
from app.models.message import Message
from app.models.content import Service, PricingPlan, FAQ, Testimonial, SiteSetting, PortfolioItem
from app.forms.request_form import ProjectRequestForm
from app.services.file_service import save_uploaded_files
from app.services.ticket_service import create_unique_ticket_number, log_activity, notify_all_admins, notify_user
from app.translations import get_translator
from app.utils.helpers import localize_form_labels, localize_choices

main_bp = Blueprint("main", __name__)


@main_bp.route("/set-language/<lang_code>")
def set_language(lang_code):
    """Switch the site language (English / Arabic) and return to the referring page."""
    if lang_code in ("en", "ar"):
        session["lang"] = lang_code
        session.permanent = True
    return redirect(request.referrer or url_for("main.home"))


@main_bp.context_processor
def inject_globals():
    """Values available to every public template (site settings, unread counts, etc.)."""
    return {
        "site_settings": {
            "contact_email": SiteSetting.get("contact_email", current_app.config["PROJECT_MANAGER_EMAIL"]),
            "contact_phone": SiteSetting.get("contact_phone", current_app.config["PROJECT_MANAGER_PHONE"]),
            "contact_address": SiteSetting.get("contact_address", "Cairo, Egypt"),
            "company_name": current_app.config["COMPANY_NAME"],
        }
    }


@main_bp.route("/")
def home():
    services = Service.query.filter_by(is_active=True).order_by(Service.order).all()
    plans = PricingPlan.query.filter_by(is_active=True).order_by(PricingPlan.order).all()
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.order).all()
    testimonials = Testimonial.query.filter_by(is_active=True).order_by(Testimonial.order).all()
    portfolio_items = PortfolioItem.query.filter_by(is_active=True).order_by(PortfolioItem.order).all()
    stats = {
        "projects_delivered": ProjectRequest.query.filter_by(status="Completed").count() or 48,
        "happy_clients": max(len(testimonials) * 12, 36),
        "years_experience": 6,
        "support": "24/7",
    }
    return render_template("public/home.html", services=services, plans=plans,
                            faqs=faqs, testimonials=testimonials, stats=stats,
                            portfolio_items=portfolio_items)


@main_bp.route("/estimation")
def estimation():
    return render_template("public/estimation.html")


@main_bp.route("/pricing")
def pricing():
    plans = PricingPlan.query.filter_by(is_active=True).order_by(PricingPlan.order).all()
    return render_template("public/pricing.html", plans=plans)


@main_bp.route("/services")
def services():
    services = Service.query.filter_by(is_active=True).order_by(Service.order).all()
    return render_template("public/services.html", services=services)


@main_bp.route("/faq")
def faq():
    faqs = FAQ.query.filter_by(is_active=True).order_by(FAQ.order).all()
    return render_template("public/faq.html", faqs=faqs)


@main_bp.route("/contact")
def contact():
    return render_template("public/contact.html")


@main_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("public/privacy_policy.html")


def _build_localized_request_form():
    """Instantiate ProjectRequestForm with all labels and select-option text
    translated into the current session language."""
    form = ProjectRequestForm()
    t = get_translator(session.get("lang", "en"))

    localize_form_labels(form, t, {
        "full_name": "field_full_name", "company": "field_company", "phone": "field_phone",
        "whatsapp": "field_whatsapp", "email": "field_email", "country": "field_country",
        "city": "field_city", "business_type": "field_business_type",
        "project_name": "field_project_name", "project_category": "field_project_category",
        "platform": "field_platform", "description": "field_description",
        "expected_features": "field_expected_features", "target_users": "field_target_users",
        "budget": "field_budget", "delivery_time": "field_delivery_time",
        "existing_system": "field_existing_system", "preferred_contact": "field_preferred_contact",
        "additional_notes": "field_additional_notes", "attachments": "field_attachments",
        "accept_terms": "field_accept_terms", "submit": "field_submit_request",
    })

    localize_choices(form.platform, t, {
        "Website": "choice_platform_website", "Mobile App": "choice_platform_mobile",
        "Desktop App": "choice_platform_desktop", "ERP": "choice_platform_erp",
        "CRM": "choice_platform_crm", "POS": "choice_platform_pos", "HR": "choice_platform_hr",
        "E-Commerce": "choice_platform_ecommerce", "Inventory": "choice_platform_inventory",
        "Accounting": "choice_platform_accounting", "Other": "choice_platform_other",
    })
    localize_choices(form.preferred_contact, t, {
        "Email": "choice_contact_email", "Phone": "choice_contact_phone", "WhatsApp": "choice_contact_whatsapp",
    })
    localize_choices(form.budget, t, {
        "": "choice_budget_select", "Under 20,000 EGP": "choice_budget_under20",
        "20,000 - 40,000 EGP": "choice_budget_20_40", "40,000 - 80,000 EGP": "choice_budget_40_80",
        "80,000+ EGP": "choice_budget_80plus", "Not sure yet": "choice_budget_notsure",
    })
    localize_choices(form.delivery_time, t, {
        "": "choice_delivery_select", "Less than 20 days": "choice_delivery_under20",
        "20 - 40 days": "choice_delivery_20_40", "40 - 60 days": "choice_delivery_40_60",
        "Flexible": "choice_delivery_flexible",
    })
    return form


@main_bp.route("/request", methods=["GET", "POST"])
def project_request():
    """Public project request form — no account required."""
    form = _build_localized_request_form()

    # Pre-fill from logged-in client account for convenience
    if current_user.is_authenticated and not current_user.is_admin and request.method == "GET":
        form.full_name.data = current_user.full_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        form.company.data = current_user.company

    if form.validate_on_submit():
        attachments = save_uploaded_files(form.attachments.data, subfolder="requests")

        ticket = ProjectRequest(
            ticket_number=create_unique_ticket_number(),
            user_id=current_user.id if current_user.is_authenticated and not current_user.is_admin else None,
            full_name=form.full_name.data.strip(),
            company=form.company.data,
            phone=form.phone.data.strip(),
            whatsapp=form.whatsapp.data,
            email=form.email.data.strip().lower(),
            country=form.country.data,
            city=form.city.data,
            business_type=form.business_type.data,
            project_name=form.project_name.data.strip(),
            project_category=form.project_category.data,
            platform=form.platform.data,
            description=form.description.data.strip(),
            expected_features=form.expected_features.data,
            target_users=form.target_users.data,
            budget=form.budget.data,
            delivery_time=form.delivery_time.data,
            existing_system=form.existing_system.data,
            preferred_contact=form.preferred_contact.data,
            additional_notes=form.additional_notes.data,
            attachments=",".join(attachments),
            status="Pending",
        )
        db.session.add(ticket)
        db.session.flush()

        log_activity(actor=current_user.username if current_user.is_authenticated else "guest",
                      action="Submitted a new project request", target=ticket.ticket_number)
        notify_all_admins(
            title="New Project Request",
            body=f"{ticket.full_name} submitted '{ticket.project_name}' ({ticket.ticket_number})",
            link=f"/admin/requests/{ticket.id}",
            icon="bi-inbox-fill",
        )
        if ticket.user_id:
            notify_user(ticket.user_id, "Request Submitted",
                        f"Your request {ticket.ticket_number} has been received and is pending review.",
                        link=f"/client/requests/{ticket.id}", icon="bi-check-circle-fill")

        db.session.commit()
        return redirect(url_for("main.request_success", ticket_number=ticket.ticket_number))

    return render_template("public/request_form.html", form=form)


@main_bp.route("/request/success/<ticket_number>")
def request_success(ticket_number):
    ticket = ProjectRequest.query.filter_by(ticket_number=ticket_number).first_or_404()
    return render_template("public/request_success.html", ticket=ticket)


@main_bp.route("/track", methods=["GET", "POST"])
def track_request():
    """Allow anyone to check a ticket status using ticket number + email, no login needed.
    Also shows the conversation thread — including replies from our team — so a guest
    who never created an account can still see any message sent to them."""
    ticket = None
    messages = []
    searched = False
    if request.method == "POST":
        searched = True
        ticket_number = request.form.get("ticket_number", "").strip()
        email = request.form.get("email", "").strip().lower()
        ticket = ProjectRequest.query.filter_by(ticket_number=ticket_number, email=email).first()
        if not ticket:
            flash("No matching request found. Please check your ticket number and email.", "danger")
        else:
            messages = ticket.messages.order_by(Message.created_at.asc()).all()
    return render_template("public/track.html", ticket=ticket, messages=messages, searched=searched)


@main_bp.route("/track/reply", methods=["POST"])
def track_reply():
    """Let a guest (no account) send a reply from the track-request page."""
    ticket_number = request.form.get("ticket_number", "").strip()
    email = request.form.get("email", "").strip().lower()
    body = request.form.get("body", "").strip()
    ticket = ProjectRequest.query.filter_by(ticket_number=ticket_number, email=email).first()

    if not ticket:
        flash("Session expired — please search for your request again.", "danger")
        return redirect(url_for("main.track_request"))

    if body:
        msg = Message(request_id=ticket.id, sender_name=ticket.full_name, sender_email=ticket.email,
                      body=body, is_from_admin=False)
        db.session.add(msg)
        notify_all_admins("New Client Reply", f"{ticket.full_name} replied on {ticket.ticket_number}",
                          link=f"/admin/requests/{ticket.id}", icon="bi-chat-dots-fill")
        db.session.commit()
        flash("Your message has been sent.", "success")

    ticket = ProjectRequest.query.filter_by(ticket_number=ticket_number, email=email).first()
    messages = ticket.messages.order_by(Message.created_at.asc()).all()
    return render_template("public/track.html", ticket=ticket, messages=messages, searched=True)
