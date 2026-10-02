from datetime import date
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__)
app.secret_key = "local-hospital-dashboard"
DATABASE = Path(__file__).with_name("hospital.db")


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                doctor TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Scheduled'
            );
            """
        )


@app.route("/")
def dashboard():
    search = request.args.get("search", "").strip()
    with get_db() as connection:
        total_patients = connection.execute(
            "SELECT COUNT(*) FROM patients"
        ).fetchone()[0]
        today_appointments = connection.execute(
            "SELECT COUNT(*) FROM appointments WHERE appointment_date = ?",
            (date.today().isoformat(),),
        ).fetchone()[0]
        patient_rows = connection.execute(
            """SELECT p.*, COUNT(a.id) AS visits
               FROM patients p LEFT JOIN appointments a ON a.patient_id = p.id
               WHERE p.name LIKE ? OR p.phone LIKE ?
               GROUP BY p.id ORDER BY p.id DESC LIMIT 8""",
            (f"%{search}%", f"%{search}%"),
        ).fetchall()
        patient_options = connection.execute(
            "SELECT id, name FROM patients ORDER BY name"
        ).fetchall()
        appointment_rows = connection.execute(
            """SELECT a.*, p.name AS patient_name
               FROM appointments a JOIN patients p ON p.id = a.patient_id
               ORDER BY a.appointment_date, a.appointment_time LIMIT 8"""
        ).fetchall()
        departments = connection.execute(
            "SELECT DISTINCT department FROM appointments ORDER BY department"
        ).fetchall()
    return render_template(
        "index.html",
        patients=patient_rows,
        patient_options=patient_options,
        appointments=appointment_rows,
        total_patients=total_patients,
        today_appointments=today_appointments,
        search=search,
        departments=[row[0] for row in departments],
        today=date.today().isoformat(),
        today_label=date.today().strftime("%A, %B %d, %Y").upper(),
    )


@app.post("/patients")
def add_patient():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()
    if not name or not phone or not age.isdigit() or gender not in {"Female", "Male", "Other"}:
        flash("Please enter valid patient details.", "error")
        return redirect(url_for("dashboard"))
    with get_db() as connection:
        connection.execute(
            "INSERT INTO patients (name, phone, age, gender) VALUES (?, ?, ?, ?)",
            (name, phone, int(age), gender),
        )
    flash(f"{name} added to the patient register.", "success")
    return redirect(url_for("dashboard"))


@app.post("/appointments")
def add_appointment():
    patient_id = request.form.get("patient_id", "")
    doctor = request.form.get("doctor", "").strip()
    department = request.form.get("department", "").strip()
    appointment_date = request.form.get("appointment_date", "")
    appointment_time = request.form.get("appointment_time", "")
    if not all((patient_id, doctor, department, appointment_date, appointment_time)):
        flash("Please complete every appointment field.", "error")
        return redirect(url_for("dashboard"))
    with get_db() as connection:
        patient = connection.execute(
            "SELECT id FROM patients WHERE id = ?", (patient_id,)
        ).fetchone()
        if patient is None:
            flash("Select a patient from the register first.", "error")
            return redirect(url_for("dashboard"))
        connection.execute(
            """INSERT INTO appointments
               (patient_id, doctor, department, appointment_date, appointment_time)
               VALUES (?, ?, ?, ?, ?)""",
            (patient_id, doctor, department, appointment_date, appointment_time),
        )
    flash("Appointment scheduled.", "success")
    return redirect(url_for("dashboard"))


@app.post("/appointments/<int:appointment_id>/complete")
def complete_appointment(appointment_id):
    with get_db() as connection:
        connection.execute(
            "UPDATE appointments SET status = 'Completed' WHERE id = ?",
            (appointment_id,),
        )
    flash("Appointment marked as completed.", "success")
    return redirect(url_for("dashboard"))


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)