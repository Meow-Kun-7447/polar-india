from datetime import date, datetime
from functools import wraps
from pathlib import Path
import os
import webbrowser

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("POLAR_SECRET_KEY", "polar-india-prototype-change-me"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{BASE_DIR / 'polar_india.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)
db = SQLAlchemy(app)

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {"pdf"}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(160), nullable=False)
    institution = db.Column(db.String(180), nullable=False)
    designation = db.Column(db.String(120), default="Researcher")
    department = db.Column(db.String(160), default="")
    research_area = db.Column(db.String(120), default="")
    authority = db.Column(db.String(160), default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default="researcher")
    status = db.Column(db.String(30), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expeditions = db.relationship("Expedition", backref="submitter", lazy=True)


class Expedition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    expedition_number = db.Column(db.String(80), nullable=False)
    region = db.Column(db.String(30), nullable=False)
    location = db.Column(db.String(180), nullable=False)
    latitude = db.Column(db.Float, default=0)
    longitude = db.Column(db.Float, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    overview = db.Column(db.Text, default="")
    objectives = db.Column(db.Text, default="")
    research_activities = db.Column(db.Text, default="")
    conclusion = db.Column(db.Text, default="")
    cover_image = db.Column(db.String(500), default="")
    video_url = db.Column(db.String(500), default="")
    submitted_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(30), default="APPROVED")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    members = db.relationship("ExpeditionMember", backref="expedition", cascade="all, delete-orphan", lazy=True)
    media = db.relationship("Media", backref="expedition", lazy=True)


class ExpeditionMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expedition_id = db.Column(db.Integer, db.ForeignKey("expedition.id"), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    designation = db.Column(db.String(120), default="Researcher")
    institution = db.Column(db.String(180), default="NCPOR")
    role = db.Column(db.String(120), default="Expedition member")


class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(240), nullable=False)
    authors = db.Column(db.String(240), default="NCPOR Research Group")
    year = db.Column(db.Integer, nullable=False)
    region = db.Column(db.String(30), default="Antarctica")
    research_area = db.Column(db.String(120), default="Climate Science")
    description = db.Column(db.Text, default="")
    resource_url = db.Column(db.String(500), default="#")


class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(240), nullable=False)
    description = db.Column(db.Text, default="")
    year = db.Column(db.Integer, nullable=False)
    region = db.Column(db.String(30), default="Antarctica")
    research_area = db.Column(db.String(120), default="Oceanography")
    resource_url = db.Column(db.String(500), default="#")


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    type = db.Column(db.String(20), default="photo")
    file_path = db.Column(db.String(500), default="")
    video_url = db.Column(db.String(500), default="")
    expedition_id = db.Column(db.Integer, db.ForeignKey("expedition.id"))
    year = db.Column(db.Integer, nullable=False)
    region = db.Column(db.String(30), default="Antarctica")
    location = db.Column(db.String(160), default="")
    description = db.Column(db.Text, default="")


class InstitutionalActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, default="")
    date = db.Column(db.Date, nullable=False)
    institution = db.Column(db.String(180), default="NCPOR")
    image = db.Column(db.String(500), default="")


class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    region = db.Column(db.String(30), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    focus = db.Column(db.String(180), default="Polar science")
    description = db.Column(db.Text, default="")


def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "demo_label": "DEMO ARCHIVE"}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def approved_researcher_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Researcher access requires a login.", "warning")
            return redirect(url_for("login"))
        if user.role == "admin":
            return view(*args, **kwargs)
        if user.status != "APPROVED":
            return redirect(url_for("pending"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user() or current_user().role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_upload(file, allowed):
    if not file or not file.filename:
        return ""
    if not allowed_file(file.filename, allowed):
        raise ValueError("Unsupported upload format.")
    safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{secure_filename(file.filename)}"
    file.save(UPLOAD_DIR / safe_name)
    return f"uploads/{safe_name}"


@app.route("/")
def index():
    stats = {
        "expeditions": Expedition.query.filter_by(status="APPROVED").count(),
        "publications": Publication.query.count(),
        "datasets": Dataset.query.count(),
        "photos": Media.query.filter_by(type="photo").count(),
        "videos": Media.query.filter_by(type="video").count(),
    }
    featured = Expedition.query.filter_by(status="APPROVED").order_by(Expedition.start_date.desc()).first()
    return render_template("index.html", stats=stats, featured=featured)


@app.route("/archive")
def archive():
    query = request.args.get("q", "").strip()
    region = request.args.get("region", "all")
    content = request.args.get("content", "all")
    year = request.args.get("year", "all")
    expeditions = Expedition.query.filter_by(status="APPROVED")
    if query:
        term = f"%{query}%"
        expeditions = expeditions.filter(or_(Expedition.title.ilike(term), Expedition.location.ilike(term), Expedition.overview.ilike(term), Expedition.research_activities.ilike(term)))
    if region != "all":
        expeditions = expeditions.filter_by(region=region)
    if year != "all" and year.isdigit():
        expeditions = expeditions.filter(db.extract("year", Expedition.start_date) == int(year))
    publications = Publication.query
    datasets = Dataset.query
    if query:
        term = f"%{query}%"
        publications = publications.filter(or_(Publication.title.ilike(term), Publication.authors.ilike(term), Publication.description.ilike(term), Publication.research_area.ilike(term)))
        datasets = datasets.filter(or_(Dataset.title.ilike(term), Dataset.description.ilike(term), Dataset.research_area.ilike(term)))
    return render_template("archive.html", expeditions=expeditions.all(), publications=publications.all(), datasets=datasets.all(), query=query, region=region, content=content, year=year)


@app.route("/expeditions")
def expeditions():
    records = Expedition.query.filter_by(status="APPROVED").order_by(Expedition.start_date.desc()).all()
    return render_template("expeditions.html", expeditions=records)


@app.route("/expedition/<int:expedition_id>")
def expedition_detail(expedition_id):
    expedition = Expedition.query.get_or_404(expedition_id)
    if expedition.status != "APPROVED" and (not current_user() or (current_user().id != expedition.submitted_by and current_user().role != "admin")):
        abort(404)
    return render_template("expedition_detail.html", expedition=expedition)


@app.route("/publications")
def publications():
    query = request.args.get("q", "")
    records = Publication.query.filter(Publication.title.ilike(f"%{query}%")).order_by(Publication.year.desc()).all()
    return render_template("listings.html", page_title="Research publications", intro="Peer-reviewed work connected to India's polar research programme.", records=records, kind="publication", query=query)


@app.route("/datasets")
def datasets():
    query = request.args.get("q", "")
    records = Dataset.query.filter(Dataset.title.ilike(f"%{query}%")).order_by(Dataset.year.desc()).all()
    return render_template("listings.html", page_title="Scientific datasets", intro="Open demonstration records for polar observations and field measurements.", records=records, kind="dataset", query=query)


@app.route("/media")
def media():
    records = Media.query.order_by(Media.year.desc()).all()
    return render_template("media.html", media_items=records)


@app.route("/activities")
def activities():
    records = InstitutionalActivity.query.order_by(InstitutionalActivity.date.desc()).all()
    return render_template("activities.html", activities=records)


@app.route("/stations")
def stations():
    return render_template("stations.html", stations=Station.query.all())


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    term = f"%{query}%"
    return render_template("search.html", query=query, expeditions=Expedition.query.filter(Expedition.status == "APPROVED", or_(Expedition.title.ilike(term), Expedition.overview.ilike(term))).all(), publications=Publication.query.filter(or_(Publication.title.ilike(term), Publication.description.ilike(term))).all(), datasets=Dataset.query.filter(or_(Dataset.title.ilike(term), Dataset.description.ilike(term))).all(), activities=InstitutionalActivity.query.filter(or_(InstitutionalActivity.title.ilike(term), InstitutionalActivity.description.ilike(term))).all())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(user_id=request.form.get("user_id", "").strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password", "")):
            session["user_id"] = user.id
            if user.role == "admin":
                return redirect(url_for("admin"))
            if user.status != "APPROVED":
                return redirect(url_for("pending"))
            return redirect(url_for("dashboard"))
        flash("The user ID or password was not recognised.", "error")
    return render_template("auth.html", mode="login")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        required = ["full_name", "user_id", "email", "institution", "password"]
        if any(not request.form.get(field, "").strip() for field in required):
            flash("Please complete all required fields.", "error")
        elif request.form.get("password") != request.form.get("confirm_password"):
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(user_id=request.form.get("user_id").strip()).first():
            flash("That user ID is already registered.", "error")
        else:
            user = User(user_id=request.form["user_id"].strip(), full_name=request.form["full_name"].strip(), email=request.form["email"].strip(), institution=request.form["institution"].strip(), designation=request.form.get("designation", "Researcher"), department=request.form.get("department", ""), research_area=request.form.get("research_area", ""), authority=request.form.get("authority", ""), password_hash=generate_password_hash(request.form["password"]), role="researcher", status="PENDING")
            db.session.add(user)
            db.session.commit()
            flash("Registration submitted successfully. Your account is pending authorization.", "success")
            return redirect(url_for("login"))
    return render_template("auth.html", mode="signup")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/pending")
def pending():
    return render_template("pending.html")


@app.route("/dashboard")
@approved_researcher_required
def dashboard():
    user = current_user()
    records = Expedition.query.filter_by(submitted_by=user.id).order_by(Expedition.created_at.desc()).all()
    counts = {status: sum(record.status == status for record in records) for status in ["DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED"]}
    return render_template("dashboard.html", expeditions=records, counts=counts)


@app.route("/submit-expedition", methods=["GET", "POST"])
@approved_researcher_required
def submit_expedition():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title or not request.form.get("location", "").strip():
            flash("Expedition name and location are required.", "error")
            return render_template("submit.html")
        start = date.fromisoformat(request.form["start_date"]) if request.form.get("start_date") else None
        end = date.fromisoformat(request.form["end_date"]) if request.form.get("end_date") else None
        try:
            cover_image = save_upload(request.files.get("cover_image"), ALLOWED_IMAGE_EXTENSIONS)
            report = save_upload(request.files.get("report"), ALLOWED_DOCUMENT_EXTENSIONS)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("submit.html")
        expedition = Expedition(title=title, expedition_number=request.form.get("expedition_number", ""), region=request.form.get("region", "Antarctica"), location=request.form["location"].strip(), latitude=float(request.form.get("latitude") or 0), longitude=float(request.form.get("longitude") or 0), start_date=start, end_date=end, overview=request.form.get("overview", ""), objectives=request.form.get("objectives", ""), research_activities=request.form.get("research_activities", ""), conclusion=request.form.get("conclusion", ""), cover_image=cover_image, submitted_by=current_user().id, status="PENDING_REVIEW" if request.form.get("action") == "submit" else "DRAFT")
        if report:
            expedition.overview += f"\n[Report uploaded: {report}]"
        db.session.add(expedition)
        db.session.flush()
        member_names = request.form.getlist("member_name")
        for index, name in enumerate(member_names):
            if name.strip():
                expedition.members.append(ExpeditionMember(name=name.strip(), designation=request.form.getlist("member_designation")[index], institution=request.form.getlist("member_institution")[index], role=request.form.getlist("member_role")[index]))
        db.session.commit()
        flash("Expedition submitted for review." if expedition.status == "PENDING_REVIEW" else "Draft saved.", "success")
        return redirect(url_for("dashboard"))
    return render_template("submit.html")


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html", users=User.query.filter_by(role="researcher", status="PENDING").all(), pending_expeditions=Expedition.query.filter_by(status="PENDING_REVIEW").all(), approved_count=Expedition.query.filter_by(status="APPROVED").count(), researcher_count=User.query.filter_by(role="researcher").count())


@app.post("/admin/user/<int:user_id>/<action>")
@admin_required
def update_user(user_id, action):
    user = User.query.get_or_404(user_id)
    if action in {"approve", "reject"}:
        user.status = "APPROVED" if action == "approve" else "REJECTED"
        db.session.commit()
        flash(f"{user.full_name} marked {user.status.lower()}.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/expedition/<int:expedition_id>/<action>")
@admin_required
def update_expedition(expedition_id, action):
    expedition = Expedition.query.get_or_404(expedition_id)
    if action in {"approve", "reject"}:
        expedition.status = "APPROVED" if action == "approve" else "REJECTED"
        db.session.commit()
        flash(f"Expedition marked {expedition.status.lower()}.", "success")
    return redirect(url_for("admin"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


def seed_data():
    if User.query.first():
        return
    admin_user = User(user_id="admin", full_name="Polar India Authority", email="authority@polar-india.demo", institution="NCPOR", designation="Authority", password_hash=generate_password_hash("Admin@123"), role="admin", status="APPROVED")
    researcher = User(user_id="researcher", full_name="Dr. Ananya Rao", email="researcher@polar-india.demo", institution="NCPOR", designation="Polar Researcher", research_area="Glaciology", password_hash=generate_password_hash("Research@123"), role="researcher", status="APPROVED")
    db.session.add_all([admin_user, researcher])
    db.session.flush()
    image_urls = [
        "https://images.unsplash.com/photo-1517783999520-f068d7431a60?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1551415923-a2297c7fda79?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1483347756197-71ef80e95f73?auto=format&fit=crop&w=1200&q=80",
    ]
    locations = [("Maitri Research Station", -70.7693, 11.7339), ("Bharati Research Station", -69.4076, 76.1874), ("Southern Ocean transect", -58.0, 45.0)]
    for index in range(10):
        region = "Antarctica" if index < 8 else "Arctic"
        loc, lat, lon = locations[index % len(locations)] if region == "Antarctica" else ("Ny-Alesund, Svalbard", 78.9232, 11.9230)
        expedition = Expedition(title=f"{43 - index}th Indian {'Antarctic' if region == 'Antarctica' else 'Arctic'} Expedition", expedition_number=f"Expedition {43 - index}", region=region, location=loc, latitude=lat, longitude=lon, start_date=date(2026 - index, 1, 10), end_date=date(2026 - index, 3, 20), overview="Demonstration record documenting field observations, logistics and scientific work by an Indian polar research team.", objectives="Build long-term observations of climate, ice, ocean and polar ecosystems.", research_activities="Glaciology, atmospheric sampling and environmental monitoring.", conclusion="Demonstration outcomes are provided for the Smart India Hackathon prototype.", cover_image=image_urls[index % len(image_urls)], submitted_by=researcher.id, status="APPROVED")
        expedition.members = [ExpeditionMember(name="Dr. Ananya Rao", designation="Polar Researcher", institution="NCPOR", role="Expedition scientist"), ExpeditionMember(name="Karan Menon", designation="Field Engineer", institution="NCPOR", role="Operations")]
        db.session.add(expedition)
        db.session.flush()
        db.session.add(Media(title=f"Field diary: {expedition.title}", type="photo", expedition_id=expedition.id, year=2026 - index, region=region, location=loc, file_path=image_urls[index % len(image_urls)], description="Demonstration expedition photography."))
        db.session.add(Media(title=f"Science briefing: {expedition.title}", type="video", expedition_id=expedition.id, year=2026 - index, region=region, location=loc, video_url="https://www.youtube.com/embed/Scxs7L0vhZ4", description="Demonstration video record."))
    for index in range(15):
        db.session.add(Publication(title=f"Polar observation report {index + 1}: changing field conditions", authors="NCPOR Research Group; partner institutions", year=2026 - index % 7, region="Antarctica" if index % 3 else "Arctic", research_area=["Climate Science", "Glaciology", "Oceanography", "Biology"][index % 4], description="Demonstration publication connected to India's polar science archive.", resource_url="#"))
    for index in range(10):
        db.session.add(Dataset(title=f"Polar measurement series {index + 1}", description="Demonstration dataset containing field observations for educational exploration.", year=2026 - index % 6, region="Antarctica" if index % 2 else "Arctic", research_area=["Oceanography", "Atmospheric Science", "Environmental Science"][index % 3], resource_url="#"))
    for index in range(5):
        db.session.add(InstitutionalActivity(title=["National Polar Science Workshop", "Expedition 46 announcement", "Open science outreach day", "Antarctic research briefing", "Polar data stewardship clinic"][index], description="Demonstration institutional activity for the Polar India prototype.", date=date(2026, 9 - index, 10), institution="National Centre for Polar and Ocean Research", image=image_urls[index % len(image_urls)]))
    db.session.add_all([Station(name="Maitri Research Station", region="Antarctica", latitude=-70.7693, longitude=11.7339, focus="Atmospheric science and glaciology", description="Demonstration station marker for India's Antarctic research presence."), Station(name="Bharati Research Station", region="Antarctica", latitude=-69.4076, longitude=76.1874, focus="Oceanography and climate science", description="Demonstration station marker for India's Antarctic research presence."), Station(name="Ny-Alesund field site", region="Arctic", latitude=78.9232, longitude=11.9230, focus="Arctic climate observations", description="Demonstration Arctic research marker."), Station(name="India", region="India", latitude=20.5937, longitude=78.9629, focus="Research coordination", description="National coordination point." )])
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        webbrowser.open("http://127.0.0.1:5000")
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
