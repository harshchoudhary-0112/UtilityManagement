import uuid
from datetime import datetime, timedelta
import mysql.connector
from flask import Flask, render_template, request, redirect, flash, url_for, session
from twilio.rest import Client
import re


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
TWILIO_ACCOUNT_SID = "ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE_NUMBER = "+1234567890"


twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)



def sanitize_phone(n):
    """Ensure mobile number is in +91XXXXXXXXXX format (India)."""
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
    """Send SMS only to ward-specific registered users."""
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


        cursor.execute(
            "INSERT INTO users (name, email, ward, mobile_number, password) VALUES (%s, %s, %s, %s, %s)",
            (name, email, ward, mobile_number, password)
        )
        conn.commit()
        cursor.close()
        conn.close()


        flash("Signup successful! Please login.")
        return redirect(url_for('login'))


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
        return redirect(url_for('admin'))
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
            "SELECT name, email, department FROM admins WHERE email = %s AND password = %s AND department = %s",
            (email, password, department)
        )
        admin = cursor.fetchone()
        cursor.close()
        conn.close()


        if admin:
            session['admin_email'] = admin[1]
            session['admin_name'] = admin[0]      
            session['admin_department'] = admin[2]
            flash('Login successful')
            return redirect(url_for('admin'))
        else:
            flash('Invalid email, password, or department')
            return redirect(url_for('adminlogin'))


    return render_template('admin_login.html')

@app.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        department = request.form['department'].strip()
        mobile_number = request.form['mobile_number'].strip()
        password = request.form['password']

        if not re.fullmatch(r"[A-Za-z\s]{2,50}", name):
            flash("Full name must contain only letters and spaces")
            return redirect(url_for('admin_signup'))

        if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Enter a valid email address")
            return redirect(url_for('admin_signup'))

        if not re.fullmatch(r"[A-Za-z\s]{2,50}", department):
            flash("Department must contain only letters and spaces")
            return redirect(url_for('admin_signup'))

        if not re.fullmatch(r"\d{10}", mobile_number):
            flash("Mobile number must be exactly 10 digits")
            return redirect(url_for('admin_signup'))

        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", password):
            flash("Password must be 8 to 20 characters and include uppercase, lowercase, number, and special character")
            return redirect(url_for('admin_signup'))

        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            cursor.close()
            conn.close()
            flash("Admin email already registered. Please login.")
            return redirect(url_for('admin_signup'))

       
        cursor.execute(
            "INSERT INTO admins (name, email, department, mobile_number, password) VALUES (%s, %s, %s, %s, %s)",
            (name, email, department, mobile_number, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Admin signup successful! Please login.")
        return redirect(url_for('adminlogin'))

    return render_template('admin_signup.html')

@app.route('/admin')
def admin():
    if 'admin_email' not in session:
        return redirect(url_for('adminlogin'))


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



@app.route('/delete_complaint/<int:id>', methods=['POST'])
def delete_complaint(id):
    if 'admin_email' not in session:
        flash("Admin login required")
        return redirect(url_for('adminpage'))


    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM complaintss WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Complaint deleted successfully!")
    return redirect(url_for('admin'))



# ================= ADMIN ANNOUNCEMENTS =================
@app.route('/admin/announcement', methods=['GET', 'POST'])
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



# ================= EDIT GENERAL ANNOUNCEMENT =================
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
            print(f"🔗 Reset link: http://127.0.0.1:5000/reset-password/{token}")
            flash("Reset link generated (check console for link)")
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
        flash("Invalid or expired token")
        return redirect(url_for('login'))


    if request.method == 'POST':
        new_pass = request.form['password']


        if not re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,20}$", new_pass):
            flash("Password must be 8-20 characters with uppercase, lowercase, number, and special character")
            cursor.close()
            conn.close()
            return render_template('reset_password.html')


        cursor.execute(
            "UPDATE users SET password = %s, reset_token = NULL, token_expiry = NULL WHERE reset_token = %s",
            (new_pass, token)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Password updated successfully!")
        return redirect(url_for('login'))


    cursor.close()
    conn.close()
    return render_template('reset_password.html')



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


        if not user or user[0] != current_password:
            cursor.close()
            conn.close()
            flash("Current password is incorrect")
            return redirect(url_for('change_password'))


        cursor.execute(
            "UPDATE users SET password = %s WHERE email = %s",
            (new_password, session['user_email'])
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


        if admin_data[0] != current_password:
            cursor.close()
            conn.close()
            flash("Current password is incorrect")
            return redirect(url_for('admin_change_password'))


        cursor.execute(
            "UPDATE admins SET password = %s WHERE email = %s",
            (new_password, session['admin_email'])
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
        session['admin_mobile'] = new_mobile  # ✅ NEW

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
    app.run(debug=True)