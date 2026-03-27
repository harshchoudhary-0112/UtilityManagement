from flask import Flask,render_template,request,redirect,url_for
import uuid
from datetime import datetime, timedelta
import mysql.connector
from flask import Flask, render_template, request, redirect, flash



app = Flask(__name__)
app.secret_key = "secret123"

db=mysql.connector.connect(
host="localhost",
user="root",
password="Harsh@966933",
database="utility_portall"
)

cursor=db.cursor()

# LANDING PAGE
@app.route('/')
def home():

    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Harsh@966933",
        database="utility_portall"
    )

    cursor = conn.cursor()

    cursor.execute("SELECT message FROM announcements WHERE id=1")
    result = cursor.fetchone()

    announcement = result[0] if result else "No announcements"

    cursor.close()
    conn.close()

    return render_template('home.html', announcement=announcement)

@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():

    name = request.form['name']
    ward = request.form['ward']
    category = request.form['category']
    description = request.form['description']

    sql = "INSERT INTO complaints (name, ward, category, description) VALUES (%s,%s,%s,%s)"
    val = (name, ward, category, description)

    cursor.execute(sql, val)
    db.commit()

    flash("Complaint Submitted Successfully!")

    return redirect('/')

# LOGIN PAGE
@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/adminpage')
def adminpage():
    return render_template("admin_login.html")

@app.route('/signup',methods=['POST'])
def signup():

    name=request.form['name']
    email=request.form['email']
    ward=request.form['ward']
    password=request.form['password']

    sql="INSERT INTO users(name,email,ward,password) VALUES(%s,%s,%s,%s)"
    val=(name,email,ward,password)

    cursor.execute(sql,val)
    db.commit()

    return redirect('/login')


@app.route('/loginuser',methods=['POST'])
def loginuser():

    email=request.form['email']
    password=request.form['password']

    sql="SELECT * FROM users WHERE email=%s AND password=%s"
    val=(email,password)

    cursor.execute(sql,val)
    user=cursor.fetchone()

    if user:
        return redirect('/complaint')
    else:
        return "Invalid Login"

@app.route('/edit_announcement', methods=['GET','POST'])
def edit_announcement():

    if request.method == 'POST':
        announcement = request.form['announcement']

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Harsh@966933",
            database="utility_portall"
        )

        cursor = conn.cursor()

        cursor.execute("SELECT * FROM announcements WHERE id=1")
        data = cursor.fetchone()

        if data:
            cursor.execute("UPDATE announcements SET message=%s WHERE id=1", (announcement,))
        else:
            cursor.execute("INSERT INTO announcements (id, message) VALUES (1, %s)", (announcement,))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('home'))

    return render_template('edit_announcement.html')


@app.route('/update_announcement', methods=['POST'])
def update_announcement():

    message = request.form['message']

    sql = "UPDATE announcements SET message=%s WHERE id=1"
    val = (message,)

    cursor.execute(sql,val)
    db.commit()

    return redirect('/')        

@app.route('/complaint')
def complaint():
    return render_template("complaint.html")


@app.route('/adminlogin', methods=['POST'])
def adminlogin():

    email = request.form['email']
    password = request.form['password']

    if email == "admin@gmail.com" and password == "admin123":

        cursor.execute("SELECT * FROM complaints")
        data = cursor.fetchall()

        return render_template("admin_dash.html", complaints=data)

    else:
        return "Invalid Admin Login"
    
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # First check users table
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        table = "users"

        # If not found → check admin table
        if not user:
            cursor.execute("SELECT * FROM admins WHERE email=%s", (email,))
            user = cursor.fetchone()
            table = "admins"

        if user:
            token = str(uuid.uuid4())
            expiry = datetime.now() + timedelta(minutes=15)

            cursor.execute(
                 f"UPDATE {table} SET reset_token=%s, token_expiry=%s WHERE email=%s",
                     (token, expiry, email)
            )
            db.commit()

            reset_link = f"http://127.0.0.1:5000/reset-password/{token}"
            print("Reset link:", reset_link)  

            flash("Reset link sent! Check Your email.")
            return redirect('/forgot-password')
        else:
            flash("Email not found!")
            return redirect('/forgot-password')
        
    return render_template('forgot_password.html')    
       
@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    cursor.execute(
        "SELECT * FROM users WHERE reset_token=%s AND token_expiry > NOW()",
        (token,)
    )
    user = cursor.fetchone()

    if not user:
        return "Invalid or expired token"

    if request.method == 'POST':
        new_password = request.form['password']

        cursor.execute(
            "UPDATE users SET password=%s, reset_token=NULL, token_expiry=NULL WHERE reset_token=%s",
            (new_password, token)
        )
        db.commit()

        flash("Password updated successfully!")
        return redirect('/')
    return render_template('reset_password.html')       
        
@app.route('/admin')
def admin():

    cursor.execute("SELECT * FROM complaints")
    data=cursor.fetchall()

    return render_template("admin.html",complaints=data)


if __name__=="__main__":
    app.run(debug=True)