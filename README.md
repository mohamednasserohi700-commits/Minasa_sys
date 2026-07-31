# ClientFlow — Client Request & Project Management Platform

A production-ready Flask web application for collecting client project requests, managing them
through a full workflow, and communicating with clients — built with a premium, modern SaaS-style
UI (glassmorphism, soft UI, dark/light mode, smooth animations).

---

## 1. Features

- **Public marketing site**: Hero, About, Services, Why Choose Us, Portfolio, Technologies,
  How It Works, Pricing, Testimonials, FAQ, Contact — plus a dedicated **Project Estimation** page.
- **No-login project request form** with file uploads (PDF, DOCX, ZIP, RAR, images), auto-generated
  ticket numbers, and public ticket tracking (ticket number + email).
- **Optional client accounts**: registration, login, password reset, profile & avatar, "My Requests",
  in-app messaging, notifications, uploaded files.
- **Admin panel**: dashboard with Chart.js analytics, full request lifecycle management (status,
  internal notes, assignment, replies), client management, website content management
  (Services / Pricing / FAQs / Testimonials), site settings, PDF/Excel export, activity logs,
  database backup, and the ability to create additional administrator accounts.
- **Security**: CSRF protection (Flask-WTF), password hashing (Werkzeug), server-side validation,
  secure sessions, file-type/size validation, custom error pages, rotating file logging.
- **REST-ish JSON endpoints** for notification polling (`/api/...`), ready to extend.

---

## 2. Tech Stack

| Layer          | Technology                                   |
|----------------|-----------------------------------------------|
| Backend        | Python 3.11, Flask 3                          |
| ORM            | SQLAlchemy (via Flask-SQLAlchemy)             |
| Auth           | Flask-Login                                   |
| Forms          | Flask-WTF / WTForms                            |
| DB (dev)       | SQLite                                         |
| DB (prod)      | PostgreSQL (Railway)                           |
| Migrations     | Flask-Migrate (Alembic)                        |
| Reports        | reportlab (PDF), openpyxl (Excel)              |
| Frontend       | Jinja2, vanilla CSS/JS, Bootstrap Icons, Chart.js |
| WSGI server    | Gunicorn                                       |

---

## 3. Project Structure

```
clientflow/
├── app/
│   ├── models/          # SQLAlchemy models (user, request, message, notification, content)
│   ├── routes/           # Blueprints: main, auth, client, admin, api
│   ├── forms/             # Flask-WTF forms
│   ├── services/          # file_service, ticket_service, export_service
│   ├── utils/              # decorators, helpers (Jinja filters)
│   ├── templates/          # Jinja2 templates (public, auth, client, admin, errors, partials)
│   └── static/              # css/, js/, images/, uploads/
├── config.py              # Environment-driven configuration
├── run.py                  # WSGI entry point
├── requirements.txt
├── runtime.txt
├── Procfile
├── railway.json
├── .env.example
└── README.md
```

---

## 4. Local Installation

### Prerequisites
- Python 3.11+
- pip

### Steps

```bash
# 1. Clone / unzip the project, then enter it
cd clientflow

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and set a real SECRET_KEY, admin credentials, etc.

# 5. Run the app (SQLite database is created automatically, along with
#    the default admin account and demo content, on first run)
python run.py
```

The app will be available at **http://localhost:5000**.

### Default Administrator Account
```
Username: administrator
Password: 3000330210
```
**Change this password immediately after first login** (Profile is managed the same way as a
client account — via the login session — or create a new admin from
`Admin → Add Administrator` and deactivate/remove the default one if desired).

---

## 5. Configuration (.env)

All configuration is environment-driven — see `.env.example` for the full list. Key variables:

| Variable                | Purpose                                              |
|--------------------------|-------------------------------------------------------|
| `SECRET_KEY`              | Flask session/CSRF signing key — **must** be changed in production |
| `DATABASE_URL`            | SQLite path locally; Railway injects PostgreSQL URL automatically |
| `ADMIN_USERNAME/PASSWORD` | Bootstrap admin account (created on first run only)    |
| `MAX_CONTENT_LENGTH_MB`   | Max upload size (default 25MB)                          |
| `MAIL_*`                  | SMTP settings — wired for future email sending          |
| `PROJECT_MANAGER_NAME`    | Shown on the Estimation page                             |

---

## 6. Database Migrations

The app auto-creates tables via `db.create_all()` on first run for convenience. For production
schema changes going forward, use Flask-Migrate:

```bash
# Initialize migrations folder (first time only)
flask db init

# Create a migration after changing models
flask db migrate -m "Describe your change"

# Apply migrations
flask db upgrade
```

On Railway, migrations run automatically via the `release: flask db upgrade` line in the `Procfile`.

---

## 7. Deploying to Railway

1. **Push your code** to a GitHub repository.
2. **Create a new Railway project** → "Deploy from GitHub repo" → select your repo.
3. **Add a PostgreSQL database** from the Railway dashboard (Railway automatically injects
   `DATABASE_URL` into your service — no manual configuration needed; `config.py` normalizes it).
4. **Set environment variables** in the Railway service settings (copy from `.env.example`):
   - `SECRET_KEY` (generate a strong random value)
   - `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`
   - `FLASK_ENV=production`
   - Any `MAIL_*` / company info variables you want
5. Railway will detect `railway.json` / `Procfile` and build automatically using Nixpacks.
6. On deploy, `release: flask db upgrade` runs migrations, then `web:` starts Gunicorn.
7. Visit your generated Railway URL — the app seeds the admin account and demo content
   automatically on first boot against the new database.

### Manual PostgreSQL backup/restore (production)
```bash
# Backup
railway run pg_dump $DATABASE_URL > backup.sql

# Restore
railway run psql $DATABASE_URL < backup.sql
```
(The in-app **Settings → Database Backup** button only works for local SQLite; use the commands
above for PostgreSQL environments.)

---

## 8. Admin Guide

- **Dashboard**: KPIs, request-volume trend, status/platform breakdown charts, recent activity.
- **Project Requests**: search/filter by status, country, category, budget, and date range;
  open any request to change its status, add assignment + internal notes (client-invisible),
  reply directly to the client, view/download attachments, or export a single ticket as PDF.
- **Clients**: view all registered accounts, their submitted requests, and activate/deactivate access.
- **Messages**: quick access to every conversation thread.
- **Website Content**: manage Services, Pricing Plans, FAQs, and Testimonials shown on the public site.
- **Settings**: contact info, social links, and database backup download.
- **Activity Logs**: an audit trail of status changes, content edits, and account actions.
- **Add Administrator**: grant another user full admin permissions.
- **Reports**: charts by status/country/platform, plus Excel/PDF export of all requests.

## 9. Client (User) Guide

- Submitting a project **never requires an account** — just fill out the form and save the
  generated ticket number, or use it with your email on the **Track Request** page anytime.
- Creating a free account additionally unlocks: a dashboard with request stats, two-way
  messaging per ticket, notifications, a profile with an avatar, and a consolidated view of every
  file you've uploaded.

---

## 10. Security Notes

- All forms are CSRF-protected (Flask-WTF `CSRFProtect`).
- Passwords are hashed with Werkzeug's `generate_password_hash` (PBKDF2).
- File uploads are validated by extension and size (`MAX_CONTENT_LENGTH_MB`); filenames are
  sanitized with `secure_filename` and stored under a random prefix to prevent collisions/guessing.
- Admin-only routes are protected by a `@admin_required` decorator in addition to `@login_required`.
- Uploaded files are served through authenticated, ownership-checked routes rather than a public
  static folder.
- Rotating file logging is enabled in production (`logs/clientflow.log`).

---

## 11. Extending the Platform

- **Email delivery**: `MAIL_*` config is already present; wire up Flask-Mail (or an API like
  SendGrid) inside `app/services/` and call it from the password-reset and notification flows.
- **Payments/invoices**: the `Invoice` concept referenced in the client dashboard spec can be
  added as a new model + blueprint following the same pattern as `ProjectRequest`.
- **Public REST API**: `app/routes/api.py` already exists as the natural home for additional
  JSON endpoints.

---

© ClientFlow. Built with Flask.
