# Survey & Feedback Platform

A full-stack web app where admins create surveys, respondents submit answers,
and results appear on a dashboard with charts.

**Status:** In progress

## Tech Stack
Flask · PostgreSQL · SQLAlchemy · Flask-Login · Chart.js

## Planned Features
- [ ] User sign-up and login with admin/respondent roles
- [ ] Create surveys with rating and text questions
- [ ] Submit responses (one per user)
- [ ] Results dashboard with charts

## Setup
1. Clone the repo and create a virtual environment
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your values
4. `flask --app app run`