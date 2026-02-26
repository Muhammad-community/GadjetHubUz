from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import os

app = Flask(__name__)
# Secret key for session management
app.secret_key = os.urandom(24)

DB_PATH = "/tmp/database.db"

# ─── Database Setup ───────────────────────────────────────────────────────────

def get_db():
    """Opens a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates tables if they don't already exist."""
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                listing_type TEXT NOT NULL,  -- 'sell' or 'buy'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

# ─── Helper Functions ─────────────────────────────────────────────────────────

def hash_password(password):
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def current_user():
    """Returns the currently logged-in user dict or None."""
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    return user

def login_required(fn):
    """Decorator that redirects to login page if user is not authenticated."""
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Iltimos, avval tizimga kiring.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# ─── Context Processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_user():
    """Makes `user` available in every template automatically."""
    return {"user": current_user()}

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home page – showcases gadget cards."""
    # Hardcoded sample gadgets for display
    gadgets = [
        {"id": 1, "name": "SmartPhone X12 Pro", "price": 4_599_000, "img": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&q=80", "badge": "Yangi", "rating": 4.8},
        {"id": 2, "name": "AirBuds Neo", "price": 899_000, "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400&q=80", "badge": "Top Sotuv", "rating": 4.6},
        {"id": 3, "name": "4K UltraTab", "price": 3_299_000, "img": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&q=80", "badge": "Chegirma", "rating": 4.7},
        {"id": 4, "name": "SmartWatch Series 9", "price": 1_450_000, "img": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400&q=80", "badge": "Trend", "rating": 4.9},
        {"id": 5, "name": "NoiseCam 360", "price": 2_100_000, "img": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400&q=80", "badge": "Yangi", "rating": 4.5},
        {"id": 6, "name": "PowerHub Pro", "price": 650_000, "img": "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400&q=80", "badge": "Mashhur", "rating": 4.4},
    ]
    return render_template("index.html", gadgets=gadgets)

@app.route("/about")
def about():
    """About us page."""
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    """Contact page – saves messages to DB."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if name and email and message:
            with get_db() as db:
                db.execute(
                    "INSERT INTO messages (name, email, message) VALUES (?, ?, ?)",
                    (name, email, message)
                )
                db.commit()
            flash("Xabaringiz muvaffaqiyatli yuborildi!", "success")
            return redirect(url_for("contact"))
        else:
            flash("Iltimos, barcha maydonlarni to'ldiring.", "danger")
    return render_template("contact.html")

@app.route("/pricing")
def pricing():
    """Pricing / subscription plans page."""
    plans = [
        {"name": "Bepul", "price": 0, "features": ["5 ta vazifa", "Asosiy do'kon", "Email qo'llab-quvvatlash"], "color": "secondary"},
        {"name": "Pro", "price": 79_000, "features": ["Cheksiz vazifalar", "Bozorga kirish", "24/7 qo'llab-quvvatlash", "Analitika paneli"], "color": "primary", "popular": True},
        {"name": "Biznes", "price": 199_000, "features": ["Hamma Pro imkoniyatlar", "API kirish", "Maxsus menejer", "SLA kafolat"], "color": "dark"},
    ]
    return render_template("pricing.html", plans=plans)

@app.route("/marketplace", methods=["GET", "POST"])
@login_required
def marketplace():
    """Buy/sell listings page – only for authenticated users."""
    db = get_db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", 0)
        listing_type = request.form.get("listing_type", "sell")
        if title and price:
            db.execute(
                "INSERT INTO listings (user_id, title, description, price, listing_type) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], title, description, float(price), listing_type)
            )
            db.commit()
            flash("E'lon muvaffaqiyatli joylashtirildi!", "success")
            return redirect(url_for("marketplace"))
        else:
            flash("Sarlavha va narx majburiy.", "danger")

    listings = db.execute(
        "SELECT l.*, u.username FROM listings l JOIN users u ON l.user_id = u.id ORDER BY l.created_at DESC"
    ).fetchall()
    return render_template("marketplace.html", listings=listings)

@app.route("/marketplace/delete/<int:listing_id>", methods=["POST"])
@login_required
def delete_listing(listing_id):
    """Deletes a listing belonging to the current user."""
    with get_db() as db:
        db.execute(
            "DELETE FROM listings WHERE id = ? AND user_id = ?",
            (listing_id, session["user_id"])
        )
        db.commit()
    flash("E'lon o'chirildi.", "info")
    return redirect(url_for("marketplace"))

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration route."""
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not (username and email and password):
            flash("Barcha maydonlar to'ldirilishi shart.", "danger")
        elif password != confirm:
            flash("Parollar mos kelmayapti.", "danger")
        elif len(password) < 6:
            flash("Parol kamida 6 ta belgidan iborat bo'lishi kerak.", "danger")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                        (username, email, hash_password(password))
                    )
                    db.commit()
                flash("Ro'yxatdan muvaffaqiyatli o'tdingiz! Iltimos, tizimga kiring.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Bu foydalanuvchi nomi yoki email allaqachon mavjud.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login route."""
    if current_user():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (email, hash_password(password))
        ).fetchone()
        if user:
            session["user_id"] = user["id"]
            flash(f"Xush kelibsiz, {user['username']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Email yoki parol noto'g'ri.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Clears the session and logs the user out."""
    session.clear()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for("index"))

# ─── Dashboard / To-Do Routes ─────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing their To-Do list."""
    db = get_db()
    tasks = db.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()
    done_count = sum(1 for t in tasks if t["done"])
    return render_template("dashboard.html", tasks=tasks, done_count=done_count)

@app.route("/task/add", methods=["POST"])
@login_required
def add_task():
    """Adds a new task for the current user."""
    title = request.form.get("title", "").strip()
    if title:
        with get_db() as db:
            db.execute(
                "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
                (session["user_id"], title)
            )
            db.commit()
    else:
        flash("Vazifa matni bo'sh bo'lishi mumkin emas.", "warning")
    return redirect(url_for("dashboard"))

@app.route("/task/toggle/<int:task_id>", methods=["POST"])
@login_required
def toggle_task(task_id):
    """Toggles a task's done/undone status."""
    with get_db() as db:
        db.execute(
            "UPDATE tasks SET done = 1 - done WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        )
        db.commit()
    return redirect(url_for("dashboard"))

@app.route("/task/delete/<int:task_id>", methods=["POST"])
@login_required
def delete_task(task_id):
    """Deletes a task belonging to the current user."""
    with get_db() as db:
        db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, session["user_id"])
        )
        db.commit()
    return redirect(url_for("dashboard"))

# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()  # Initialize DB on first run
    app.run(debug=True)
