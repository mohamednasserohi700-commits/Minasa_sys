from datetime import datetime, timezone
from app.models import db


class Service(db.Model):
    __tablename__ = "services"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), default="bi-stars")
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class PricingPlan(db.Model):
    """Bilingual pricing plan — every visible field has an English and Arabic
    version so the plan renders correctly regardless of the visitor's chosen language."""
    __tablename__ = "pricing_plans"
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    price_en = db.Column(db.String(50), nullable=False)  # e.g. "8,000 EGP+"
    price_ar = db.Column(db.String(50), nullable=False)  # e.g. "8,000 جنيه+"
    description_en = db.Column(db.String(255))
    description_ar = db.Column(db.String(255))
    features_en = db.Column(db.Text)  # newline separated
    features_ar = db.Column(db.Text)  # newline separated
    is_featured = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    def name(self, lang):
        return self.name_ar if lang == "ar" else self.name_en

    def price(self, lang):
        return self.price_ar if lang == "ar" else self.price_en

    def description(self, lang):
        return self.description_ar if lang == "ar" else self.description_en

    def feature_list(self, lang):
        raw = self.features_ar if lang == "ar" else self.features_en
        return [f.strip() for f in (raw or "").split("\n") if f.strip()]


class FAQ(db.Model):
    __tablename__ = "faqs"
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    answer = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Testimonial(db.Model):
    __tablename__ = "testimonials"
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(150), nullable=False)
    client_role = db.Column(db.String(150))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, default=5)
    avatar_url = db.Column(db.String(255))
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class PortfolioItem(db.Model):
    """A showcased ready-made product on the public Portfolio section, with an
    optional live demo link and demo login credentials shown to visitors."""
    __tablename__ = "portfolio_items"
    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(100), default="")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(255), default="")  # relative path under /static/
    demo_url = db.Column(db.String(500), default="")
    demo_username = db.Column(db.String(150), default="")
    demo_password = db.Column(db.String(150), default="")
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class SiteSetting(db.Model):
    """Simple key-value store for editable site content (contact info, etc.)."""
    __tablename__ = "site_settings"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    @staticmethod
    def get(key, default=""):
        row = SiteSetting.query.filter_by(key=key).first()
        return row.value if row else default

    @staticmethod
    def set(key, value):
        row = SiteSetting.query.filter_by(key=key).first()
        if not row:
            row = SiteSetting(key=key, value=value)
            db.session.add(row)
        else:
            row.value = value
        return row
