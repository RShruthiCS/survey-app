import os
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from forms import LoginForm, QuestionForm, RegistrationForm, SurveyForm
from models import Question, Response, Survey, User, db

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

db.init_app(app)
csrf = CSRFProtect(app)  # CSRF protection for every form, including hand-written ones

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


def completed_survey_ids(user_id):
    """IDs of surveys this user has already answered."""
    rows = (
        db.session.query(Question.survey_id)
        .join(Response, Response.question_id == Question.id)
        .filter(Response.user_id == user_id)
        .distinct()
        .all()
    )
    return {row.survey_id for row in rows}


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
            password_hash=generate_password_hash(form.password.data, method="pbkdf2:sha256"),
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
    if current_user.role == "admin":
        surveys = (
            Survey.query.filter_by(created_by=current_user.id)
            .order_by(Survey.created_at.desc())
            .all()
        )
        return render_template("dashboard.html", surveys=surveys)

    # Respondents: every survey that has at least one question
    surveys = (
        Survey.query.filter(Survey.questions.any())
        .order_by(Survey.created_at.desc())
        .all()
    )
    completed_ids = completed_survey_ids(current_user.id)
    return render_template("dashboard.html", surveys=surveys, completed_ids=completed_ids)


# --- Survey creation (admins only) -----------------------------------------
@app.route("/surveys/new", methods=["GET", "POST"])
@admin_required
def create_survey():
    form = SurveyForm()
    if form.validate_on_submit():
        survey = Survey(title=form.title.data.strip(), created_by=current_user.id)
        db.session.add(survey)
        db.session.commit()
        flash("Survey created. Now add some questions.", "success")
        return redirect(url_for("edit_survey", survey_id=survey.id))
    return render_template("create_survey.html", form=form)


@app.route("/surveys/<int:survey_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_survey(survey_id):
    survey = db.get_or_404(Survey, survey_id)
    if survey.created_by != current_user.id:
        abort(403)  # admins can only edit their own surveys

    form = QuestionForm()
    if form.validate_on_submit():
        question = Question(
            survey_id=survey.id,
            text=form.text.data.strip(),
            question_type=form.question_type.data,
        )
        db.session.add(question)
        db.session.commit()
        flash("Question added.", "success")
        return redirect(url_for("edit_survey", survey_id=survey.id))

    return render_template("edit_survey.html", survey=survey, form=form)


# --- Taking surveys (respondents only) -------------------------------------
MAX_TEXT_LENGTH = 1000


@app.route("/surveys/<int:survey_id>/take", methods=["GET", "POST"])
@login_required
def take_survey(survey_id):
    if current_user.role != "respondent":
        abort(403)

    survey = db.get_or_404(Survey, survey_id)
    if not survey.questions:
        abort(404)

    if survey.id in completed_survey_ids(current_user.id):
        flash("You've already completed this survey.", "info")
        return redirect(url_for("dashboard"))

    answers = {}  # what the user typed, so we can refill the form on errors
    errors = {}   # question.id -> error message

    if request.method == "POST":
        for question in survey.questions:
            raw = request.form.get(f"q_{question.id}", "").strip()
            answers[question.id] = raw

            if question.question_type == "rating":
                if raw not in {"1", "2", "3", "4", "5"}:
                    errors[question.id] = "Please choose a rating from 1 to 5."
            else:
                if not raw:
                    errors[question.id] = "Please write an answer."
                elif len(raw) > MAX_TEXT_LENGTH:
                    errors[question.id] = f"Please keep it under {MAX_TEXT_LENGTH} characters."

        if not errors:
            for question in survey.questions:
                value = answers[question.id]
                db.session.add(
                    Response(
                        question_id=question.id,
                        user_id=current_user.id,
                        rating_value=int(value) if question.question_type == "rating" else None,
                        text_value=value if question.question_type == "text" else None,
                    )
                )
            try:
                db.session.commit()
            except IntegrityError:
                # The UNIQUE(question_id, user_id) constraint caught a duplicate,
                # e.g. the user double-clicked Submit.
                db.session.rollback()
                flash("You've already completed this survey.", "info")
                return redirect(url_for("dashboard"))

            flash(f"Thanks! Your answers to \"{survey.title}\" were submitted.", "success")
            return redirect(url_for("dashboard"))

        flash("Please answer every question.", "danger")

    return render_template("take_survey.html", survey=survey, answers=answers, errors=errors)