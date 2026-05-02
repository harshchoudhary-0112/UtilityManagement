import uuid
from datetime import datetime, timedelta
import mysql.connector
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from twilio.rest import Client
import re
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


app = Flask(__name__)
app.secret_key = "secret123"

serializer = URLSafeTimedSerializer(app.secret_key)


# ================= EMAIL HELPERS =================
def send_email(to_email, subject, body):
    sender_email = "harshchoudhar6268y@gmail.com"
    sender_password = "zikz hpnq feac menc"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print("❌ Email error:", str(e))
        return False


def send_reset_email(to_email, reset_link):
    subject = "Password Reset Request"
    body = f"""
Hello,

Click the link below to reset your password:

{reset_link}

This link will expire in 15 minutes.

If you did not request this, please ignore this email.
"""
    return send_email(to_email, subject, body)


def send_verification_email(to_email, verify_link, role):
    subject = "Verify Your Email"
    body = f"""
Hello,

Click the link below to verify your {role} account email:

{verify_link}

This link will expire in 60 minutes.

If you did not create this account, please ignore this email.
"""
    return send_email(to_email, subject, body)


def generate_email_token(email, role):
    return serializer.dumps({"email": email, "role": role}, salt="email-verify-salt")


def verify_email_token(token, max_age=3600):
    try:
        data = serializer.loads(token, salt="email-verify-salt", max_age=max_age)
        return data
    except SignatureExpired:
        return None
    except BadSignature:
        return None


# ================= CACHE CONTROL =================
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ================= DATABASE =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Harsh@966933",
        database="utility_portalll"
    )


# ================= TWILIO CONFIGURATION =================
TWILIO_ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "+1234567890"

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def sanitize_phone(n):
    n = str(n).strip()
    if not n.startswith("9"):
        if n.startswith("0"):
            n = n[1:]
    else:
        if len(n) == 10 and n[0] == "9":
            n = "91" + n
    if not n.startswith("+"):
        n = "+" + n
    return n


def notify_users(ward, message):
    if ward == "all":
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT mobile_number FROM users WHERE ward = %s AND mobile_number IS NOT NULL AND mobile_number != ''",
            (ward,)
        )
        numbers = cursor.fetchall()
        for row in numbers:
            number = str(row[0]).strip()
            if not number:
                continue
            try:
                phone = sanitize_phone(number)
                msg = twilio_client.messages.create(
                    body=f"New announcement for your ward: {message}",
                    from_=TWILIO_PHONE_NUMBER,
                    to=phone
                )
                print(f"✅ SMS OK to {phone} | SID: {msg.sid}")
            except Exception as e:
                print(f"❌ Failed to send SMS to {number}: {str(e)}")
    except Exception as e:
        print(f"Database error in notify_users: {str(e)}")
    finally:
        cursor.close()
        conn.close()


def detect_complaint_category(user_message):
    msg = user_message.lower()

    if "water" in msg:
        return "Water Supply", "Water"
    elif "electricity" in msg or "light" in msg or "power" in msg:
        return "Electricity Supply", "Electricity"
    else:
        return "General Complaint", "General"


def extract_mobile_number(user_message):
    match = re.search(r"\b\d{10}\b", user_message)
    return match.group(0) if match else None


# ================= CHAT BOT =================
def chatbot_reply_logic(user_message):
    if not session.get('user_email'):
        return {
            "reply": "Please login first to use the chatbot.",
            "action": "none"
        }

    msg = user_message.strip()
    msg_lower = msg.lower()

    if not msg:
        return {
            "reply": "Please type something. For example: register water complaint, show my complaints, show announcements, update mobile number 9876543210.",
            "action": "none"
        }

    if any(x in msg_lower for x in ["help", "what can you do", "commands", "options"]):
        return {
            "reply": "I can help you with: 1) register complaint, 2) show my complaints, 3) show announcements, 4) update mobile number. Example: 'register water complaint no water in my area' or 'update mobile number 9876543210'.",
            "action": "help"
        }

    if "announcement" in msg_lower or "announcements" in msg_lower or "notice" in msg_lower or "notices" in msg_lower:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message, ward, created_at
            FROM announcements
            WHERE ward = %s OR ward = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, ("all", session.get('user_ward')))
        announcements = cursor.fetchall()

        cursor.close()
        conn.close()

        if not announcements:
            return {
                "reply": "No announcements are available right now.",
                "action": "announcements"
            }

        lines = []
        for a in announcements:
            lines.append(f"Ward {a[1]}: {a[0]}")

        return {
            "reply": "Here are the latest announcements:\n" + "\n".join(lines),
            "action": "announcements"
        }

    if "show my complaints" in msg_lower or "track complaint" in msg_lower or "track complaints" in msg_lower or "my complaints" in msg_lower:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, category, description, status, admin_reply, created_at
            FROM complaintss
            WHERE user_email = %s AND is_deleted = 0
            ORDER BY created_at DESC
            LIMIT 5
        """, (session['user_email'],))
        complaints = cursor.fetchall()
        cursor.close()
        conn.close()

        if not complaints:
            return {
                "reply": "You have not registered any complaints yet.",
                "action": "complaints"
            }

        lines = []
        for c in complaints:
            reply_text = c[4] if c[4] else "No reply yet"
            lines.append(f"#{c[0]} | {c[1]} | {c[3]} | {reply_text}")

        return {
            "reply": "Here are your latest complaints:\n" + "\n".join(lines),
            "action": "complaints"
        }

    if "update mobile" in msg_lower or "change mobile" in msg_lower or "update phone" in msg_lower or "change phone" in msg_lower:
        mobile = extract_mobile_number(msg)

        if not mobile:
            return {
                "reply": "Please send a valid 10-digit mobile number. Example: update mobile number 9876543210",
                "action": "update_mobile"
            }

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET mobile_number = %s WHERE email = %s",
            (mobile, session['user_email'])
        )
        conn.commit()
        cursor.close()
        conn.close()

        session['user_mobile'] = mobile

        return {
            "reply": f"Your mobile number has been updated to {mobile}.",
            "action": "update_mobile"
        }

    if "complaint" in msg_lower or "register complaint" in msg_lower:
        category, department = detect_complaint_category(msg)
        description = msg

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaintss (name, ward, category, description, status, user_email, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session.get('user_name'),
            session.get('user_ward'),
            category,
            description,
            "Pending",
            session.get('user_email'),
            department
        ))
        conn.commit()
        complaint_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return {
            "reply": f"Your complaint has been registered successfully. Complaint ID: {complaint_id}. Category: {category}. Status: Pending.",
            "action": "register_complaint"
        }

    return {
        "reply": "Sorry, I could not understand that clearly. Try: 'show announcements', 'show my complaints', 'update mobile number 9876543210', or 'register water complaint no water since morning'.",
        "action": "unknown"
    }


@app.route('/chatbot', methods=['POST'])
def chatbot():
    if not session.get('user_email'):
        return jsonify({
            "reply": "Please login first to use the chatbot.",
            "action": "none"
        }), 401

    data = request.get_json()
    user_message = data.get('message', '').strip()

    result = chatbot_reply_logic(user_message)
    return jsonify(result)


# ================= HOME =================
@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT message, ward, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, ("all",))
    announcements = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'home.html',
        announcements=announcements,
        user_logged_in=session.get('user_email'),
        admin_logged_in=session.get('admin_email'),
        user_name=session.get('user_name'),
        admin_name=session.get('admin_name'),
        admin_department=session.get('admin_department')
    )


# ================= USER DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if not session.get('user_email'):
        return redirect(url_for('login'))

    user_ward = session.get('user_ward')
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, ward, message, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
    """, ("all",))
    general_announcements = cursor.fetchall()

    cursor.execute("""
        SELECT id, ward, message, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
    """, (user_ward,))
    ward_announcements = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        general_announcements=general_announcements,
        ward_announcements=ward_announcements,
        user_ward=user_ward
    )


# ================= USER AUTH =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_email'):
        return redirect('/dashboard')

    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, ward, password, mobile_number, is_verified
            FROM users
            WHERE email = %s
        """, (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user or not check_password_hash(user[4], password):
            flash("Invalid credentials")
            return redirect(url_for('login'))

        if int(user[6]) != 1:
            flash("Please verify your email before login.")
            return redirect(url_for('login'))

        session['user_id'] = user[0]
        session['user_name'] = user[1]
        session['user_email'] = user[2]
        session['user_ward'] = user[3]
        session['user_mobile'] = user[5]
        flash("Login successful!")
        return redirect('/dashboard')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        ward = request.form['ward'].strip()
        mobile_number = request.form['mobile_number'].strip()
        password = request.form['password']

        if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
            flash("Full name must contain only letters and spaces")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Enter a valid email address")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{1,4}", ward):
            flash("Ward number must contain only 1 to 4 digits")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"\d{10}", mobile_number):
            flash("Mobile number must be exactly 10 digits")
            return redirect(url_for('signup'))

        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", password):
            flash("Password must be 8 to 20 characters and include uppercase, lowercase, number, and special character")
            return redirect(url_for('signup'))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            conn.close()
            flash("Email already registered. Please login.")
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO users (name, email, ward, mobile_number, password, is_verified)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, ward, mobile_number, hashed_password, 0))
        conn.commit()
        cursor.close()
        conn.close()

        token = generate_email_token(email, "user")
        verify_link = url_for('verify_email', token=token, _external=True)
        send_verification_email(email, verify_link, "user")

        flash("Signup successful! Please verify your email, then login.")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/verify-email/<token>')
def verify_email(token):
    data = verify_email_token(token, max_age=3600)

    if not data:
        flash("Verification link is invalid or expired.")
        return redirect(url_for('home'))

    email = data.get("email")
    role = data.get("role")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if role == "user":
            cursor.execute("UPDATE users SET is_verified = 1 WHERE email = %s", (email,))
            conn.commit()
            flash("User email verified successfully! You can now login.")
            return redirect(url_for('login'))

        elif role == "admin":
            cursor.execute("UPDATE admins SET is_verified = 1 WHERE email = %s", (email,))
            conn.commit()
            flash("Admin email verified successfully! You can now login.")
            return redirect(url_for('adminlogin'))

        else:
            flash("Invalid verification request.")
            return redirect(url_for('home'))

    except Exception as e:
        conn.rollback()
        print("Verification error:", str(e))
        flash("Something went wrong during verification.")
        return redirect(url_for('home'))
    finally:
        cursor.close()
        conn.close()


@app.route('/resend-verification', methods=['GET', 'POST'])
def resend_verification():
    if request.method == 'POST':
        email = request.form['email'].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT email, is_verified FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                if int(user[1]) == 1:
                    flash("User email is already verified.")
                    return redirect(url_for('resend_verification'))

                token = generate_email_token(email, "user")
                verify_link = url_for('verify_email', token=token, _external=True)
                send_verification_email(email, verify_link, "user")
                flash("Verification email resent successfully.")
                return redirect(url_for('login'))

            cursor.execute("SELECT email, is_verified FROM admins WHERE email = %s", (email,))
            admin = cursor.fetchone()

            if admin:
                if int(admin[1]) == 1:
                    flash("Admin email is already verified.")
                    return redirect(url_for('resend_verification'))

                token = generate_email_token(email, "admin")
                verify_link = url_for('verify_email', token=token, _external=True)
                send_verification_email(email, verify_link, "admin")
                flash("Verification email resent successfully.")
                return redirect(url_for('adminlogin'))

            flash("Email not found.")
            return redirect(url_for('resend_verification'))

        except Exception as e:
            print("Resend verification error:", str(e))
            flash("Something went wrong. Please try again.")
            return redirect(url_for('resend_verification'))
        finally:
            cursor.close()
            conn.close()

    return render_template('resend_verification.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ================= COMPLAINTS =================
@app.route('/register_complaint', methods=['GET', 'POST'])
def register_complaint():
    if request.method == 'POST':
        name = request.form['name']
        ward = request.form['ward']
        category = request.form['category']
        description = request.form['description']
        user_email = session.get('user_email')

        if category == "Water Supply":
            department = "Water"
        elif category == "Electricity Supply":
            department = "Electricity"
        else:
            department = "General"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaintss (name, ward, category, description, status, user_email, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, ward, category, description, "Pending", user_email, department))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Complaint submitted successfully")
        return redirect('/track_complaints')

    return render_template('register_complaint.html')


@app.route('/track_complaints')
def track_complaints():
    if not session.get('user_email'):
        flash("Please login first")
        return redirect('/login')

    email = session['user_email']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, ward, category, description, status, admin_reply, created_at
        FROM complaintss
        WHERE user_email = %s AND is_deleted = 0
        ORDER BY created_at DESC
    """, (email,))
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('track_complaints.html', complaints=complaints)


@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if not session.get('user_email'):
        flash("Please login first")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE complaintss
        SET is_deleted = 1
        WHERE id = %s AND user_email = %s AND status = 'Resolved'
    """, (id, session['user_email']))
    conn.commit()

    if cursor.rowcount > 0:
        flash("Complaint removed from your track page successfully!")
    else:
        flash("Complaint could not be removed. Only your resolved complaints can be hidden.")

    cursor.close()
    conn.close()
    return redirect(url_for('track_complaints'))


# ================= ADMIN =================
@app.route('/adminpage')
def adminpage():
    if session.get('admin_email'):
        return redirect(url_for('admin'))
    return render_template('admin_login.html')


@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        department = request.form['department'].strip().lower()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, email, department, password, is_verified
            FROM admins
            WHERE email = %s
        """, (email,))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if not admin:
            flash('Admin email not found')
            return redirect(url_for('adminlogin'))

        db_department = admin[2].strip().lower()

        if db_department != department:
            flash('Invalid department selected')
            return redirect(url_for('adminlogin'))

        if not check_password_hash(admin[3], password):
            flash('Invalid password')
            return redirect(url_for('adminlogin'))

        if int(admin[4]) != 1:
            flash("Please verify your admin email before login.")
            return redirect(url_for('adminlogin'))

        session['admin_email'] = admin[1]
        session['admin_name'] = admin[0]
        session['admin_department'] = admin[2]
        flash('Login successful')
        return redirect(url_for('admin'))
        
    return render_template('admin_login.html')

@app.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        department = request.form['department'].strip()
        mobile_number = request.form['mobile_number'].strip()
        password = request.form['password']
        page = request.form['page']

        if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
            flash("Full name must contain only letters and spaces")
            return redirect(url_for(f'admin_signup_{page}'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Enter a valid email address")
            return redirect(url_for(f'admin_signup_{page}'))

        if not re.fullmatch(r"\d{10}", mobile_number):
            flash("Mobile number must be exactly 10 digits")
            return redirect(url_for(f'admin_signup_{page}'))

        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", password):
            flash("Password must be strong")
            return redirect(url_for(f'admin_signup_{page}'))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            cursor.close()
            conn.close()
            flash("Admin email already registered. Please login.")
            return redirect(url_for(f'admin_signup_{page}'))

        hashed_password = generate_password_hash(password)

        cursor.execute("""
            INSERT INTO admins (name, email, department, mobile_number, password, is_verified)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, email, department, mobile_number, hashed_password, 0))
        conn.commit()
        cursor.close()
        conn.close()

        token = generate_email_token(email, "admin")
        verify_link = url_for('verify_email', token=token, _external=True)
        send_verification_email(email, verify_link, "admin")

        flash("Admin signup successful! Please verify your email, then login.")
        return redirect(url_for('adminlogin'))

    return render_template('admin_signup.html')


@app.route('/admin_signup_water')
def admin_signup_water():
    return render_template('admin_signup_water.html')


@app.route('/admin_signup_electricity')
def admin_signup_electricity():
    return render_template('admin_signup_electricity.html')


@app.route('/admin_history')
def admin_history():
    if 'admin_email' not in session:
        return redirect(url_for('adminlogin'))

    department = session.get('admin_department')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM complaintss
        WHERE department = %s AND status = %s
        ORDER BY created_at DESC
    """, (department, 'Resolved'))
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_history.html', complaints=complaints)


@app.route('/admin')
def admin():
    if 'admin_email' not in session:
        return redirect(url_for('adminlogin'))

    department = session.get('admin_department')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM complaintss
        WHERE department = %s AND status != %s
        ORDER BY created_at DESC
    """, (department, 'Resolved'))
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_dash.html', complaints=complaints)


@app.route('/update_complaint/<int:id>', methods=['POST'])
def update_complaint(id):
    if 'admin_email' not in session:
        return redirect(url_for('adminpage'))

    status = request.form['status']
    reply = request.form['admin_reply']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaintss SET status = %s, admin_reply = %s WHERE id = %s",
        (status, reply, id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    flash("Updated successfully")
    return redirect(url_for('admin'))


# ================= ADMIN ANNOUNCEMENTS =================
@app.route('/admin_announcement', methods=['GET', 'POST'])
def admin_announcement():
    if 'admin_email' not in session:
        return redirect(url_for('adminpage'))

    if request.method == 'POST':
        ward = request.form['ward'].strip()
        message = request.form['message'].strip()

        if not ward:
            ward = "all"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO announcements (ward, message, created_at) VALUES (%s, %s, NOW())",
            (ward, message)
        )
        conn.commit()
        cursor.close()
        conn.close()

        if ward != "all":
            notify_users(ward, message)

        flash("Announcement sent successfully!")
        return redirect(url_for('admin_announcement'))

    return render_template('admin_announcement.html')


# ================= EDIT ANNOUNCEMENT =================
@app.route('/edit_announcement', methods=['GET', 'POST'])
def edit_announcement():
    if 'admin_email' not in session:
        return redirect(url_for('adminpage'))

    if request.method == 'POST':
        announcement = request.form['announcement'].strip()
        ward = request.form.get('ward', 'all').strip()

        if ward == "":
            ward = "all"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO announcements (ward, message, created_at) VALUES (%s, %s, NOW())",
            (ward, announcement)
        )
        conn.commit()
        cursor.close()
        conn.close()

        if ward != "all":
            notify_users(ward, announcement)

        flash("Announcement added successfully!")
        return redirect(url_for('edit_announcement'))

    return render_template('edit_announcement.html')


# ================= PASSWORD RESET =================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(minutes=15)

            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                cursor.execute("""
                    UPDATE users
                    SET reset_token = %s, token_expiry = %s
                    WHERE email = %s
                """, (token, expiry, email))
                conn.commit()

                reset_link = url_for('reset_password', token=token, _external=True)
                send_reset_email(email, reset_link)
                flash("Reset link has been sent to your email.")
                return redirect(url_for('forgot_password'))

            cursor.execute("SELECT email FROM admins WHERE email = %s", (email,))
            admin = cursor.fetchone()

            if admin:
                cursor.execute("""
                    UPDATE admins
                    SET reset_token = %s, token_expiry = %s
                    WHERE email = %s
                """, (token, expiry, email))
                conn.commit()

                reset_link = url_for('reset_password', token=token, _external=True)
                send_reset_email(email, reset_link)
                flash("Reset link has been sent to your email.")
                return redirect(url_for('forgot_password'))

            flash("Email not found.")

        except Exception as e:
            conn.rollback()
            print("Forgot password error:", str(e))
            flash("Something went wrong. Please try again.")
        finally:
            cursor.close()
            conn.close()

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT email FROM users
            WHERE reset_token = %s AND token_expiry > NOW()
        """, (token,))
        user = cursor.fetchone()

        account_type = None

        if user:
            account_type = "user"
        else:
            cursor.execute("""
                SELECT email FROM admins
                WHERE reset_token = %s AND token_expiry > NOW()
            """, (token,))
            admin = cursor.fetchone()
            if admin:
                account_type = "admin"

        if not account_type:
            flash("Invalid or expired reset link.")
            return redirect(url_for('forgot_password'))

        if request.method == 'POST':
            new_pass = request.form['password'].strip()

            if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", new_pass):
                flash("Password must be 8-20 characters with uppercase, lowercase, number, and special character")
                return render_template('reset_password.html', token=token)

            hashed_password = generate_password_hash(new_pass)

            if account_type == "user":
                cursor.execute("""
                    UPDATE users
                    SET password = %s, reset_token = NULL, token_expiry = NULL
                    WHERE reset_token = %s
                """, (hashed_password, token))
            else:
                cursor.execute("""
                    UPDATE admins
                    SET password = %s, reset_token = NULL, token_expiry = NULL
                    WHERE reset_token = %s
                """, (hashed_password, token))

            conn.commit()
            flash("Password updated successfully!")

            if account_type == "admin":
                return redirect(url_for('adminlogin'))
            return redirect(url_for('login'))

        return render_template('reset_password.html', token=token)

    except Exception as e:
        conn.rollback()
        print("Reset password error:", str(e))
        flash("Something went wrong. Please try again.")
        return redirect(url_for('forgot_password'))
    finally:
        cursor.close()
        conn.close()


# ================= USER CHANGE PASSWORD =================
@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if not session.get('user_email'):
        flash("Please login first")
        return redirect(url_for('login'))

    if request.method == 'POST':
        current_password = request.form['current_password'].strip()
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        if not current_password or not new_password or not confirm_password:
            flash("All fields are required")
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash("New password and confirm password do not match")
            return redirect(url_for('change_password'))

        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", new_password):
            flash("New password must be 8-20 characters with uppercase, lowercase, number, and special character")
            return redirect(url_for('change_password'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM users WHERE email = %s",
            (session['user_email'],)
        )
        user = cursor.fetchone()

        if not user or not check_password_hash(user[0], current_password):
            cursor.close()
            conn.close()
            flash("Current password is incorrect")
            return redirect(url_for('change_password'))

        cursor.execute(
            "UPDATE users SET password = %s WHERE email = %s",
            (generate_password_hash(new_password), session['user_email'])
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("✅ Password changed successfully!")
        return redirect(url_for('dashboard'))

    return render_template('change_password.html')


# ================= USER CHANGE DETAILS =================
@app.route('/change-details', methods=['GET', 'POST'])
def change_details():
    if not session.get('user_email'):
        flash("Please login first")
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, email, ward, mobile_number FROM users WHERE email = %s",
        (session['user_email'],)
    )
    current_user = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        ward = request.form['ward'].strip()
        mobile_number = request.form['mobile_number'].strip()

        if not name or not email or not ward or not mobile_number:
            flash("All fields are required")
            return redirect(url_for('change_details'))

        if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
            flash("Full name must contain only letters and spaces")
            return redirect(url_for('change_details'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Enter a valid email address")
            return redirect(url_for('change_details'))

        if not re.fullmatch(r"\d{1,4}", ward):
            flash("Ward number must contain only 1 to 4 digits")
            return redirect(url_for('change_details'))

        if not re.fullmatch(r"\d{10}", mobile_number):
            flash("Mobile number must be exactly 10 digits")
            return redirect(url_for('change_details'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE email = %s AND email != %s",
            (email, session['user_email'])
        )
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            conn.close()
            flash("Email already exists with another account")
            return redirect(url_for('change_details'))

        cursor.execute("""
            UPDATE users
            SET name = %s, email = %s, ward = %s, mobile_number = %s
            WHERE email = %s
        """, (name, email, ward, mobile_number, session['user_email']))
        conn.commit()

        session['user_name'] = name
        session['user_email'] = email
        session['user_ward'] = ward
        session['user_mobile'] = mobile_number

        cursor.close()
        conn.close()

        flash("✅ Profile details updated successfully!")
        return redirect(url_for('dashboard'))

    return render_template('changedetails.html', user=current_user)


# ================= ADMIN PASSWORD/DETAILS =================
@app.route('/admin_change_password', methods=['GET', 'POST'])
def admin_change_password():
    if 'admin_email' not in session:
        flash("Please login first")
        return redirect(url_for('adminlogin'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            flash("New password and confirm password do not match")
            return redirect(url_for('admin_change_password'))

        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", new_password):
            flash("New password must be 8-20 characters with uppercase, lowercase, number, and special character")
            return redirect(url_for('admin_change_password'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT password FROM admins WHERE email = %s",
            (session['admin_email'],)
        )
        admin_data = cursor.fetchone()

        if not admin_data:
            cursor.close()
            conn.close()
            flash("Admin not found")
            return redirect(url_for('adminlogin'))

        if not check_password_hash(admin_data[0], current_password):
            cursor.close()
            conn.close()
            flash("Current password is incorrect")
            return redirect(url_for('admin_change_password'))

        cursor.execute(
            "UPDATE admins SET password = %s WHERE email = %s",
            (generate_password_hash(new_password), session['admin_email'])
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Password changed successfully")
        return redirect(url_for('admin'))

    return render_template('admin_change_password.html')


@app.route('/admin_change_details', methods=['GET', 'POST'])
def admin_change_details():
    if 'admin_email' not in session:
        flash("Please login first")
        return redirect(url_for('adminlogin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        new_name = request.form['name']
        new_email = request.form['email']
        new_department = request.form['department']
        new_mobile = request.form['mobile_number']

        if not re.fullmatch(r"\d{10}", new_mobile):
            flash("Mobile number must be exactly 10 digits")
            cursor.close()
            conn.close()
            return redirect(url_for('admin_change_details'))

        cursor.execute(
            "UPDATE admins SET name = %s, email = %s, department = %s, mobile_number = %s WHERE email = %s",
            (new_name, new_email, new_department, new_mobile, session['admin_email'])
        )
        conn.commit()

        session['admin_email'] = new_email
        session['admin_name'] = new_name
        session['admin_department'] = new_department
        session['admin_mobile'] = new_mobile

        cursor.close()
        conn.close()
        flash("Admin details updated successfully")
        return redirect(url_for('admin'))

    cursor.execute(
        "SELECT name, email, department, mobile_number FROM admins WHERE email = %s",
        (session['admin_email'],)
    )
    admin_data = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('admin_change_details.html', admin=admin_data)


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)