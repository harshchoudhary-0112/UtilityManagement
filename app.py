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

# ================= DATABASE =================
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Harsh@966933",
    database="utility_portalll"
)
cursor = db.cursor()

# ================= TWILIO =================
TWILIO_ACCOUNT_SID = 'YOUR_TWILIO_SID'
TWILIO_AUTH_TOKEN = 'YOUR_TWILIO_AUTH_TOKEN'
TWILIO_PHONE_NUMBER = '+1234567890'
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def notify_users(ward, message):
    cursor.execute("SELECT mobile_number FROM users WHERE ward=%s", (ward,))
    numbers = cursor.fetchall()
    for number in numbers:
        try:
            twilio_client.messages.create(
                body=f"New announcement for your ward: {message}",
                from_=TWILIO_PHONE_NUMBER,
                to=number[0]
            )
        except Exception as e:
            print(f"Failed to send SMS to {number[0]}: {e}")

# ================= HOME =================
@app.route('/')
def home():
    cursor.execute("""
        SELECT message, ward, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, ('all',))
    announcements = cursor.fetchall()
    return render_template('home.html', announcements=announcements)

# ================= USER DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if not session.get('user_email'):
        return redirect(url_for('login'))

    user_ward = session.get('user_ward')

    # General announcements
    cursor.execute("""
        SELECT id, ward, message, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
    """, ('all',))
    general_announcements = cursor.fetchall()

    # Ward-specific announcements
    cursor.execute("""
        SELECT id, ward, message, created_at
        FROM announcements
        WHERE ward = %s
        ORDER BY created_at DESC
    """, (user_ward,))
    ward_announcements = cursor.fetchall()

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
        cursor.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_email'] = user[2]
            session['user_ward'] = user[3]
            session['user_mobile'] = user[5]   
            flash("Login successful!")
            return redirect('/dashboard')
        else:
            flash("Invalid credentials")
            return redirect('/login')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        ward = request.form['ward']
        mobile_number = request.form['mobile_number']  # NEW FIELD
        password = request.form['password']

        cursor.execute(
            "INSERT INTO users(name,email,ward,mobile_number,password) VALUES(%s,%s,%s,%s,%s)",
            (name, email, ward, mobile_number, password)
        )
        db.commit()

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
    if not session.get('user_email'):
        flash("Please login first")
        return redirect('/login')
    if request.method == 'POST':
        name = request.form['name']
        ward = request.form['ward']
        category = request.form['category']
        description = request.form['description']
        user_email = session['user_email']

        cursor.execute("""
            INSERT INTO complaints (name, ward, category, description, user_email, status, admin_reply)
            VALUES (%s,%s,%s,%s,%s,'Pending','')
        """, (name, ward, category, description, user_email))
        db.commit()
        flash("Complaint submitted successfully!")
        return redirect('/track_complaints')

    return render_template('register_complaint.html')

@app.route('/track_complaints')
def track_complaints():
    if not session.get('user_email'):
        flash("Please login first")
        return redirect('/login')

    email = session['user_email']
    cursor.execute("SELECT id,name,ward,category,description,status,admin_reply,created_at FROM complaints WHERE user_email=%s ORDER BY created_at DESC", (email,))
    complaints = cursor.fetchall()
    return render_template('track_complaints.html', complaints=complaints)

# ================= ADMIN =================
@app.route('/adminpage')
def adminpage():
    if session.get('admin'):
        return redirect('/admin')
    return render_template('admin_login.html')

@app.route('/adminlogin', methods=['POST'])
def adminlogin():
    email = request.form['email']
    password = request.form['password']
    if email == "admin@gmail.com" and password == "admin123":
        session['admin'] = True
        cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
        data = cursor.fetchall()
        return render_template('admin_dash.html', complaints=data)
    else:
        flash("Invalid Admin Login")
        return redirect('/adminpage')

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/adminpage')
    cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC")
    data = cursor.fetchall()
    return render_template('admin_dash.html', complaints=data)

@app.route('/update_complaint/<int:id>', methods=['POST'])
def update_complaint(id):
    if 'admin' not in session:
        return redirect('/adminpage')
    status = request.form['status']
    reply = request.form['admin_reply']
    cursor.execute("UPDATE complaints SET status=%s, admin_reply=%s WHERE id=%s", (status, reply, id))
    db.commit()
    flash("Updated successfully")
    return redirect('/admin')

@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if 'admin' not in session:
        flash("Admin login required")
        return redirect('/adminpage')
    cursor.execute("DELETE FROM complaints WHERE id=%s", (id,))
    db.commit()
    flash("Complaint deleted successfully!")
    return redirect('/admin')

# ================= ADMIN ANNOUNCEMENTS =================
@app.route('/admin/announcement', methods=['GET', 'POST'])
def admin_announcement():
    if 'admin' not in session:
        return redirect('/adminpage')

    if request.method == 'POST':
        ward = request.form['ward'].strip()
        message = request.form['message'].strip()

        if ward == "":
            ward = "all"

        cursor.execute(
            "INSERT INTO announcements (ward, message, created_at) VALUES (%s, %s, NOW())",
            (ward, message)
        )
        db.commit()

        if ward != "all":
            notify_users(ward, message)

        flash("Announcement sent successfully!")
        return redirect('/admin/announcement')

    return render_template('admin_announcement.html')

# ================= EDIT GENERAL ANNOUNCEMENT =================
@app.route('/edit_announcement', methods=['GET', 'POST'])
def edit_announcement():
    if 'admin' not in session:
        return redirect('/adminpage')

    if request.method == 'POST':
        announcement = request.form['announcement'].strip()
        ward = request.form.get('ward', 'all').strip()

        if ward == "":
            ward = "all"

        cursor.execute(
            "INSERT INTO announcements (ward, message, created_at) VALUES (%s, %s, NOW())",
            (ward, announcement)
        )
        db.commit()

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
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if user:
            token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(minutes=15)
            cursor.execute("UPDATE users SET reset_token=%s, token_expiry=%s WHERE email=%s", (token, expiry, email))
            db.commit()
            print(f"Reset link: http://127.0.0.1:5000/reset-password/{token}")
            flash("Reset link generated (check console)")
        else:
            flash("Email not found")
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cursor.execute("SELECT * FROM users WHERE reset_token=%s AND token_expiry > NOW()", (token,))
    user = cursor.fetchone()
    if not user:
        return "Invalid or expired token"
    if request.method == 'POST':
        new_pass = request.form['password']
        cursor.execute("UPDATE users SET password=%s, reset_token=NULL, token_expiry=NULL WHERE reset_token=%s", (new_pass, token))
        db.commit()
        flash("Password updated!")
        return redirect('/login')
    return render_template('reset_password.html')

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)