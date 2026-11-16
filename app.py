import os
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
db_url = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "libsphere.db"))
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(BASE_DIR, "static", "uploads")
app.config["PROFILE_FOLDER"] = os.path.join(app.config["UPLOAD_FOLDER"], "profiles")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROFILE_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
ALLOWED_EXTENSIONS = {"pdf", "epub"}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)
    profile_pic = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False, index=True)
    author = db.Column(db.String(180), default="")
    publisher = db.Column(db.String(180), default="")
    isbn = db.Column(db.String(40), default="", index=True)
    edition = db.Column(db.String(80), default="")
    subject = db.Column(db.String(120), default="", index=True)
    department = db.Column(db.String(80), default="")
    call_no = db.Column(db.String(80), default="", index=True)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    copies = db.relationship("BookCopy", backref="book", cascade="all, delete-orphan")

class BookCopy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    acc_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    barcode_value = db.Column(db.String(80), unique=True, nullable=False, index=True)
    shelf = db.Column(db.String(80), default="")
    condition = db.Column(db.String(40), default="Good")
    status = db.Column(db.String(30), default="available", index=True)
    acquisition_date = db.Column(db.Date)
    purchase_price = db.Column(db.Float)
    vendor = db.Column(db.String(150), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.relationship("BookEvent", backref="copy", cascade="all, delete-orphan", order_by="BookEvent.created_at.desc()")

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    copy_id = db.Column(db.Integer, db.ForeignKey("book_copy.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    issued_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_at = db.Column(db.DateTime, nullable=False)
    returned_at = db.Column(db.DateTime)
    returned_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    issue_condition = db.Column(db.String(40), default="Good")
    return_condition = db.Column(db.String(40))
    borrower = db.relationship("User", foreign_keys=[user_id])
    copy = db.relationship("BookCopy", backref=db.backref("loans", lazy=True))
    issuer = db.relationship("User", foreign_keys=[issued_by])
    returner = db.relationship("User", foreign_keys=[returned_by])

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default="waiting")
    notified_at = db.Column(db.DateTime)
    book = db.relationship("Book")
    user = db.relationship("User")

class BookEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    copy_id = db.Column(db.Integer, db.ForeignKey("book_copy.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    event_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    actor = db.relationship("User")

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    user = db.relationship("User")

@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.is_active else None

ALLOWED_EMAIL_DOMAINS = {"vvitu.ac.in", "vvit.net"}
ALLOWED_PROFILE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def valid_institution_email(email):
    email = (email or "").strip().lower()
    if email.count("@") != 1:
        return False
    local, domain = email.rsplit("@", 1)
    return bool(local) and domain in ALLOWED_EMAIL_DOMAINS

def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def staff_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if current_user.role not in ("librarian", "admin"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

def log_event(copy, event_type, details=""):
    db.session.add(BookEvent(copy_id=copy.id, actor_id=current_user.id if current_user.is_authenticated else None,
                             event_type=event_type, details=details))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    unread = Notification.query.filter_by(user_id=current_user.id, read=False).count() if current_user.is_authenticated else 0
    return {"unread_notifications": unread, "today": date.today(),
            "profile_image_url": url_for("static", filename=current_user.profile_pic) if current_user.is_authenticated and current_user.profile_pic else None}

@app.route("/")
def home():
    total_titles = Book.query.count()
    total_copies = BookCopy.query.count()
    available = BookCopy.query.filter_by(status="available").count()
    recent = Book.query.order_by(Book.created_at.desc()).limit(6).all()
    return render_template("home.html", total_titles=total_titles, total_copies=total_copies, available=available, recent=recent)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated: return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter(db.func.lower(User.email) == email).first() if valid_institution_email(email) else None
        if user and user.is_active and user.check_password(request.form.get("password", "")):
            login_user(user)
            flash("Welcome back, " + user.name + ".", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not username or not valid_institution_email(email):
            flash("Use an institutional email ending in @vvitu.ac.in or @vvit.net.", "danger")
        elif User.query.filter((User.username == username) | (db.func.lower(User.email) == email)).first():
            flash("That username or email is already registered.", "warning")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            user = User(name=name, username=username, email=email, role="student")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Student account created successfully.", "success")
            return redirect(url_for("dashboard"))
    return render_template("register.html")

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            current_user.name = name
        image = request.files.get("profile_pic")
        if image and image.filename:
            ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
            if ext not in ALLOWED_PROFILE_EXTENSIONS:
                flash("Profile picture must be PNG, JPG or WEBP.", "danger")
                return redirect(url_for("profile"))
            import uuid
            filename = uuid.uuid4().hex + "." + ext
            image.save(os.path.join(app.config["PROFILE_FOLDER"], filename))
            current_user.profile_pic = "uploads/profiles/" + filename
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html")

@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        action = request.form.get("action", "")
        if action == "create":
            name = request.form.get("name", "").strip()
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            role = request.form.get("role", "student")
            password = request.form.get("password", "")
            if not name or not username or not valid_institution_email(email):
                flash("Enter a name, username and valid @vvitu.ac.in or @vvit.net email.", "danger")
            elif role not in ("student", "faculty", "librarian", "admin"):
                flash("Invalid account role.", "danger")
            elif len(password) < 8:
                flash("Temporary password must be at least 8 characters.", "danger")
            elif User.query.filter((User.username == username) | (db.func.lower(User.email) == email)).first():
                flash("Username or email already exists.", "warning")
            else:
                user = User(name=name, username=username, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash(f"{role.title()} account created.", "success")
            return redirect(url_for("admin_users"))
        user = db.session.get(User, request.form.get("user_id", type=int))
        if not user:
            flash("Account not found.", "danger")
        elif user.id == current_user.id:
            flash("You cannot change your own role or status here.", "warning")
        elif action == "role":
            role = request.form.get("role")
            if role in ("student", "faculty", "librarian", "admin"):
                user.role = role
                db.session.commit()
                flash("User role updated.", "success")
        elif action in ("activate", "deactivate"):
            user.is_active = action == "activate"
            db.session.commit()
            flash("Account status updated. User history is retained.", "success")
        return redirect(url_for("admin_users"))
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter((User.name.ilike(f"%{q}%")) | (User.username.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")))
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users, q=q)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role in ("admin", "librarian"):
        stats = {
            "titles": Book.query.count(),
            "copies": BookCopy.query.count(),
            "available": BookCopy.query.filter_by(status="available").count(),
            "issued": BookCopy.query.filter_by(status="issued").count(),
            "students": User.query.filter_by(role="student").count(),
            "reservations": Reservation.query.filter_by(status="waiting").count()
        }
        recent_loans = Loan.query.order_by(Loan.issued_at.desc()).limit(8).all()
        return render_template("dashboard.html", stats=stats, recent_loans=recent_loans)
    loans = Loan.query.filter_by(user_id=current_user.id, returned_at=None).order_by(Loan.due_at).all()
    reservations = Reservation.query.filter_by(user_id=current_user.id, status="waiting").all()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    return render_template("student_dashboard.html", loans=loans, reservations=reservations, notifications=notifications)

@app.route("/books")
def books():
    q = request.args.get("q", "").strip()
    availability = request.args.get("availability", "all")
    query = Book.query
    if q:
        matching_ids = [r[0] for r in db.session.query(BookCopy.book_id).filter(
            (BookCopy.acc_no.ilike(f"%{q}%")) | (BookCopy.barcode_value.ilike(f"%{q}%"))).distinct().all()]
        query = query.filter((Book.title.ilike(f"%{q}%")) | (Book.author.ilike(f"%{q}%")) |
                             (Book.isbn.ilike(f"%{q}%")) | (Book.call_no.ilike(f"%{q}%")) |
                             (Book.subject.ilike(f"%{q}%")) | (Book.id.in_(matching_ids)))
    results = query.order_by(Book.title).all()
    if availability == "available":
        results = [b for b in results if any(c.status == "available" for c in b.copies)]
    elif availability == "issued":
        results = [b for b in results if b.copies and all(c.status == "issued" for c in b.copies)]
    return render_template("books.html", books=results, q=q, availability=availability)

@app.route("/book/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    copies = BookCopy.query.filter_by(book_id=book.id).order_by(BookCopy.acc_no).all()
    waiting = Reservation.query.filter_by(book_id=book.id, status="waiting").count()
    return render_template("book_detail.html", book=book, copies=copies, waiting=waiting)

@app.route("/copy/<int:copy_id>")
@login_required
def copy_detail(copy_id):
    copy = BookCopy.query.get_or_404(copy_id)
    events = BookEvent.query.filter_by(copy_id=copy.id).order_by(BookEvent.created_at.desc()).all()
    loans = Loan.query.filter_by(copy_id=copy.id).order_by(Loan.issued_at.desc()).all()
    return render_template("copy_detail.html", copy=copy, events=events, loans=loans)

@app.route("/reserve/<int:book_id>", methods=["POST"])
@login_required
def reserve(book_id):
    book = Book.query.get_or_404(book_id)
    if Reservation.query.filter_by(book_id=book.id, user_id=current_user.id, status="waiting").first():
        flash("You already have an active reservation for this title.", "warning")
    else:
        db.session.add(Reservation(book_id=book.id, user_id=current_user.id))
        db.session.commit()
        flash("Reservation added to the waiting queue.", "success")
    return redirect(url_for("book_detail", book_id=book.id))

@app.route("/reservation/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def cancel_reservation(reservation_id):
    r = Reservation.query.get_or_404(reservation_id)
    if r.user_id != current_user.id and current_user.role not in ("admin", "librarian"): abort(403)
    r.status = "cancelled"
    db.session.commit()
    flash("Reservation cancelled.", "info")
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/scanner")
@staff_required
def scanner():
    return render_template("scanner.html")

@app.route("/api/lookup/<acc_no>")
@staff_required
def lookup_accession(acc_no):
    acc_no = (acc_no or "").strip()
    copy = BookCopy.query.filter_by(acc_no=acc_no).first() or BookCopy.query.filter_by(barcode_value=acc_no).first()
    if not copy: return jsonify({"found": False}), 404
    active = Loan.query.filter_by(copy_id=copy.id, returned_at=None).first()
    return jsonify({"found": True, "id": copy.id, "acc_no": copy.acc_no, "title": copy.book.title,
                    "author": copy.book.author, "status": copy.status, "condition": copy.condition,
                    "borrower": active.borrower.name if active else None,
                    "due": active.due_at.strftime("%d %b %Y") if active else None,
                    "url": url_for("copy_detail", copy_id=copy.id)})

@app.route("/manage")
@staff_required
def manage():
    copies = BookCopy.query.order_by(BookCopy.created_at.desc()).limit(100).all()
    users = User.query.order_by(User.name).all()
    return render_template("manage.html", copies=copies, users=users)

@app.route("/add-book", methods=["GET", "POST"])
@staff_required
def add_book():
    if request.method == "POST":
        acc = request.form.get("acc_no", "").strip()
        if not acc:
            flash("ACC.NO is required.", "danger")
            return redirect(url_for("add_book"))
        if BookCopy.query.filter((BookCopy.acc_no == acc) | (BookCopy.barcode_value == acc)).first():
            flash("That ACC.NO/barcode is already registered. Open the existing copy instead.", "warning")
            return redirect(url_for("add_book"))
        title = request.form.get("title", "").strip()
        if not title:
            flash("Book title is required.", "danger")
            return redirect(url_for("add_book"))
        book = Book.query.filter_by(title=title, author=request.form.get("author", "").strip(),
                                    isbn=request.form.get("isbn", "").strip()).first()
        if not book:
            book = Book(title=title, author=request.form.get("author", "").strip(),
                        publisher=request.form.get("publisher", "").strip(), isbn=request.form.get("isbn", "").strip(),
                        edition=request.form.get("edition", "").strip(), subject=request.form.get("subject", "").strip(),
                        department=request.form.get("department", "").strip(), call_no=request.form.get("call_no", "").strip(),
                        description=request.form.get("description", "").strip())
            db.session.add(book)
            db.session.flush()
        else:
            # Fill missing master metadata without overwriting existing details.
            for field in ("publisher", "edition", "subject", "department", "call_no", "description"):
                value = request.form.get(field, "").strip()
                if value and not getattr(book, field): setattr(book, field, value)
        acquired = request.form.get("acquisition_date")
        price = request.form.get("purchase_price")
        copy = BookCopy(book_id=book.id, acc_no=acc, barcode_value=acc,
                        shelf=request.form.get("shelf", "").strip(),
                        condition=request.form.get("condition", "Good"),
                        acquisition_date=date.fromisoformat(acquired) if acquired else date.today(),
                        purchase_price=float(price) if price else None,
                        vendor=request.form.get("vendor", "").strip())
        db.session.add(copy)
        db.session.flush()
        log_event(copy, "REGISTERED", "Physical copy registered with ACC.NO " + acc)
        db.session.commit()
        flash("Book copy registered successfully.", "success")
        return redirect(url_for("copy_detail", copy_id=copy.id))
    return render_template("add_book.html")

@app.route("/issue", methods=["GET", "POST"])
@staff_required
def issue():
    if request.method == "POST":
        acc = request.form.get("acc_no", "").strip()
        username = request.form.get("username", "").strip()
        copy = BookCopy.query.filter_by(acc_no=acc).first()
        user = User.query.filter_by(username=username).first()
        if not copy or not user:
            flash("Book accession number or borrower account was not found.", "danger")
        elif copy.status != "available":
            flash("This physical copy is not available for issue.", "warning")
        elif user.role not in ("student", "faculty"):
            flash("Select a student or faculty account.", "danger")
        else:
            loan = Loan(copy_id=copy.id, user_id=user.id, issued_by=current_user.id,
                        due_at=datetime.utcnow() + timedelta(days=14), issue_condition=copy.condition)
            copy.status = "issued"
            db.session.add(loan)
            log_event(copy, "ISSUED", f"Issued to {user.name} ({user.username}); due {loan.due_at:%d %b %Y}")
            db.session.add(Notification(user_id=user.id, message=f"{copy.book.title} (ACC.NO {copy.acc_no}) was issued to you. Due {loan.due_at:%d %b %Y}."))
            db.session.commit()
            flash("Book issued successfully.", "success")
            return redirect(url_for("copy_detail", copy_id=copy.id))
    users = User.query.filter(User.role.in_(["student", "faculty"])).order_by(User.name).all()
    return render_template("issue.html", users=users)

@app.route("/return-book", methods=["GET", "POST"])
@staff_required
def return_book():
    if request.method == "POST":
        acc = request.form.get("acc_no", "").strip()
        copy = BookCopy.query.filter_by(acc_no=acc).first()
        loan = Loan.query.filter_by(copy_id=copy.id, returned_at=None).first() if copy else None
        if not copy or not loan:
            flash("No active loan found for that ACC.NO.", "danger")
        else:
            condition = request.form.get("condition", copy.condition)
            loan.returned_at = datetime.utcnow()
            loan.returned_by = current_user.id
            loan.return_condition = condition
            copy.condition = condition
            copy.status = "available" if condition.lower() not in ("lost", "damaged beyond repair", "withdrawn") else "unavailable"
            log_event(copy, "RETURNED", f"Returned by {loan.borrower.name}; condition: {condition}")
            db.session.add(Notification(user_id=loan.user_id, message=f"Return recorded for {copy.book.title} (ACC.NO {copy.acc_no})."))
            # Notify first waiting student when a copy becomes available.
            if copy.status == "available":
                reservation = Reservation.query.filter_by(book_id=copy.book_id, status="waiting").order_by(Reservation.created_at).first()
                if reservation:
                    reservation.status = "ready"
                    reservation.notified_at = datetime.utcnow()
                    db.session.add(Notification(user_id=reservation.user_id, message=f"A copy of {copy.book.title} is available. Please contact the library to collect it."))
            db.session.commit()
            flash("Book return processed and history updated.", "success")
            return redirect(url_for("copy_detail", copy_id=copy.id))
    return render_template("return.html")

@app.route("/digital", methods=["GET", "POST"])
@login_required
def digital():
    if request.method == "POST":
        if current_user.role not in ("admin", "librarian"):
            abort(403)
        file = request.files.get("file")
        if not file or not file.filename or not allowed_file(file.filename):
            flash("Upload a PDF or EPUB file.", "danger")
        else:
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            flash("Digital resource uploaded.", "success")
            return redirect(url_for("digital"))
    files = sorted([f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.lower().endswith((".pdf", ".epub"))])
    return render_template("digital.html", files=files)

@app.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

@app.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in items: n.read = True
    db.session.commit()
    return render_template("notifications.html", items=items)

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])
    copies = BookCopy.query.filter((BookCopy.acc_no.ilike(f"%{q}%")) | (BookCopy.barcode_value.ilike(f"%{q}%"))).limit(10).all()
    exact = [{"type": "copy", "label": f"{c.acc_no} · {c.book.title}", "url": url_for("copy_detail", copy_id=c.id) if current_user.is_authenticated else url_for("book_detail", book_id=c.book_id)} for c in copies]
    titles = Book.query.filter((Book.title.ilike(f"%{q}%")) | (Book.author.ilike(f"%{q}%")) | (Book.isbn.ilike(f"%{q}%"))).limit(10).all()
    exact += [{"type": "book", "label": f"{b.title} · {b.author}", "url": url_for("book_detail", book_id=b.id)} for b in titles]
    return jsonify(exact[:12])

@app.errorhandler(403)
def forbidden(e): return render_template("error.html", code=403, message="You don't have permission to access this page."), 403
@app.errorhandler(404)
def not_found(e): return render_template("error.html", code=404, message="The page or record could not be found."), 404

def seed():
    if not User.query.filter_by(username="admin").first():
        admin = User(name="Library Administrator", username="admin", email="admin@vvitu.ac.in", role="admin")
        admin.set_password("Admin@123")
        librarian = User(name="Demo Librarian", username="librarian", email="librarian@vvitu.ac.in", role="librarian")
        librarian.set_password("Lib@123")
        student = User(name="Demo Student", username="student", email="student@vvitu.ac.in", role="student")
        student.set_password("Student@123")
        db.session.add_all([admin, librarian, student])
        db.session.commit()
    if Book.query.count() == 0:
        b = Book(title="Complex Variables and Linear Algebra", author="Example Author", publisher="Academic Press",
                 isbn="9780000000001", edition="1st", subject="Engineering Mathematics", department="CSE",
                 call_no="515.84 TYE", description="Sample catalogue record. Replace with verified library metadata.")
        db.session.add(b); db.session.flush()
        for acc in ("160553", "160554"):
            c = BookCopy(book_id=b.id, acc_no=acc, barcode_value=acc, shelf="Central Library", condition="Good")
            db.session.add(c); db.session.flush()
            db.session.add(BookEvent(copy_id=c.id, event_type="REGISTERED", details=f"Demo seed copy {acc}"))
        db.session.commit()

def add_missing_user_columns():
    """Small additive compatibility migration for databases created by older ZIP builds."""
    inspector = db.inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("user")}
    dialect = db.engine.dialect.name
    additions = []
    if "profile_pic" not in existing:
        additions.append('ALTER TABLE "user" ADD COLUMN profile_pic VARCHAR(255) DEFAULT \'\'')
    if "is_active" not in existing:
        default = "TRUE" if dialect == "postgresql" else "1"
        additions.append(f'ALTER TABLE "user" ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT {default}')
    for statement in additions:
        db.session.execute(text(statement))
    if additions:
        db.session.commit()
    # Update only the three bundled demo accounts from the previous prototype domain.
    db.session.execute(text("UPDATE \"user\" SET email = 'admin@vvitu.ac.in' WHERE username = 'admin' AND email = 'admin@vvitu.edu.in'"))
    db.session.execute(text("UPDATE \"user\" SET email = 'librarian@vvitu.ac.in' WHERE username = 'librarian' AND email = 'librarian@vvitu.edu.in'"))
    db.session.execute(text("UPDATE \"user\" SET email = 'student@vvitu.ac.in' WHERE username = 'student' AND email = 'student@vvitu.edu.in'"))
    db.session.commit()

with app.app_context():
    db.create_all()
    add_missing_user_columns()
    seed()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
