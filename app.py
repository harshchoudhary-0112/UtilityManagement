import uuid
from datetime import datetime, timedelta
import mysql.connector
from flask import Flask, render_template, request, redirect, flash, url_for, session
from twilio.rest import Client


app = Flask(__name__)
app.secret_key = "secret123"


# ================= CACHE CONTROL =================
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ================= DATABASE - SINGLE CONSISTENT CONNECTION =================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Harsh@966933",
        database="utility_portalll"
    )


# ================= TWILIO CONFIGURATION =================
# Replace these with your actual Twilio credentials
TWILIO_ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"  # your real SID
TWILIO_AUTH_TOKEN  = "your_auth_token"                   # your real token
TWILIO_PHONE_NUMBER = "+1234567890"                      # your Twilio number

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def sanitize_phone(n):
    """Ensure mobile number is in +91XXXXXXXXXX format (India)."""
    n = str(n).strip()
    if not n.startswith("9"):
        # If it starts with 0, remove 0
        if n.startswith("0"):
            n = n[1:]
    else:
        # If it's 10 digits starting with 9, add +91
        if len(n) == 10 and n[0] == "9":
            n = "91" + n
    if not n.startswith("+"):
        n = "+" + n
    return n


def notify_users(ward, message):
    """Send SMS only to ward-specific registered users."""
    if ward == "all":
        return  # skip SMS for general announcements

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT mobile_number FROM users WHERE ward = %s AND mobile_number IS NOT NULL AND mobile_number != ''", (ward,))
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
    return render_template('home.html', announcements=announcements)


# ================= USER DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if not session.get('user_email'):
        return redirect(url_for('login'))

    user_ward = session.get('user_ward')
    conn = get_db_connection()
    cursor = conn.cursor()

    # General announcements
    cursor.execute("""
        SELECT id, ward, message, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
    """, ("all",))
    general_announcements = cursor.fetchall()

    # Ward-specific announcements
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
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, ward, password, mobile_number FROM users WHERE email = %s AND password = %s",
            (email, password)
        )
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session['user_ward'] = user[3]
            session['user_mobile'] = user[5]
            flash("Login successful!")
            cursor.close()
            conn.close()
            return redirect('/dashboard')
        else:
            flash("Invalid credentials")
        cursor.close()
        conn.close()

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        ward = request.form['ward']
        mobile_number = request.form['mobile_number']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users(name, email, ward, mobile_number, password) VALUES(%s, %s, %s, %s, %s)",
            (name, email, ward, mobile_number, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Signup successful! Please login.")
        return redirect('/login')

    return render_template('signup.html')


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
    cursor.execute(
        "SELECT id, name, ward, category, description, status, admin_reply, created_at "
        "FROM complaintss WHERE user_email = %s ORDER BY created_at DESC",
        (email,)
    )
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('track_complaints.html', complaints=complaints)


# ================= ADMIN =================
@app.route('/adminpage')
def adminpage():
    if session.get('admin_email'):
        return redirect('/admin')
    return render_template('admin_login.html')


@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        department = request.form['department']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM admins WHERE email = %s AND password = %s AND department = %s",
            (email, password, department)
        )
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            session['admin_email'] = email
            session['admin_department'] = department
            flash('Login successful')
            return redirect('/admin')
        else:
            flash('Invalid email, password, or department')
            return redirect('/adminlogin')

    return render_template('admin_login.html')


@app.route('/admin')
def admin_dashboard():
    if 'admin_email' not in session:
        return redirect('/adminlogin')

    department = session.get('admin_department')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaintss WHERE department = %s", (department,))
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_dash.html', complaints=complaints)


@app.route('/update_complaint/<int:id>', methods=['POST'])
def update_complaint(id):
    if 'admin_email' not in session:
        return redirect('/adminpage')
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
    return redirect('/admin')


@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if 'admin_email' not in session:
        flash("Admin login required")
        return redirect('/adminpage')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM complaintss WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Complaint deleted successfully!")
    return redirect('/admin')


# ================= ADMIN ANNOUNCEMENTS =================
@app.route('/admin/announcement', methods=['GET', 'POST'])
def admin_announcement():
    if 'admin_email' not in session:
        return redirect('/adminpage')

    if request.method == 'POST':
        ward = request.form['ward'].strip()
        message = request.form['message'].strip()

        if not ward or ward == "":
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

        # Send SMS only for ward-specific announcements
        if ward != "all":
            notify_users(ward, message)

        flash("Announcement sent successfully!")
        return redirect('/admin/announcement')

    return render_template('admin_announcement.html')


# ================= EDIT GENERAL ANNOUNCEMENT =================
@app.route('/edit_announcement', methods=['GET', 'POST'])
def edit_announcement():
    if 'admin_email' not in session:
        return redirect('/adminpage')

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

        # Only send SMS for ward-specific, not "all"
        if ward != "all":
            notify_users(ward, announcement)

        flash("Announcement added successfully!")
        return redirect('/edit_announcement')

    return render_template('edit_announcement.html')


# ================= PASSWORD RESET =================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(minutes=15)
            cursor.execute(
                "UPDATE users SET reset_token = %s, token_expiry = %s WHERE email = %s",
                (token, expiry, email)
            )
            conn.commit()
            print(f"Reset link: http://127.0.0.1:5000/reset-password/{token}")
            flash("Reset link generated (check console)")
        else:
            flash("Email not found")
        cursor.close()
        conn.close()
    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE reset_token = %s AND token_expiry > NOW()",
        (token,)
    )
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        return "Invalid or expired token"

    if request.method == 'POST':
        new_pass = request.form['password']
        cursor.execute(
            "UPDATE users SET password = %s, reset_token = NULL, token_expiry = NULL WHERE reset_token = %s",
            (new_pass, token)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Password updated!")
        return redirect('/login')

    cursor.close()
    conn.close()
    return render_template('reset_password.html')


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)