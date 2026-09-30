# POLAR INDIA

India's Polar Knowledge Gateway, built as a Smart India Hackathon prototype for Problem Statement 26063.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Keep the terminal running, then open this address in Chrome or Edge by clicking it or pasting it into the browser address bar:

**http://127.0.0.1:5000**

Do not type the URL as a PowerShell command. To open it automatically from a second PowerShell window, run:

```powershell
Start-Process http://127.0.0.1:5000
```

The SQLite database is created automatically on first run and seeded with clearly marked demonstration records.

## Demo accounts

- Admin: `admin` / `Admin@123`
- Approved researcher: `researcher` / `Research@123`

A normal signup creates a `PENDING` researcher and cannot submit until an admin approves it.

## Architecture

`app.py` contains the Flask routes, SQLAlchemy models, authentication, validation, seed data and upload handling. Jinja templates are in `templates/`; the responsive dark-polar interface is in `static/css/site.css` and browser behavior is in `static/js/site.js`. Public routes only query approved expeditions. Researcher and administrator routes are protected by decorators. Uploaded images are limited to PNG/JPG/JPEG/WEBP and documents to PDF, with Werkzeug safe filenames.

This is demonstration data for a prototype, not an official government archive. A production deployment should integrate NCPOR identity systems, CSRF protection, object storage, moderation workflows and an official metadata catalogue.
