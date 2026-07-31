from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# Import models so they register with SQLAlchemy metadata.
from app.models.user import User          # noqa: E402,F401
from app.models.request import ProjectRequest, ActivityLog   # noqa: E402,F401
from app.models.message import Message                        # noqa: E402,F401
from app.models.notification import Notification              # noqa: E402,F401
from app.models.content import Service, PricingPlan, FAQ, Testimonial, SiteSetting, PortfolioItem  # noqa: E402,F401


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
