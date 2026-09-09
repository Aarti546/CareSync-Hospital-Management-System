import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor

# MySQL Configuration (editable via environment or defaults)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_DB = os.getenv("MYSQL_DB", "hospital_db")

SQLITE_DB_PATH = os.path.join(os.path.dirname(__file__), "hospital.db")

_USE_MYSQL = False

def check_mysql_connection():
    """Attempts to connect to MySQL. Returns True if successful, False otherwise."""
    global _USE_MYSQL
    try:
        # First connect without db to ensure server is reachable
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            connect_timeout=2
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
        conn.close()

        # Connect to target database
        conn = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            database=MYSQL_DB,
            cursorclass=DictCursor,
            connect_timeout=2
        )
        conn.close()
        _USE_MYSQL = True
        return True
    except Exception as e:
        _USE_MYSQL = False
        return False

# Initialize connection check at import
check_mysql_connection()

def get_db_type():
    return "MySQL" if _USE_MYSQL else "SQLite (Local Fallback)"

def get_connection():
    """Returns an active database connection."""
    if _USE_MYSQL:
        return pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            database=MYSQL_DB,
            cursorclass=DictCursor,
            autocommit=True
        )
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def execute_query(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and returns the lastrowid or affected rows."""
    params = params or ()
    conn = get_connection()
    try:
        if _USE_MYSQL:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                last_id = cursor.lastrowid
                conn.commit()
                return last_id
        else:
            # For SQLite, convert %s placeholders to ?
            sqlite_sql = sql.replace("%s", "?")
            cursor = conn.cursor()
            cursor.execute(sqlite_sql, params)
            last_id = cursor.lastrowid
            conn.commit()
            return last_id
    finally:
        conn.close()

def query_all(sql, params=None):
    """Executes a SELECT query and returns all matching rows as a list of dictionaries."""
    params = params or ()
    conn = get_connection()
    try:
        if _USE_MYSQL:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall() or []
        else:
            sqlite_sql = sql.replace("%s", "?")
            cursor = conn.cursor()
            cursor.execute(sqlite_sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()

def query_one(sql, params=None):
    """Executes a SELECT query and returns a single row as a dictionary, or None."""
    params = params or ()
    conn = get_connection()
    try:
        if _USE_MYSQL:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        else:
            sqlite_sql = sql.replace("%s", "?")
            cursor = conn.cursor()
            cursor.execute(sqlite_sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()

def init_db():
    """Initializes the database schema for either MySQL or SQLite."""
    conn = get_connection()
    try:
        if _USE_MYSQL:
            with conn.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    age INT NOT NULL,
                    gender VARCHAR(10) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    email VARCHAR(100),
                    blood_group VARCHAR(10),
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    specialization VARCHAR(100) NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    email VARCHAR(100),
                    available_days VARCHAR(100) DEFAULT 'Mon,Tue,Wed,Thu,Fri',
                    available_time VARCHAR(50) DEFAULT '09:00 AM - 05:00 PM',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
                    patient_id INT NOT NULL,
                    doctor_id INT NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time VARCHAR(20) NOT NULL,
                    reason TEXT,
                    status VARCHAR(20) DEFAULT 'Confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                    UNIQUE KEY unique_doctor_slot (doctor_id, appointment_date, appointment_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
        else:
            with conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER NOT NULL,
                    gender TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    blood_group TEXT,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS doctors (
                    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    specialization TEXT NOT NULL,
                    department TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    available_days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri',
                    available_time TEXT DEFAULT '09:00 AM - 05:00 PM',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'Confirmed',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE,
                    UNIQUE (doctor_id, appointment_date, appointment_time)
                );
                """)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print(f"Database successfully initialized using: {get_db_type()}")
