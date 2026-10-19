from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    role = SelectField(
        "I am signing up as",
        choices=[("respondent", "Respondent (take surveys)"), ("admin", "Admin (create surveys)")],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")

class SurveyForm(FlaskForm):
    title = StringField("Survey title", validators=[DataRequired(), Length(max=200)])
    submit = SubmitField("Create survey")


class QuestionForm(FlaskForm):
    text = StringField("Question", validators=[DataRequired(), Length(max=500)])
    question_type = SelectField(
        "Answer type",
        choices=[("rating", "Rating (1–5)"), ("text", "Short text")],
    )
    submit = SubmitField("Add question")