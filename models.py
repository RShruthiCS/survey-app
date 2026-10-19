from datetime import datetime, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    """Current time in UTC, used as the default for timestamp columns."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="respondent")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    surveys = db.relationship("Survey", back_populates="creator")
    responses = db.relationship("Response", back_populates="user")

    __table_args__ = (
        db.CheckConstraint("role IN ('admin', 'respondent')", name="valid_role"),
    )


class Survey(db.Model):
    __tablename__ = "surveys"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    creator = db.relationship("User", back_populates="surveys")
    questions = db.relationship(
    "Question", back_populates="survey", cascade="all, delete-orphan", order_by="Question.id"
    )


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey("surveys.id"), nullable=False)
    text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(10), nullable=False)  # 'rating' or 'text'

    survey = db.relationship("Survey", back_populates="questions")
    responses = db.relationship(
        "Response", back_populates="question", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.CheckConstraint(
            "question_type IN ('rating', 'text')", name="valid_question_type"
        ),
    )


class Response(db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating_value = db.Column(db.Integer)  # filled for rating questions
    text_value = db.Column(db.Text)       # filled for text questions
    submitted_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    question = db.relationship("Question", back_populates="responses")
    user = db.relationship("User", back_populates="responses")

    __table_args__ = (
        db.UniqueConstraint("question_id", "user_id", name="one_answer_per_question"),
        db.CheckConstraint(
            "rating_value IS NULL OR (rating_value BETWEEN 1 AND 5)",
            name="valid_rating",
        ),
    )