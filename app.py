import uuid
import os
from datetime import datetime, timedelta
import mysql.connector
from flask import Flask, render_template, request, redirect, flash, url_for, session, jsonify
from twilio.rest import Client
import re
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature


app = Flask(__name__)
app.secret_key = "secret123"

serializer = URLSafeTimedSerializer(app.secret_key)


# ================= EMAIL HELPERS =================
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


PORTAL_NAME = "Real Time Urban Utility Management & Communication Portal"
PORTAL_SHORT = "RTUUMC Portal"


def send_email(to_email, subject, body, is_html=False):
    sender_email = "harshchoudhar6268y@gmail.com"
    sender_password = "zikz hpnq feac menc"
    display_name = PORTAL_NAME

    if is_html:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{display_name} <{sender_email}>"
        msg['To'] = to_email
        msg.attach(MIMEText(body, 'html'))
    else:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = f"{display_name} <{sender_email}>"
        msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Email error:", str(e))
        return False


def email_template(title, greeting, content_html, button_text=None, button_url=None, footer_note=None):
    button_block = ""
    if button_text and button_url:
        button_block = f'''
        <tr><td style="padding:28px 36px 0;text-align:center">
          <a href="{button_url}" style="display:inline-block;padding:16px 44px;background:linear-gradient(135deg,#0077b6,#00c853);color:#ffffff;text-decoration:none;border-radius:14px;font-weight:700;font-size:15px;letter-spacing:0.3px;box-shadow:0 10px 28px rgba(0,119,182,0.35);transition:all 0.3s ease">{button_text}</a>
        </td></tr>'''
    footer = footer_note or f"You are receiving this email because you are registered on {PORTAL_NAME}."
    year = datetime.now().year
    return f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:linear-gradient(135deg,#eef2f7,#dbeafe);font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#eef2f7,#dbeafe);padding:40px 16px">
<tr><td align="center">

  <!-- Main Card -->
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:24px;overflow:hidden;box-shadow:0 25px 60px rgba(15,23,42,0.12)">

    <!-- Header Banner -->
    <tr><td style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#0077b6 100%);padding:36px 36px 32px;text-align:center">
      <div style="display:inline-block;width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#0077b6,#00c853);text-align:center;line-height:56px;font-size:26px;box-shadow:0 10px 24px rgba(0,200,83,0.3);margin-bottom:16px">🏛️</div>
      <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:0.4px;line-height:1.4">{PORTAL_NAME}</h1>
      <div style="margin:12px auto 0;display:inline-block;padding:6px 18px;border-radius:999px;background:rgba(255,255,255,0.15);backdrop-filter:blur(8px)">
        <span style="font-size:12px;color:rgba(255,255,255,0.9);font-weight:600;letter-spacing:0.5px">{title}</span>
      </div>
    </td></tr>

    <!-- Body Content -->
    <tr><td style="padding:36px 36px 16px">
      <p style="margin:0 0 20px;font-size:17px;color:#111827;font-weight:700">{greeting}</p>
      {content_html}
    </td></tr>

    <!-- Button -->
    {button_block}

    <!-- Footer -->
    <tr><td style="padding:32px 36px 28px">
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 20px">
      <p style="margin:0 0 4px;font-size:11px;color:#9ca3af;text-align:center;line-height:1.6">{footer}</p>
      <p style="margin:0;font-size:11px;color:#b0b8c4;text-align:center">© {year} CDGI | {PORTAL_NAME}</p>
    </td></tr>

  </table>

</td></tr>
</table>
</body></html>'''


# ================= TWILIO CONFIGURATION =================


twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def sanitize_phone(n):
    n = str(n).strip()

    if n.startswith("+"):
        return n

    if n.startswith("0"):
        n = n[1:]

    if len(n) == 10:
        n = "91" + n

    if not n.startswith("+"):
        n = "+" + n

    return n


def send_sms(to_number, message):
    try:
        if not to_number:
            return False

        phone = sanitize_phone(to_number)
        msg = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        print(f"✅ SMS sent successfully to {phone} | SID: {msg.sid}")
        return True
    except Exception as e:
        print("❌ SMS error:", str(e))
        return False


# ================= DATABASE =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Harsh@966933",
        database="utility_portalll"
    )


def get_contact_details_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT name, email, mobile_number
            FROM users
            WHERE email = %s
        """, (email,))
        user = cursor.fetchone()

        if user:
            return {
                "name": user[0],
                "email": user[1],
                "mobile_number": user[2],
                "role": "user"
            }

        cursor.execute("""
            SELECT name, email, mobile_number
            FROM admins
            WHERE email = %s
        """, (email,))
        admin = cursor.fetchone()

        if admin:
            return {
                "name": admin[0],
                "email": admin[1],
                "mobile_number": admin[2],
                "role": "admin"
            }

        return None

    except Exception as e:
        print("Contact fetch error:", str(e))
        return None

    finally:
        cursor.close()
        conn.close()


def send_notification(to_email, subject, email_body, sms_body=None, is_html=False):
    email_sent = send_email(to_email, subject, email_body, is_html=is_html)

    contact = get_contact_details_by_email(to_email)
    sms_sent = False

    if contact and contact.get("mobile_number"):
        sms_text = sms_body if sms_body else subject
        sms_sent = send_sms(contact.get("mobile_number"), sms_text)

    return email_sent, sms_sent


def send_reset_email(to_email, reset_link):
    subject = "Password Reset Request"
    content = '''
      <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.7">We received a request to reset your password. Click the button below to choose a new password.</p>
      <div style="background:#fef3c7;border:1px solid #fbbf24;border-radius:12px;padding:14px 16px;margin:0 0 6px">
        <p style="margin:0;font-size:13px;color:#92400e">⏱️ This link will expire in <strong>15 minutes</strong>.</p>
      </div>
      <p style="margin:14px 0 0;font-size:13px;color:#6b7280">If you did not request this, please ignore this email.</p>
    '''
    body = email_template(
        title="Password Reset",
        greeting="Hello,",
        content_html=content,
        button_text="🔐 Reset Password",
        button_url=reset_link
    )
    sms_body = f"{PORTAL_NAME}: Password reset requested. Check your email for the reset link. Valid for 15 minutes."
    return send_notification(to_email, subject, body, sms_body, is_html=True)


def send_verification_email(to_email, verify_link, role):
    subject = "Verify Your Email"
    content = f'''
      <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.7">Thank you for signing up! Please verify your <strong>{role}</strong> account email to get started.</p>
      <div style="background:#ecfdf5;border:1px solid #34d399;border-radius:12px;padding:14px 16px;margin:0 0 6px">
        <p style="margin:0;font-size:13px;color:#065f46">⏱️ This verification link will expire in <strong>60 minutes</strong>.</p>
      </div>
      <p style="margin:14px 0 0;font-size:13px;color:#6b7280">If you did not create this account, please ignore this email.</p>
    '''
    body = email_template(
        title="Email Verification",
        greeting="Hello,",
        content_html=content,
        button_text="✅ Verify Email",
        button_url=verify_link
    )
    sms_body = f"{PORTAL_NAME}: Your {role} account verification link has been sent to your email. Please verify within 60 minutes."
    return send_notification(to_email, subject, body, sms_body, is_html=True)


def send_complaint_registered_email(to_email, user_name, complaint_id, category, description, status):
    subject = f"Complaint Registered Successfully - {complaint_id}"
    content = f'''
      <p style="margin:0 0 18px;font-size:14px;color:#374151;line-height:1.7">Your complaint has been registered successfully. Here are the details:</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden">
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Complaint ID</span><br><strong style="font-size:15px;color:#0077b6">{complaint_id}</strong></td></tr>
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Category</span><br><strong style="font-size:14px;color:#111827">{category}</strong></td></tr>
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Description</span><br><span style="font-size:14px;color:#374151">{description}</span></td></tr>
        <tr><td style="padding:14px 18px"><span style="font-size:12px;color:#6b7280">Status</span><br><span style="display:inline-block;padding:5px 14px;border-radius:999px;background:linear-gradient(135deg,#f97316,#fb923c);color:#fff;font-size:12px;font-weight:700">{status}</span></td></tr>
      </table>
    '''
    body = email_template(
        title="Complaint Registered",
        greeting=f"Hello {user_name},",
        content_html=content
    )
    sms_body = f"{PORTAL_SHORT}: Complaint {complaint_id} registered. Category: {category}. Status: {status}."
    return send_notification(to_email, subject, body, sms_body, is_html=True)


def send_complaint_update_email(to_email, user_name, complaint_id, category, description, status, admin_reply):
    subject = f"Complaint Updated - {complaint_id}"
    status_colors = {'Pending': '#f97316', 'In Progress': '#3b82f6', 'Resolved': '#00a86b', 'Rejected': '#ef4444'}
    s_color = status_colors.get(status, '#6b7280')
    reply_html = f'<span style="font-size:14px;color:#374151">{admin_reply}</span>' if admin_reply else '<span style="font-size:13px;color:#9ca3af;font-style:italic">No reply provided</span>'
    content = f'''
      <p style="margin:0 0 18px;font-size:14px;color:#374151;line-height:1.7">Your complaint has been updated by the admin. See the latest details below:</p>
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden">
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Complaint ID</span><br><strong style="font-size:15px;color:#0077b6">{complaint_id}</strong></td></tr>
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Category</span><br><strong style="font-size:14px;color:#111827">{category}</strong></td></tr>
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Description</span><br><span style="font-size:14px;color:#374151">{description}</span></td></tr>
        <tr><td style="padding:14px 18px;border-bottom:1px solid #e2e8f0"><span style="font-size:12px;color:#6b7280">Updated Status</span><br><span style="display:inline-block;padding:5px 14px;border-radius:999px;background:{s_color};color:#fff;font-size:12px;font-weight:700">{status}</span></td></tr>
        <tr><td style="padding:14px 18px"><span style="font-size:12px;color:#6b7280">Admin Reply</span><br>{reply_html}</td></tr>
      </table>
    '''
    body = email_template(
        title="Complaint Status Update",
        greeting=f"Hello {user_name},",
        content_html=content
    )
    sms_body = f"{PORTAL_SHORT}: Complaint {complaint_id} updated. Status: {status}. Reply: {admin_reply if admin_reply else 'No reply'}"
    return send_notification(to_email, subject, body, sms_body, is_html=True)


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


def notify_users_email(ward, message):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if ward == "all":
            cursor.execute("""
                SELECT email, name, ward, mobile_number
                FROM users
                WHERE email IS NOT NULL AND email != ''
            """)
        else:
            cursor.execute("""
                SELECT email, name, ward, mobile_number
                FROM users
                WHERE ward = %s AND email IS NOT NULL AND email != ''
            """, (ward,))

        users = cursor.fetchall()

        for user in users:
            to_email = user[0]
            name = user[1] if user[1] else "User"
            user_ward = user[2]
            mobile_number = user[3]

            if ward == "all":
                subject = "New General Announcement"
                content = f'''
                  <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.7">A new general announcement has been posted for all users:</p>
                  <div style="background:linear-gradient(135deg,#eef7ff,#f9fcff);border:1px solid #bfdbfe;border-radius:14px;padding:18px 20px;border-left:5px solid #0077b6">
                    <p style="margin:0;font-size:14px;color:#1f2937;line-height:1.7">{message}</p>
                  </div>
                '''
                body = email_template(
                    title="General Announcement",
                    greeting=f"Hello {name},",
                    content_html=content
                )
                sms_body = f"{PORTAL_SHORT}: New general announcement: {message}"
            else:
                subject = f"New Announcement for Ward {ward}"
                content = f'''
                  <p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.7">A new announcement has been posted for <strong>Ward {ward}</strong>:</p>
                  <div style="background:linear-gradient(135deg,#effff4,#fbfffd);border:1px solid #86efac;border-radius:14px;padding:18px 20px;border-left:5px solid #00a86b">
                    <p style="margin:0;font-size:14px;color:#1f2937;line-height:1.7">{message}</p>
                  </div>
                '''
                body = email_template(
                    title=f"Ward {ward} Announcement",
                    greeting=f"Hello {name},",
                    content_html=content
                )
                sms_body = f"{PORTAL_SHORT}: New announcement for Ward {ward}: {message}"

            send_email(to_email, subject, body, is_html=True)

            if mobile_number:
                send_sms(mobile_number, sms_body)

    except Exception as e:
        print("Announcement email/SMS error:", str(e))
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


def generate_complaint_id():
    prefix = "CMP"
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{date_part}-{random_part}"


def generate_sms_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_sms(mobile_number, otp_code):
    message = f"{PORTAL_NAME}: Your verification code is {otp_code}. Valid for 10 minutes. Do not share this code."
    sms_sent = send_sms(mobile_number, message)
    return sms_sent


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
            SELECT complaint_id, id, category, description, status, admin_reply, created_at
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
            reply_text = c[5] if c[5] else "No reply yet"
            lines.append(f"{c[0]} | {c[2]} | {c[4]} | {reply_text}")

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
        complaint_id = generate_complaint_id()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaintss
            (complaint_id, name, ward, category, description, status, user_email, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            complaint_id,
            session.get('user_name'),
            session.get('user_ward'),
            category,
            description,
            "Pending",
            session.get('user_email'),
            department
        ))
        conn.commit()
        cursor.close()
        conn.close()

        if session.get('user_email'):
            send_complaint_registered_email(
                to_email=session.get('user_email'),
                user_name=session.get('user_name') or "User",
                complaint_id=complaint_id,
                category=category,
                description=description,
                status="Pending"
            )

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
            SELECT id, name, email, ward, password, mobile_number, is_verified, profile_photo
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
        session['user_photo'] = user[7] if user[7] else None
        flash("Login successful!")
        return redirect('/dashboard')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        form_type = request.form.get('form_type', 'signup')

        # ── Step 1: Initial signup form ──
        if form_type == 'signup':
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

            cursor.close()
            conn.close()

            otp = generate_sms_otp()
            session['pending_user_signup'] = {
                'name': name,
                'email': email,
                'ward': ward,
                'mobile_number': mobile_number,
                'password': password,
                'otp': otp,
                'otp_time': datetime.now().isoformat()
            }

            send_otp_sms(mobile_number, otp)
            flash("A 6-digit verification code has been sent to your mobile number.")
            return redirect(url_for('signup'))

        # ── Step 2: Verify OTP ──
        elif form_type == 'verify_otp':
            pending = session.get('pending_user_signup')
            if not pending:
                flash("No pending signup found. Please start again.")
                return redirect(url_for('signup'))

            otp_input = request.form['otp'].strip()
            otp_time = datetime.fromisoformat(pending['otp_time'])

            if datetime.now() - otp_time > timedelta(minutes=10):
                flash("Verification code has expired. Please resend.")
                return redirect(url_for('signup'))

            if otp_input != pending['otp']:
                flash("Invalid verification code. Please try again.")
                return redirect(url_for('signup'))

            hashed_password = generate_password_hash(pending['password'])

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE email = %s", (pending['email'],))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                session.pop('pending_user_signup', None)
                flash("Email already registered. Please login.")
                return redirect(url_for('signup'))

            cursor.execute("""
                INSERT INTO users (name, email, ward, mobile_number, password, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pending['name'], pending['email'], pending['ward'],
                  pending['mobile_number'], hashed_password, 0))
            conn.commit()
            cursor.close()
            conn.close()

            token = generate_email_token(pending['email'], "user")
            verify_link = url_for('verify_email', token=token, _external=True)
            send_verification_email(pending['email'], verify_link, "user")

            session.pop('pending_user_signup', None)
            flash("Mobile verified! Please check your email to verify your email address, then login.")
            return redirect(url_for('login'))

        # ── Step 3: Resend OTP ──
        elif form_type == 'resend_otp':
            pending = session.get('pending_user_signup')
            if not pending:
                flash("No pending signup found. Please start again.")
                return redirect(url_for('signup'))

            otp = generate_sms_otp()
            pending['otp'] = otp
            pending['otp_time'] = datetime.now().isoformat()
            session['pending_user_signup'] = pending

            send_otp_sms(pending['mobile_number'], otp)
            flash("A new verification code has been sent to your mobile number.")
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/signup_cancel')
def signup_cancel():
    session.pop('pending_user_signup', None)
    return redirect(url_for('signup'))

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

    return render_template('resendverification.html')


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

        complaint_id = generate_complaint_id()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO complaintss
            (complaint_id, name, ward, category, description, status, user_email, department)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (complaint_id, name, ward, category, description, "Pending", user_email, department))
        conn.commit()
        cursor.close()
        conn.close()

        if user_email:
            send_complaint_registered_email(
                to_email=user_email,
                user_name=name,
                complaint_id=complaint_id,
                category=category,
                description=description,
                status="Pending"
            )

        flash(f"Complaint submitted successfully! Your Complaint ID is {complaint_id}")
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
        SELECT complaint_id, id, name, ward, category, description, status, admin_reply, created_at
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

        conn2 = get_db_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("SELECT profile_photo FROM admins WHERE email = %s", (admin[1],))
        photo_row = cursor2.fetchone()
        session['admin_photo'] = photo_row[0] if photo_row and photo_row[0] else None
        cursor2.close()
        conn2.close()

        flash('Login successful')
        return redirect(url_for('admin'))

    return render_template('admin_login.html')


@app.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        form_type = request.form.get('form_type', 'signup')
        page = request.form.get('page', 'admin_signup')

        # Build redirect target from page
        def get_redirect_page():
            if page in ('water', 'electricity'):
                return url_for(f'admin_signup_{page}')
            return url_for('admin_signup')

        # ── Step 1: Initial signup form ──
        if form_type == 'signup':
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            department = request.form['department'].strip()
            mobile_number = request.form['mobile_number'].strip()
            password = request.form['password']

            if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
                flash("Full name must contain only letters and spaces")
                return redirect(get_redirect_page())

            if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Enter a valid email address")
                return redirect(get_redirect_page())

            if not re.fullmatch(r"\d{10}", mobile_number):
                flash("Mobile number must be exactly 10 digits")
                return redirect(get_redirect_page())

            if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", password):
                flash("Password must be strong")
                return redirect(get_redirect_page())

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
            existing_admin = cursor.fetchone()

            if existing_admin:
                cursor.close()
                conn.close()
                flash("Admin email already registered. Please login.")
                return redirect(get_redirect_page())

            cursor.close()
            conn.close()

            otp = generate_sms_otp()
            session['pending_admin_signup'] = {
                'name': name,
                'email': email,
                'department': department,
                'mobile_number': mobile_number,
                'password': password,
                'page': page,
                'otp': otp,
                'otp_time': datetime.now().isoformat()
            }

            send_otp_sms(mobile_number, otp)
            flash("A 6-digit verification code has been sent to your mobile number.")
            return redirect(get_redirect_page())

        # ── Step 2: Verify OTP ──
        elif form_type == 'verify_otp':
            pending = session.get('pending_admin_signup')
            if not pending:
                flash("No pending signup found. Please start again.")
                return redirect(get_redirect_page())

            otp_input = request.form['otp'].strip()
            otp_time = datetime.fromisoformat(pending['otp_time'])

            if datetime.now() - otp_time > timedelta(minutes=10):
                flash("Verification code has expired. Please resend.")
                return redirect(get_redirect_page())

            if otp_input != pending['otp']:
                flash("Invalid verification code. Please try again.")
                return redirect(get_redirect_page())

            hashed_password = generate_password_hash(pending['password'])

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM admins WHERE email = %s", (pending['email'],))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                session.pop('pending_admin_signup', None)
                flash("Admin email already registered. Please login.")
                return redirect(get_redirect_page())

            cursor.execute("""
                INSERT INTO admins (name, email, department, mobile_number, password, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (pending['name'], pending['email'], pending['department'],
                  pending['mobile_number'], hashed_password, 0))
            conn.commit()
            cursor.close()
            conn.close()

            token = generate_email_token(pending['email'], "admin")
            verify_link = url_for('verify_email', token=token, _external=True)
            send_verification_email(pending['email'], verify_link, "admin")

            session.pop('pending_admin_signup', None)
            flash("Mobile verified! Please check your email to verify your email address, then login.")
            return redirect(url_for('adminlogin'))

        # ── Step 3: Resend OTP ──
        elif form_type == 'resend_otp':
            pending = session.get('pending_admin_signup')
            if not pending:
                flash("No pending signup found. Please start again.")
                return redirect(get_redirect_page())

            otp = generate_sms_otp()
            pending['otp'] = otp
            pending['otp_time'] = datetime.now().isoformat()
            session['pending_admin_signup'] = pending

            send_otp_sms(pending['mobile_number'], otp)
            flash("A new verification code has been sent to your mobile number.")
            return redirect(get_redirect_page())

    return render_template('admin_signup.html')


@app.route('/admin_signup_cancel')
def admin_signup_cancel():
    page = None
    pending = session.get('pending_admin_signup')
    if pending:
        page = pending.get('page')
    session.pop('pending_admin_signup', None)
    if page in ('water', 'electricity'):
        return redirect(url_for(f'admin_signup_{page}'))
    return redirect(url_for('admin_signup'))


@app.route('/admin_signup_water')
def admin_signup_water():
    return render_template('admin_signup_water.html')


@app.route('/admin_signup_electricity')
def admin_signup_electricity():
    return render_template('admin_signup_electricity.html')


@app.route('/adminhistory')
def adminhistory():
    if 'admin_email' not in session:
        return redirect(url_for('adminlogin'))

    department = session.get('admin_department')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, complaint_id, name, ward, category, description, status, admin_reply, created_at
        FROM complaintss
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
        SELECT id, complaint_id, name, ward, category, description, status, admin_reply, created_at
        FROM complaintss
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

    cursor.execute("""
        SELECT complaint_id, name, user_email, category, description
        FROM complaintss
        WHERE id = %s
    """, (id,))
    complaint = cursor.fetchone()

    if not complaint:
        cursor.close()
        conn.close()
        flash("Complaint not found")
        return redirect(url_for('admin'))

    complaint_id = complaint[0]
    user_name = complaint[1]
    user_email = complaint[2]
    category = complaint[3]
    description = complaint[4]

    cursor.execute(
        "UPDATE complaintss SET status = %s, admin_reply = %s WHERE id = %s",
        (status, reply, id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    if user_email:
        send_complaint_update_email(
            to_email=user_email,
            user_name=user_name,
            complaint_id=complaint_id,
            category=category,
            description=description,
            status=status,
            admin_reply=reply
        )

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

        notify_users_email(ward, message)

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

        notify_users_email(ward, announcement)

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
@app.route("/change-details", methods=["GET", "POST"])
def change_details():
    if not session.get("user_email"):
        flash("Please login first")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, email, ward, mobile_number FROM users WHERE email = %s",
        (session["user_email"],)
    )
    current_user = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == "POST":
        form_type = request.form.get("form_type", "update")

        # ── Step 1: Submit details form ──
        if form_type == "update":
            name = request.form["name"].strip()
            email = request.form["email"].strip()
            ward = request.form["ward"].strip()
            mobilenumber = request.form["mobile_number"].strip()

            if not name or not email or not ward or not mobilenumber:
                flash("All fields are required")
                return redirect(url_for("change_details"))

            if not re.fullmatch(r"[A-Za-z ]{2,50}", name):
                flash("Full name must contain only letters and spaces")
                return redirect(url_for("change_details"))

            if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Enter a valid email address")
                return redirect(url_for("change_details"))

            if not re.fullmatch(r"\d{1,4}", ward):
                flash("Ward number must contain only 1 to 4 digits")
                return redirect(url_for("change_details"))

            if not re.fullmatch(r"\d{10}", mobilenumber):
                flash("Mobile number must be exactly 10 digits")
                return redirect(url_for("change_details"))

            old_mobile = session.get("user_mobile", "")
            mobile_changed = (mobilenumber != old_mobile)

            # If mobile number changed, require OTP verification
            if mobile_changed:
                otp = generate_sms_otp()
                session['pending_user_mobile_otp'] = {
                    'name': name,
                    'email': email,
                    'ward': ward,
                    'mobile_number': mobilenumber,
                    'otp': otp,
                    'otp_time': datetime.now().isoformat()
                }
                send_otp_sms(mobilenumber, otp)
                flash("A verification code has been sent to your new mobile number.")
                return redirect(url_for("change_details"))

            # No mobile change — update directly
            old_email = session["user_email"]
            email_changed = (email.lower() != old_email.lower())

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND email != %s",
                    (email, old_email)
                )
                existing_user = cursor.fetchone()

                if existing_user:
                    flash("Email already exists with another account")
                    return redirect(url_for("change_details"))

                if email_changed:
                    cursor.execute(
                        """
                        UPDATE users
                        SET name = %s, email = %s, ward = %s, mobile_number = %s, is_verified = 0
                        WHERE email = %s
                        """,
                        (name, email, ward, mobilenumber, old_email)
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE users
                        SET name = %s, ward = %s, mobile_number = %s
                        WHERE email = %s
                        """,
                        (name, ward, mobilenumber, old_email)
                    )

                conn.commit()

                session["user_name"] = name
                session["user_email"] = email
                session["user_ward"] = ward
                session["user_mobile"] = mobilenumber

                if email_changed:
                    token = generate_email_token(email, "user")
                    verify_link = url_for("verify_email", token=token, _external=True)
                    send_verification_email(email, verify_link, "user")
                    flash("Profile updated. A verification link has been sent to your new email.")
                else:
                    flash("Profile details updated successfully!")

                return redirect(url_for("dashboard"))

            except Exception as e:
                conn.rollback()
                print("Change details error:", str(e))
                flash("Something went wrong while updating profile.")
                return redirect(url_for("change_details"))

            finally:
                cursor.close()
                conn.close()

        # ── Step 2: Verify mobile OTP ──
        elif form_type == "verify_mobile_otp":
            pending = session.get('pending_user_mobile_otp')
            if not pending:
                flash("No pending verification found. Please try again.")
                return redirect(url_for("change_details"))

            otp_input = request.form['otp'].strip()
            otp_time = datetime.fromisoformat(pending['otp_time'])

            if datetime.now() - otp_time > timedelta(minutes=10):
                flash("Verification code has expired. Please resend.")
                return redirect(url_for("change_details"))

            if otp_input != pending['otp']:
                flash("Invalid verification code. Please try again.")
                return redirect(url_for("change_details"))

            # OTP verified — now update the profile
            name = pending['name']
            email = pending['email']
            ward = pending['ward']
            mobilenumber = pending['mobile_number']
            old_email = session["user_email"]
            email_changed = (email.lower() != old_email.lower())

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND email != %s",
                    (email, old_email)
                )
                existing_user = cursor.fetchone()

                if existing_user:
                    flash("Email already exists with another account")
                    session.pop('pending_user_mobile_otp', None)
                    return redirect(url_for("change_details"))

                if email_changed:
                    cursor.execute(
                        """
                        UPDATE users
                        SET name = %s, email = %s, ward = %s, mobile_number = %s, is_verified = 0
                        WHERE email = %s
                        """,
                        (name, email, ward, mobilenumber, old_email)
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE users
                        SET name = %s, ward = %s, mobile_number = %s
                        WHERE email = %s
                        """,
                        (name, ward, mobilenumber, old_email)
                    )

                conn.commit()

                session["user_name"] = name
                session["user_email"] = email
                session["user_ward"] = ward
                session["user_mobile"] = mobilenumber
                session.pop('pending_user_mobile_otp', None)

                if email_changed:
                    token = generate_email_token(email, "user")
                    verify_link = url_for("verify_email", token=token, _external=True)
                    send_verification_email(email, verify_link, "user")
                    flash("Mobile verified & profile updated! A verification link has been sent to your new email.")
                else:
                    flash("Mobile number verified & profile updated successfully!")

                return redirect(url_for("dashboard"))

            except Exception as e:
                conn.rollback()
                print("Change details error:", str(e))
                flash("Something went wrong while updating profile.")
                return redirect(url_for("change_details"))

            finally:
                cursor.close()
                conn.close()

        # ── Step 3: Resend mobile OTP ──
        elif form_type == "resend_mobile_otp":
            pending = session.get('pending_user_mobile_otp')
            if not pending:
                flash("No pending verification found. Please try again.")
                return redirect(url_for("change_details"))

            otp = generate_sms_otp()
            pending['otp'] = otp
            pending['otp_time'] = datetime.now().isoformat()
            session['pending_user_mobile_otp'] = pending

            send_otp_sms(pending['mobile_number'], otp)
            flash("A new verification code has been sent to your mobile number.")
            return redirect(url_for("change_details"))

    return render_template("changedetails.html", user=current_user)


@app.route('/change_details_cancel_otp')
def change_details_cancel_otp():
    session.pop('pending_user_mobile_otp', None)
    return redirect(url_for('change_details'))



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

        flash("✅ Admin password changed successfully!")
        return redirect(url_for('admin'))

    return render_template('admin_change_password.html')


@app.route('/admin_change_details', methods=['GET', 'POST'])
def admin_change_details():
    if 'admin_email' not in session:
        flash("Please login first")
        return redirect(url_for('adminlogin'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, email, department, mobile_number, is_verified FROM admins WHERE email = %s",
        (session['admin_email'],)
    )
    current_admin = cursor.fetchone()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        form_type = request.form.get('form_type', 'update')

        # ── Step 1: Submit details form ──
        if form_type == 'update':
            name = request.form['name'].strip()
            email = request.form['email'].strip()
            department = request.form['department'].strip()
            mobile_number = request.form['mobile_number'].strip()

            if not name or not email or not department or not mobile_number:
                flash("All fields are required")
                return redirect(url_for('admin_change_details'))

            if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
                flash("Full name must contain only letters and spaces")
                return redirect(url_for('admin_change_details'))

            if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
                flash("Enter a valid email address")
                return redirect(url_for('admin_change_details'))

            if not re.fullmatch(r"\d{10}", mobile_number):
                flash("Mobile number must be exactly 10 digits")
                return redirect(url_for('admin_change_details'))

            old_mobile = session.get('admin_mobile', '')
            mobile_changed = (mobile_number != old_mobile)

            # If mobile number changed, require OTP verification
            if mobile_changed:
                otp = generate_sms_otp()
                session['pending_admin_mobile_otp'] = {
                    'name': name,
                    'email': email,
                    'department': department,
                    'mobile_number': mobile_number,
                    'otp': otp,
                    'otp_time': datetime.now().isoformat()
                }
                send_otp_sms(mobile_number, otp)
                flash("A verification code has been sent to your new mobile number.")
                return redirect(url_for('admin_change_details'))

            # No mobile change — update directly
            old_email = session['admin_email']
            email_changed = (email.lower() != old_email.lower())

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email FROM admins WHERE email = %s AND email != %s",
                (email, old_email)
            )
            existing_admin = cursor.fetchone()

            if existing_admin:
                cursor.close()
                conn.close()
                flash("Email already exists with another admin account")
                return redirect(url_for('admin_change_details'))

            try:
                if email_changed:
                    cursor.execute("""
                        UPDATE admins
                        SET name = %s, email = %s, department = %s, mobile_number = %s, is_verified = 0
                        WHERE email = %s
                    """, (name, email, department, mobile_number, old_email))
                else:
                    cursor.execute("""
                        UPDATE admins
                        SET name = %s, email = %s, department = %s, mobile_number = %s
                        WHERE email = %s
                    """, (name, email, department, mobile_number, old_email))

                conn.commit()

                session['admin_name'] = name
                session['admin_email'] = email
                session['admin_department'] = department
                session['admin_mobile'] = mobile_number

                if email_changed:
                    token = generate_email_token(email, "admin")
                    verify_link = url_for('verify_email', token=token, _external=True)
                    send_verification_email(email, verify_link, "admin")
                    flash("Admin details updated! A verification link has been sent to your new email.")
                else:
                    flash("Admin details updated successfully!")

                return redirect(url_for('admin'))

            except Exception as e:
                conn.rollback()
                print("Admin change details error:", str(e))
                flash("Something went wrong while updating admin details")
                return redirect(url_for('admin_change_details'))

            finally:
                cursor.close()
                conn.close()

        # ── Step 2: Verify mobile OTP ──
        elif form_type == 'verify_mobile_otp':
            pending = session.get('pending_admin_mobile_otp')
            if not pending:
                flash("No pending verification found. Please try again.")
                return redirect(url_for('admin_change_details'))

            otp_input = request.form['otp'].strip()
            otp_time = datetime.fromisoformat(pending['otp_time'])

            if datetime.now() - otp_time > timedelta(minutes=10):
                flash("Verification code has expired. Please resend.")
                return redirect(url_for('admin_change_details'))

            if otp_input != pending['otp']:
                flash("Invalid verification code. Please try again.")
                return redirect(url_for('admin_change_details'))

            # OTP verified — now update the profile
            name = pending['name']
            email = pending['email']
            department = pending['department']
            mobile_number = pending['mobile_number']
            old_email = session['admin_email']
            email_changed = (email.lower() != old_email.lower())

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email FROM admins WHERE email = %s AND email != %s",
                (email, old_email)
            )
            existing_admin = cursor.fetchone()

            if existing_admin:
                cursor.close()
                conn.close()
                session.pop('pending_admin_mobile_otp', None)
                flash("Email already exists with another admin account")
                return redirect(url_for('admin_change_details'))

            try:
                if email_changed:
                    cursor.execute("""
                        UPDATE admins
                        SET name = %s, email = %s, department = %s, mobile_number = %s, is_verified = 0
                        WHERE email = %s
                    """, (name, email, department, mobile_number, old_email))
                else:
                    cursor.execute("""
                        UPDATE admins
                        SET name = %s, email = %s, department = %s, mobile_number = %s
                        WHERE email = %s
                    """, (name, email, department, mobile_number, old_email))

                conn.commit()

                session['admin_name'] = name
                session['admin_email'] = email
                session['admin_department'] = department
                session['admin_mobile'] = mobile_number
                session.pop('pending_admin_mobile_otp', None)

                if email_changed:
                    token = generate_email_token(email, "admin")
                    verify_link = url_for('verify_email', token=token, _external=True)
                    send_verification_email(email, verify_link, "admin")
                    flash("Mobile verified & admin details updated! A verification link has been sent to your new email.")
                else:
                    flash("Mobile number verified & admin details updated successfully!")

                return redirect(url_for('admin'))

            except Exception as e:
                conn.rollback()
                print("Admin change details error:", str(e))
                flash("Something went wrong while updating admin details")
                return redirect(url_for('admin_change_details'))

            finally:
                cursor.close()
                conn.close()

        # ── Step 3: Resend mobile OTP ──
        elif form_type == 'resend_mobile_otp':
            pending = session.get('pending_admin_mobile_otp')
            if not pending:
                flash("No pending verification found. Please try again.")
                return redirect(url_for('admin_change_details'))

            otp = generate_sms_otp()
            pending['otp'] = otp
            pending['otp_time'] = datetime.now().isoformat()
            session['pending_admin_mobile_otp'] = pending

            send_otp_sms(pending['mobile_number'], otp)
            flash("A new verification code has been sent to your mobile number.")
            return redirect(url_for('admin_change_details'))

    return render_template('admin_change_details.html', admin=current_admin)


@app.route('/admin_change_details_cancel_otp')
def admin_change_details_cancel_otp():
    session.pop('pending_admin_mobile_otp', None)
    return redirect(url_for('admin_change_details'))


# ================= PROFILE PHOTO UPLOAD =================
@app.route('/upload_profile_photo', methods=['POST'])
def upload_profile_photo():
    if not session.get('user_email'):
        return jsonify({'error': 'Login required'}), 401

    if 'photo' not in request.files:
        flash('No file selected')
        return redirect(url_for('dashboard'))

    file = request.files['photo']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('dashboard'))

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"user_{session['user_id']}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET profile_photo = %s WHERE email = %s", (filename, session['user_email']))
        conn.commit()
        cursor.close()
        conn.close()

        session['user_photo'] = filename
        flash('Profile photo updated!')
    else:
        flash('Invalid file type. Use JPG, PNG, or GIF.')

    return redirect(url_for('dashboard'))


@app.route('/admin_upload_profile_photo', methods=['POST'])
def admin_upload_profile_photo():
    if not session.get('admin_email'):
        return jsonify({'error': 'Login required'}), 401

    if 'photo' not in request.files:
        flash('No file selected')
        return redirect(url_for('admin'))

    file = request.files['photo']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('admin'))

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"admin_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET profile_photo = %s WHERE email = %s", (filename, session['admin_email']))
        conn.commit()
        cursor.close()
        conn.close()

        session['admin_photo'] = filename
        flash('Profile photo updated!')
    else:
        flash('Invalid file type. Use JPG, PNG, or GIF.')

    return redirect(url_for('admin'))


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
