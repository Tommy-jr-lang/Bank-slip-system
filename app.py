from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

API_KEY = os.getenv("API_KEY")

students = {}
submissions = []

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")

# ---------------- STUDENT ----------------
@app.route("/student")
def student():
    return render_template("student_form.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.form
    students[data["regno"]] = data
    session["user"] = data["regno"]
    return redirect(url_for("dashboard"))

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))

    regno = session["user"]
    student = students.get(regno)

    user_subs = [s for s in submissions if s["regno"] == regno]

    return render_template("dashboard.html", student=student, regno=regno, submissions=user_subs)

# ---------------- UPLOAD ----------------
@app.route("/upload")
def upload():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("upload.html")

# ---------------- OCR + VERIFY ----------------
@app.route("/submit-slip", methods=["POST"])
def submit_slip():
    if "user" not in session:
        return redirect(url_for("home"))

    file = request.files.get("slip")
    if not file or file.filename == "":
        flash("No file selected")
        return redirect(url_for("upload"))

    filename = secure_filename(file.filename)
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(path)

    regno = session["user"]
    student = students.get(regno)

    # OCR
    with open(path, "rb") as f:
        res = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": f},
            data={"apikey": API_KEY}
        ).json()

    text = ""
    if "ParsedResults" in res:
        text = res["ParsedResults"][0]["ParsedText"].lower()

    # -------- VALIDATION --------
    status = "Pending"
    amount_detected = "Unknown"

    if text == "":
        status = "Not Clear"
        flash("Slip not clear!")

    elif student["fullname"].lower() in text and regno.lower() in text:
        status = "Verified"
        flash("Slip verified successfully!")

    else:
        status = "Fake"
        flash("Slip does not match your details!")

    # -------- AMOUNT DETECTION --------
    import re
    amounts = re.findall(r'\d+\.\d{2}', text)
    if amounts:
        amount_detected = max(amounts)

    # -------- DUPLICATE CHECK --------
    for s in submissions:
        if s["filename"] == filename:
            status = "Duplicate"
            flash("Duplicate slip detected!")

    submissions.append({
        "fullname": student["fullname"],
        "regno": regno,
        "filename": filename,
        "date": datetime.now().strftime("%d-%m-%Y"),
        "time": datetime.now().strftime("%H:%M"),
        "status": status,
        "amount": amount_detected
    })

    return redirect(url_for("dashboard"))

# ---------------- ADMIN ----------------
@app.route("/admin")
def admin():
    return render_template("admin_login.html")

@app.route("/admin-login", methods=["POST"])
def admin_login():
    if request.form["username"] == "admin" and request.form["password"] == "1234":
        session["admin"] = True
        return redirect(url_for("admin_dashboard"))
    flash("Wrong credentials")
    return redirect(url_for("admin"))

@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin"))
    return render_template("admin_dashboard.html", submissions=submissions)

# APPROVE
@app.route("/approve/<int:index>")
def approve(index):
    submissions[index]["status"] = "Approved"
    return redirect(url_for("admin_dashboard"))

# REJECT
@app.route("/reject/<int:index>")
def reject(index):
    submissions[index]["status"] = "Rejected"
    return redirect(url_for("admin_dashboard"))

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)