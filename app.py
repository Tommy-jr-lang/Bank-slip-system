from flask import Flask, render_template, request, redirect, url_for
from flask import session, flash, send_from_directory

import os
from datetime import datetime
from werkzeug.utils import secure_filename
import requests
import re

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "BankSlipSecret123"
)

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# OCR API KEY
API_KEY = "K88887681888957"

# CREATE UPLOADS FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# MEMORY STORAGE
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

        x for x in submissions
        if x["regno"] == regno

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


# ---------------- SUBMIT SLIP ----------------
@app.route("/submit-slip", methods=["POST"])
def submit_slip():

    if "user" not in session:

        return redirect(url_for("home"))

    file = request.files.get("slip")

    # -------- CHECK FILE --------
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

            flash(
                "⚠️ This bank slip was already uploaded."
            )

            return redirect(url_for("dashboard"))

    # -------- OCR PROCESS --------
    extracted_text = ""

    try:

        with open(filepath, "rb") as f:

            response = requests.post(

                "https://api.ocr.space/parse/image",

                files={
                    "file": f
                },

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

            extracted_text = result[
                "ParsedResults"
            ][0].get(

                "ParsedText",
                ""

            ).lower()

    except Exception as e:

        print(e)

        flash(
            "❌ OCR verification service failed."
        )

        return redirect(url_for("upload"))

    # -------- DETECT AMOUNT --------
    amounts = re.findall(

        r"\d+[.,]?\d*",
        extracted_text

    )

    detected_amount = "Not Detected"

    if amounts:

        detected_amount = amounts[0]

    # -------- BANK KEYWORDS --------
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

    # -------- VALIDATION --------

    # NO TEXT
    if extracted_text.strip() == "":

        flash(
            "❌ No readable text detected. "
            "Upload a clearer bank slip."
        )

        return redirect(url_for("upload"))

    # INVALID IMAGE
    elif not found_bank_word:

        flash(
            "❌ Uploaded image is NOT recognized "
            "as a bank slip."
        )

        return redirect(url_for("upload"))

    # -------- SAVE SUBMISSION --------
    submissions.append({

        "id": len(submissions),

        "fullname": student["fullname"],

        "regno": regno,

        "filename": filename,

        "date": datetime.now().strftime(
            "%d-%m-%Y"
        ),

        "time": datetime.now().strftime(
            "%H:%M"
        ),

        "status": "Payment Pending",

        "amount": detected_amount,

        "balance": "Pending",

        "ocr_text": extracted_text[:700]

    })

    flash(
        "✅ Bank slip uploaded successfully. "
        "Awaiting admin verification."
    )

    return redirect(url_for("dashboard"))


# ---------------- ADMIN PAGE ----------------
@app.route("/admin")
def admin():

    return render_template(
        "admin_login.html"
    )


# ---------------- ADMIN LOGIN ----------------
@app.route("/admin-login", methods=["POST"])
def admin_login():

    username = request.form["username"]

    password = request.form["password"]

    if (

        username == "admin"
        and password == "1234"

    ):

        session["admin"] = True

        return redirect(
            url_for("admin_dashboard")
        )

    else:

        flash(
            "❌ Wrong admin credentials"
        )

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


# ---------------- CONFIRM PAYMENT ----------------
@app.route(
    "/confirm-payment/<int:submission_id>",
    methods=["POST"]
)
def confirm_payment(submission_id):

    if "admin" not in session:

        return redirect(url_for("admin"))

    balance = request.form.get("balance", "").strip()

    for item in submissions:

        if item["id"] == submission_id:

            item["status"] = "Payment Done"

            if balance == "" or balance == "0":

                item["balance"] = "CLEARED"

            else:

                item["balance"] = balance

            break

    flash(
        "✅ Payment confirmed successfully"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# ---------------- REJECT PAYMENT ----------------
@app.route(
    "/reject-payment/<int:submission_id>",
    methods=["POST"]
)
def reject_payment(submission_id):

    if "admin" not in session:

        return redirect(url_for("admin"))

    for item in submissions:

        if item["id"] == submission_id:

            item["status"] = "Rejected"

            item["balance"] = "NOT CLEARED"

            break

    flash(
        "❌ Payment rejected"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# ---------------- VIEW UPLOADED FILE ----------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(

        app.config["UPLOAD_FOLDER"],
        filename

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