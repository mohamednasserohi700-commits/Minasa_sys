from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

PLATFORM_CHOICES = [
    ("Website", "Website"),
    ("Mobile App", "Mobile App"),
    ("Desktop App", "Desktop App"),
    ("ERP", "ERP System"),
    ("CRM", "CRM System"),
    ("POS", "POS System"),
    ("HR", "HR System"),
    ("E-Commerce", "E-Commerce Platform"),
    ("Inventory", "Inventory Management"),
    ("Accounting", "Accounting System"),
    ("Other", "Other"),
]

CONTACT_CHOICES = [("Email", "Email"), ("Phone", "Phone Call"), ("WhatsApp", "WhatsApp")]

BUDGET_CHOICES = [
    ("", "Select a range (optional)"),
    ("Under 20,000 EGP", "Under 20,000 EGP"),
    ("20,000 - 40,000 EGP", "20,000 - 40,000 EGP"),
    ("40,000 - 80,000 EGP", "40,000 - 80,000 EGP"),
    ("80,000+ EGP", "80,000+ EGP"),
    ("Not sure yet", "Not sure yet"),
]

DELIVERY_CHOICES = [
    ("", "Select timeframe (optional)"),
    ("Less than 20 days", "Less than 20 days"),
    ("20 - 40 days", "20 - 40 days"),
    ("40 - 60 days", "40 - 60 days"),
    ("Flexible", "Flexible"),
]


class ProjectRequestForm(FlaskForm):
    # Contact
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=150)])
    company = StringField("Company", validators=[Optional(), Length(max=150)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=40)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=40)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=150)])
    country = StringField("Country", validators=[DataRequired(), Length(max=100)])
    city = StringField("City", validators=[Optional(), Length(max=100)])
    business_type = StringField("Business Type", validators=[Optional(), Length(max=150)])

    # Project
    project_name = StringField("Project Name", validators=[DataRequired(), Length(max=200)])
    project_category = StringField("Project Category", validators=[Optional(), Length(max=100)])
    platform = SelectField("Required Platform", choices=PLATFORM_CHOICES, validators=[DataRequired()])
    description = TextAreaField("Project Description", validators=[DataRequired(), Length(max=5000)])
    expected_features = TextAreaField("Expected Features", validators=[Optional(), Length(max=3000)])
    target_users = StringField("Target Users", validators=[Optional(), Length(max=200)])
    budget = SelectField("Budget", choices=BUDGET_CHOICES, validators=[Optional()])
    delivery_time = SelectField("Expected Delivery Time", choices=DELIVERY_CHOICES, validators=[Optional()])
    existing_system = TextAreaField("Existing System (if any)", validators=[Optional(), Length(max=2000)])
    preferred_contact = SelectField("Preferred Contact Method", choices=CONTACT_CHOICES, validators=[DataRequired()])
    additional_notes = TextAreaField("Additional Notes", validators=[Optional(), Length(max=2000)])

    attachments = MultipleFileField(
        "Attach Files (PDF, DOCX, ZIP, RAR, Images)",
        validators=[
            Optional(),
            FileAllowed(["pdf", "docx", "doc", "zip", "rar", "png", "jpg", "jpeg"],
                        "Unsupported file type."),
        ],
    )

    accept_terms = BooleanField("I accept the Terms & Conditions", validators=[DataRequired()])
    submit = SubmitField("Submit Project Request")
