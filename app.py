import os

from dotenv import load_dotenv
from flask import Flask

from models import db

load_dotenv()  # reads your .env file

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]

db.init_app(app)  # connects the database to this app


@app.cli.command("init-db")
def init_db():
    """Create all database tables from the models."""
    db.create_all()
    print("Database tables created.")


@app.route("/")
def home():
    return "Survey app is running!"