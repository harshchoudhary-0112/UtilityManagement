import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Harsh@966933",
    database="utility_portalll"
)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE workers ADD COLUMN login_verified TINYINT DEFAULT 0")
    conn.commit()
    print("SUCCESS: login_verified column added to workers table")
except mysql.connector.errors.ProgrammingError as e:
    if "Duplicate column name" in str(e):
        print("Column login_verified already exists - no action needed")
    else:
        print(f"ERROR: {e}")
except Exception as e:
    print(f"ERROR: {e}")
finally:
    cursor.close()
    conn.close()
