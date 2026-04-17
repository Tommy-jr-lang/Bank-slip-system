from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "BankSlipSecret123")

# Upload folder
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder if missing
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Temporary memory storage
students = {}
submissions = []

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")


# ---------------- STUDENT CHOICE ----------------
@app.route("/student")
def student():
    return render_template("student_form.html")


# ---------------- REGISTER STUDENT ----------------
@app.route("/register", methods=["POST"])
def register():
    fullname = request.form["fullname"]
    regno = request.form["regno"]
    program = request.form["program"]
    school = request.form["school"]
    year = request.form["year"]
    semester = request.form["semester"]
    phone = request.form["phone"]

    students[regno] = {
        "fullname": fullname,
        "program": program,
        "school": school,
        "year": year,
        "semester": semester,
        "phone": phone
    }

    session["user"] = regno
    return redirect(url_for("dashboard"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("home"))

    regno = session["user"]
    student = students.get(regno)

    my_submissions = [x for x in submissions if x["regno"] == regno]

    return render_template(
        "dashboard.html",
        student=student,
        regno=regno,
        submissions=my_submissions
    )


# ---------------- UPLOAD PAGE ----------------
@app.route("/upload")
def upload():
    if "user" not in session:
        return redirect(url_for("home"))
    return render_template("upload.html")


# ---------------- SAVE UPLOAD ----------------
@app.route("/submit-slip", methods=["POST"])
def submit_slip():
    if "user" not in session:
        return redirect(url_for("home"))

    if "slip" not in request.files:
        flash("No file selected")
        return redirect(url_for("upload"))

    file = request.files["slip"]

    if file.filename == "":
        flash("No selected file")
        return redirect(url_for("upload"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    regno = session["user"]
    student = students.get(regno)

    submissions.append({
        "fullname": student["fullname"],
        "regno": regno,
        "filename": filename,
        "date": datetime.now().strftime("%d-%m-%Y"),
        "time": datetime.now().strftime("%I:%M %p"),
        "status": "Pending"
    })

    flash("Slip uploaded successfully")
    return redirect(url_for("dashboard"))


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin")
def admin():
    return render_template("admin_login.html")


@app.route("/admin-login", methods=["POST"])
def admin_login():
    username = request.form["username"]
    password = request.form["password"]

    if username == "admin" and password == "1234":
        session["admin"] = True
        return redirect(url_for("admin_dashboard"))
    else:
        flash("Wrong admin credentials")
        return redirect(url_for("admin"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin"))

    return render_template("admin_dashboard.html", submissions=submissions)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)