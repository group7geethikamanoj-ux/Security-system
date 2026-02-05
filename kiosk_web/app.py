"""
app.py -- Flask dashboard that reads logs from Supabase (robust & beginner-friendly)
"""

from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3
import datetime
import requests
import logging

# -------------------------
# CONFIG - put your values here
# -------------------------
SUPABASE_URL = "https://aexgzuaxdfokyvzoadjk.supabase.co"   # your project URL (no /rest part)
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFleGd6dWF4ZGZva3l2em9hZGprIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkwMTg5NDQsImV4cCI6MjA4NDU5NDk0NH0.d9T2d_lV3ACH0RRwHoRI7BNiIZe7NW6zGW39TWpdmLM"

# REST endpoint base for logs
SUPABASE_REST = f"{SUPABASE_URL}/rest/v1/logs"

HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # helpful for inserts if you want created row back
}

# -------------------------
# Flask app
# -------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# remove SERVER_NAME or it may break local dev
# app.config["SERVER_NAME"] = "logbook.local:5000"

# -------------------------
# Logging configuration (prints helpful diagnostics to console)
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logbook")

# -------------------------
# Users (local sqlite only for auth)
# -------------------------
def init_users_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_default_user():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            ("admin", "Naga@7")
        )
        conn.commit()
    conn.close()

init_users_db()
create_default_user()

# -------------------------
# Supabase helper functions (safe)
# -------------------------
def fetch_logs():
    """
    Fetch all logs, newest first. Returns a list (could be empty).
    Failure -> returns [] and logs the error.
    """
    try:
        r = requests.get(f"{SUPABASE_REST}?select=*&order=timestamp.desc", headers=HEADERS, timeout=6)
        if r.status_code == 200:
            return r.json()
        else:
            logger.error("Supabase returned status %s: %s", r.status_code, r.text)
    except Exception as e:
        logger.exception("Error fetching logs from Supabase: %s", e)
    return []

def fetch_history():
    """
    Fetch logs where blacklist_status == 'Yes' OR final_status == 'Denied'
    Returns list or [] on error.
    """
    try:
        # OR filter: must be URL-safe; this is accepted by Supabase REST
        q = ("select=*&or=(blacklist_status.eq.Yes,final_status.eq.Denied)"
             "&order=timestamp.desc")
        r = requests.get(f"{SUPABASE_REST}?{q}", headers=HEADERS, timeout=6)
        if r.status_code == 200:
            return r.json()
        else:
            logger.error("Supabase history returned %s: %s", r.status_code, r.text)
    except Exception as e:
        logger.exception("Error fetching history from Supabase: %s", e)
    return []

def insert_log_to_cloud(data):
    """
    Example server-side insertion wrapper (not required if Pi sends directly).
    Returns True when inserted (201) else False.
    """
    try:
        # Add timestamp if missing
        if "timestamp" not in data:
            data["timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        r = requests.post(SUPABASE_REST, headers=HEADERS, json=data, timeout=6)
        if r.status_code in (201, 200):
            return True
        logger.error("Insert failed %s: %s", r.status_code, r.text)
    except Exception as e:
        logger.exception("Error inserting to Supabase: %s", e)
    return False

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    return render_template("splash.html")

@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()

    if user:
        session["user"] = username
        return redirect(url_for("dashboard"))

    return "Incorrect username or password", 401

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("dashboard.html")

# Endpoint the Pi/PC could use if you prefer app-as-api (optional)
@app.route("/add_log", methods=["POST"])
def add_log():
    if not request.is_json:
        return jsonify({"error": "JSON required"}), 400
    data = request.get_json()
    ok = insert_log_to_cloud(data)
    if ok:
        return jsonify({"message": "saved"}), 201
    else:
        return jsonify({"error": "cloud save failed"}), 500

@app.route("/logs")
def view_logs():
    try:
        logs = fetch_logs() or []
        # ensure we pass a list of dictionaries to template
        return render_template("logs.html", logs=logs)
    except Exception as e:
        logger.exception("Unexpected error in /logs: %s", e)
        return f"Error loading logs: {e}", 500

@app.route("/history")
def history():
    try:
        logs = fetch_history() or []
        return render_template("history.html", logs=logs)
    except Exception as e:
        logger.exception("Unexpected error in /history: %s", e)
        return f"Error loading history: {e}", 500

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# -------------------------
# Run (debug=True for dev)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
