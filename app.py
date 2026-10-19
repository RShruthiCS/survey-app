import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from forms import LoginForm, RegistrationForm
from models import User, db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

db.init_app(app)

# --- Login setup ---------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # where @login_required sends logged-out users
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login calls this on every request to get the logged-in user."""
    return db.session.get(User, int(user_id))


def admin_required(view):
    """Only let logged-in admins into a page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if current_user.role != "admin":
            abort(403)  # 403 = Forbidden
        return view(*args, **kwargs)
    return wrapped


# --- CLI command ---------------------------------------------------------
@app.cli.command("init-db")
def init_db():
    """Create all database tables from the models."""
    db.create_all()
    print("Database tables created.")


# --- Routes ----------------------------------------------------------------
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html", form=form)

        user = User(
            email=email,
            password_hash=generate_password_hash(form.password.data),
            role=form.role.data,
        )
        db.session.add(user)
        db.session.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/admin-test")
@admin_required
def admin_test():
    """Temporary page to check that role protection works. Remove in Step 4."""
    return "Only admins can see this page."