from flask import Flask, render_template, request, redirect, session
import os
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- STORAGE ----------------
students = {}
transactions = {}

TOTAL_FEES = 1000000

# 🔥 PUT YOUR OCR API KEY HERE
API_KEY = "K89924887088957"

# ---------------- OCR VERIFICATION ----------------
def verify_slip(image_path, student):
    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                files={'file': f},
                data={'apikey': API_KEY}
            )

        result = response.json()

        if result.get("IsErroredOnProcessing"):
            return False, None

        text = result['ParsedResults'][0]['ParsedText'].lower()

        name = student['name'].lower()
        reg_no = student['reg_no'].lower()

        has_bank = any(word in text for word in ["bank", "ugx", "payment", "deposit"])
        name_match = name in text
        reg_match = reg_no in text

        # extract receipt
        receipt = "N/A"
        for word in text.split():
            if word.isdigit() and len(word) >= 6:
                receipt = word
                break

        return has_bank and name_match and reg_match, receipt

    except:
        return False, None

# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('login.html')

# ---------------- STUDENT FORM ----------------
@app.route('/student')
def student():
    return render_template('student_form.html')

# ---------------- SUBMIT ----------------
@app.route('/submit', methods=['POST'])
def submit():
    reg_no = request.form['reg_no']

    students[reg_no] = {
        "name": request.form['name'],
        "reg_no": reg_no,
        "program": request.form['program'],
        "school": request.form['school'],
        "year": request.form['year'],
        "semester": request.form['semester'],
        "phone": request.form['phone']
    }

    transactions[reg_no] = []
    session['user'] = reg_no

    return redirect('/dashboard')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    reg_no = session['user']
    student = students[reg_no]
    user_transactions = transactions.get(reg_no, [])

    total_paid = sum(t['amount'] for t in user_transactions)
    balance = TOTAL_FEES - total_paid
    status = "Cleared" if balance <= 0 else "Not Cleared"

    return render_template('dashboard.html',
                           student=student,
                           reg_no=reg_no,
                           total_paid=total_paid,
                           balance=balance,
                           status=status,
                           transactions=user_transactions)

# ---------------- UPLOAD PAGE ----------------
@app.route('/upload')
def upload_page():
    if 'user' not in session:
        return redirect('/')
    return render_template('upload.html')

# ---------------- UPLOAD + OCR ----------------
@app.route('/upload', methods=['POST'])
def upload():
    if 'user' not in session:
        return redirect('/')

    file = request.files['slip']
    reg_no = session['user']
    student = students[reg_no]

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        valid, receipt = verify_slip(filepath, student)

        if valid:
            transactions[reg_no].append({
                "amount": 100000,
                "receipt": receipt,
                "date": datetime.now().strftime("%d %B %Y, %I:%M %p")
            })
            return render_template('upload.html', message="✅ Valid Bank Slip Verified")

        else:
            return render_template('upload.html', message="❌ Invalid Slip (Check Name/Reg No)")

    return render_template('upload.html', message="No file selected")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)