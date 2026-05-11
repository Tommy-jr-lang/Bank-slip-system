from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "BankSlipSecret123")

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# OCR API KEY
API_KEY = "K88887681888957"

# Create uploads folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Temporary memory storage
students = {}
submissions = []

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")


# ---------------- STUDENT PAGE ----------------
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

    my_submissions = [
        x for x in submissions if x["regno"] == regno
    ]

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

    file = request.files.get("slip")

    # -------- FILE CHECK --------
    if not file or file.filename == "":
        flash("❌ No file selected")
        return redirect(url_for("upload"))

    filename = secure_filename(file.filename)

    filepath = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(filepath)

    regno = session["user"]
    student = students.get(regno)

    # -------- DUPLICATE CHECK --------
    for item in submissions:

        if item["filename"] == filename:

            flash("⚠️ This bank slip was already uploaded.")

            return redirect(url_for("dashboard"))

    # -------- OCR PROCESS --------
    extracted_text = ""

    try:

        with open(filepath, "rb") as f:

            response = requests.post(
                "https://api.ocr.space/parse/image",
                files={"file": f},
                data={
                    "apikey": API_KEY,
                    "language": "eng"
                }
            )

        result = response.json()

        print(result)

        if (
            "ParsedResults" in result
            and result["ParsedResults"]
        ):

            extracted_text = result["ParsedResults"][0].get(
                "ParsedText",
                ""
            ).lower()

    except Exception as e:

        print(e)

        flash("❌ Verification service failed")

        return redirect(url_for("dashboard"))

    # -------- VERIFICATION --------
    status = "Pending"

    fullname = student["fullname"].lower()

    # Detect amount-like patterns
    amounts = re.findall(
        r"\d+[.,]\d{2}",
        extracted_text
    )

    # Bank keywords
    bank_keywords = [
        "bank",
        "deposit",
        "receipt",
        "payment",
        "transaction",
        "ugx",
        "invoice",
        "cash",
        "account",
        "withdraw",
        "branch"
    ]

    found_bank_word = any(
        word in extracted_text
        for word in bank_keywords
    )

    # -------- CONDITIONS --------

    # NO TEXT FOUND
    if extracted_text.strip() == "":

        status = "Not Clear"

        flash(
            "❌ No readable text detected. "
            "Please upload a clear bank slip image."
        )

    # RANDOM IMAGE / NOT BANK SLIP
    elif not found_bank_word:

        status = "Invalid"

        flash(
            "⚠️ Uploaded image is not recognized "
            "as a valid bank slip."
        )

    # VERIFIED
    elif (
        fullname in extracted_text
        and regno.lower() in extracted_text
    ):

        status = "Verified"

        if amounts:

            flash(
                f"✅ Bank slip VERIFIED successfully. "
                f"Amount detected: {amounts[0]}"
            )

        else:

            flash(
                "✅ Bank slip VERIFIED successfully."
            )

    # DETAILS MISMATCH
    else:

        status = "Mismatch"

        flash(
            "❌ Slip details do not match "
            "student records."
        )

    # -------- SAVE SUBMISSION --------
    submissions.append({
        "fullname": student["fullname"],
        "regno": regno,
        "filename": filename,
        "date": datetime.now().strftime("%d-%m-%Y"),
        "time": datetime.now().strftime("%H:%M"),
        "status": status,
        "ocr_text": extracted_text[:300]
    })

    return redirect(url_for("dashboard"))


# ---------------- ADMIN PAGE ----------------
@app.route("/admin")
def admin():
    return render_template("admin_login.html")


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin-login", methods=["POST"])
def admin_login():

    username = request.form["username"]
    password = request.form["password"]

    if username == "admin" and password == "1234":

        session["admin"] = True

        return redirect(url_for("admin_dashboard"))

    else:

        flash("❌ Wrong admin credentials")

        return redirect(url_for("admin"))


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("admin"))

    return render_template(
        "admin_dashboard.html",
        submissions=submissions
    )


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# ---------------- RUN APP ----------------
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )