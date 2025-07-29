# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import os
from flask import Response
import csv
import io

app = Flask(__name__)
app.secret_key = "supersecretkey"  # άλλαξέ το αν το κάνεις public

DB_FILE = "db.sqlite3"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # Events
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (user, pwd))
        result = c.fetchone()
        conn.close()
        if result:
            session["user_id"] = result[0]
            session["username"] = user
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (user, pwd))
            conn.commit()
            flash("Account created. You can log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, date FROM events WHERE user_id = ?", (session["user_id"],))
    rows = c.fetchall()
    conn.close()

    events = []
    for event_id, title, date_str in rows:
        try:
            expired = datetime.strptime(date_str, "%Y-%m-%d").date() < datetime.today().date()
        except:
            expired = False
        events.append({
            "id": event_id,
            "title": title,
            "date": date_str,
            "expired": expired
        })

    return render_template("dashboard.html", username=session["username"], events=events)

@app.route("/add", methods=["GET", "POST"])
def add_event():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        date = request.form["date"]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO events (user_id, title, date) VALUES (?, ?, ?)",
                  (session["user_id"], title, date))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))

    return render_template("add_event.html")

@app.route("/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, session["user_id"]))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/export")
def export_events():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT title, date FROM events WHERE user_id = ?", (session["user_id"],))
    rows = c.fetchall()
    conn.close()

    # Δημιουργία CSV σε μνήμη
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Date"])
    writer.writerows(rows)

    # Προετοιμασία response
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=events.csv"
    return response

    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



def home():
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
