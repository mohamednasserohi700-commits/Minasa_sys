"""
Application factory for ClientFlow — Client Request & Project Management Platform.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template, session
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

from config import config_map
from app.models import db, login_manager
from app.translations import get_translator

csrf = CSRFProtect()
migrate = Migrate()


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    # --- Extensions -------------------------------------------------------
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # --- Blueprints ---------------------------------------------------------
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.client import client_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # --- Template globals / filters -----------------------------------------
    from app.utils.helpers import time_ago, file_icon
    app.jinja_env.filters["time_ago"] = time_ago
    app.jinja_env.filters["file_icon"] = file_icon

    @app.context_processor
    def inject_year():
        from datetime import datetime, timezone
        return {"current_year": datetime.now(timezone.utc).year}

    @app.context_processor
    def inject_i18n():
        lang = session.get("lang", "en")
        return {
            "t": get_translator(lang),
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
        }

    # --- Error handlers -----------------------------------------------------
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return render_template("errors/500.html"), 500

    # --- Logging --------------------------------------------------------
    if not app.debug and not app.testing:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(os.path.join(log_dir, "clientflow.log"),
                                            maxBytes=1_000_000, backupCount=5)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("ClientFlow startup")

    # --- Ensure upload directories exist ------------------------------------
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    for sub in ("requests", "avatars"):
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

    # --- DB bootstrap (tables + default admin + seed content) --------------
    with app.app_context():
        db.create_all()
        _seed_defaults(app)

    return app


def _seed_defaults(app):
    """Create the default administrator account and baseline demo content
    the very first time the app runs against an empty database."""
    from app.models.user import User
    from app.models.content import Service, PricingPlan, FAQ, Testimonial, SiteSetting, PortfolioItem

    if not User.query.filter_by(username=app.config["ADMIN_USERNAME"]).first():
        admin = User(
            full_name="System Administrator",
            username=app.config["ADMIN_USERNAME"],
            email=app.config["ADMIN_EMAIL"],
            role="admin",
            email_verified=True,
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        app.logger.info("Default administrator account created.")

    if Service.query.count() == 0:
        default_services = [
            ("Website Development", "Modern, fast, SEO-friendly websites built with the latest technologies.", "bi-globe2"),
            ("Mobile App Development", "Native & cross-platform iOS/Android apps with premium UX.", "bi-phone-fill"),
            ("ERP & CRM Systems", "Custom enterprise resource planning and customer relationship platforms.", "bi-diagram-3-fill"),
            ("E-Commerce Solutions", "Full-featured online stores with payments, inventory & analytics.", "bi-cart-check-fill"),
            ("Point of Sale (POS)", "Reliable POS systems for retail, restaurants and services.", "bi-credit-card-2-front-fill"),
            ("UI/UX Design", "Research-driven interface design that converts and delights.", "bi-palette-fill"),
        ]
        for i, (title, desc, icon) in enumerate(default_services):
            db.session.add(Service(title=title, description=desc, icon=icon, order=i))

    if PricingPlan.query.count() == 0:
        plans = [
            (
                "Starter", "الباقة الأساسية",
                "8,000 EGP+", "8,000 جنيه+",
                "Best for small business websites & MVPs",
                "الأنسب لمواقع الشركات الصغيرة والمنتجات الأولية",
                "Landing / Business Website\nUp to 5 Pages\nBasic SEO Setup\n20 Working Days\n1 Month Free Support",
                "موقع تعريفي / صفحة هبوط\nحتى 5 صفحات\nإعداد أساسي لتحسين محركات البحث (SEO)\n20 يوم عمل\nشهر دعم مجاني",
                False,
            ),
            (
                "Professional", "الباقة الاحترافية",
                "12,000 EGP+", "12,000 جنيه+",
                "Ideal for growing businesses & platforms",
                "مثالية للشركات والمنصات المتنامية",
                "Custom Web/Mobile App\nAdmin Dashboard\nAPI Integrations\n35-45 Working Days\n3 Months Free Support",
                "تطبيق ويب / موبايل مخصص\nلوحة تحكم إدارية\nربط مع واجهات برمجية (API)\n35-45 يوم عمل\n3 أشهر دعم مجاني",
                True,
            ),
            (
                "Enterprise", "باقة المؤسسات",
                "20,000 EGP+", "20,000 جنيه+",
                "Full-scale ERP / CRM / E-Commerce systems",
                "أنظمة متكاملة ERP / CRM / تجارة إلكترونية",
                "Multi-Module System\nAdvanced Security & Roles\nDedicated Project Manager\n60 Working Days\n6 Months Free Support",
                "نظام متعدد الوحدات\nصلاحيات وأمان متقدم\nمدير مشروع مخصص\n60 يوم عمل\n6 أشهر دعم مجاني",
                False,
            ),
        ]
        for i, (name_en, name_ar, price_en, price_ar, desc_en, desc_ar, feat_en, feat_ar, featured) in enumerate(plans):
            db.session.add(PricingPlan(
                name_en=name_en, name_ar=name_ar, price_en=price_en, price_ar=price_ar,
                description_en=desc_en, description_ar=desc_ar,
                features_en=feat_en, features_ar=feat_ar,
                is_featured=featured, order=i,
            ))

    if FAQ.query.count() == 0:
        faqs = [
            ("Do I need to create an account to submit a project?",
             "No. You can submit a full project request without registering. An account is only needed if you want to track requests, message our team, or upload files later."),
            ("How long does it take to get a quotation?",
             "Our team typically reviews new requests and responds within 1-2 business days with a detailed quotation and timeline."),
            ("What technologies do you work with?",
             "We build with modern stacks including Python/Flask, React, Node.js, Flutter, and enterprise-grade databases, chosen based on your project needs."),
            ("Can I request changes after the project starts?",
             "Yes, our workflow includes structured revision cycles during the design and development phases to accommodate feedback."),
            ("Do you sign NDAs / confidentiality agreements?",
             "Absolutely. We can sign an NDA before discussing sensitive project details if required."),
        ]
        for i, (q, a) in enumerate(faqs):
            db.session.add(FAQ(question=q, answer=a, order=i))

    if Testimonial.query.count() == 0:
        testimonials = [
            ("Ahmed Farouk", "CEO, RetailPro", "The team delivered our POS system ahead of schedule with outstanding quality. Highly recommended.", 5),
            ("Sara Ibrahim", "Founder, MedCare Clinics", "Professional communication throughout and a beautiful, easy-to-use patient management platform.", 5),
            ("Youssef Hassan", "Operations Manager, LogiTrans", "Our custom ERP transformed how we manage logistics. Support has been excellent post-launch.", 5),
        ]
        for i, (name, role, content, rating) in enumerate(testimonials):
            db.session.add(Testimonial(client_name=name, client_role=role, content=content,
                                        rating=rating, order=i))

    if PortfolioItem.query.count() == 0:
        portfolio_items = [
            ("التعليم", "نظام متابعة حضور الطلاب للمدرسين",
             "أداة مخصصة تتيح للمدرسين تسجيل حضور الطلاب ومتابعته لحظيًا بسهولة.",
             "images/portfolio/education-center.png"),
            ("التعليم", "نظام إدارة السناتر التعليمية",
             "منصة متكاملة لإدارة الطلاب وتسجيل الحضور وإرسال التقارير لكل فرع تمتلكه.",
             "images/portfolio/education-center.png"),
            ("الصالونات والتجميل", "احجزلي — نظام حجز ذكي للصالونات",
             "أرسل رابط حجز لعملائك، استقبل المواعيد دون مكالمات هاتفية، وأدر قائمة الانتظار من لوحة تحكم واحدة.",
             "images/portfolio/salon-booking.png"),
            ("القانون", "نظام إدارة مكتب المحاماة الذكي",
             "نظام مخصص لمكاتب المحاماة لإدارة القضايا والعملاء وملفات القضايا بأمان تام.",
             "images/portfolio/law-firm.png"),
            ("السيارات", "نظام إدارة ومتابعة صيانة السيارات",
             "متابعة السيارات وأوامر الشغل ومخزون قطع الغيار والتحويل بين المخازن لمراكز الصيانة.",
             "images/portfolio/car-maintenance.png"),
            ("ERP", "نظام ERP محاسبي متكامل",
             "محاسبة كاملة: تقارير الأرباح والخسائر، المصاريف، الإيرادات، المخزون، وأرصدة العملاء والموردين في نظام واحد.",
             "images/portfolio/erp-system.png"),
        ]
        for i, (tag, title, desc, image) in enumerate(portfolio_items):
            db.session.add(PortfolioItem(tag=tag, title=title, description=desc, image=image, order=i))

    if not SiteSetting.query.filter_by(key="contact_email").first():
        SiteSetting.set("contact_email", app.config["PROJECT_MANAGER_EMAIL"])
        SiteSetting.set("contact_phone", app.config["PROJECT_MANAGER_PHONE"])
        SiteSetting.set("contact_address", "Cairo, Egypt")
        SiteSetting.set("whatsapp_number", app.config["PROJECT_MANAGER_PHONE"])

    db.session.commit()
