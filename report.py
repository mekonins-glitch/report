"""
Toll Operations Manager - Complete Application
Single File: toll_operations.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="🚦 Toll Operations Manager",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- CUSTOM CSS FOR ARTISTIC DESIGN --------------------
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* Card style for metrics */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s;
        border-left: 5px solid #FF4B4B;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.15);
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .manager-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .manager-btn > button {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* Success message styling */
    .stSuccess {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        border-radius: 10px;
        padding: 1rem;
        border: none;
    }
    
    /* Danger button */
    .stButton > button.danger {
        background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
    }
    .stButton > button.danger:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 15px rgba(244, 67, 54, 0.4);
    }
    
    /* Form styling */
    .stForm {
        background: white;
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: white;
        padding: 0.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.5rem 1.5rem;
        font-weight: bold;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Custom divider */
    .custom-divider {
        height: 3px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 1.5rem;
        color: #666;
        font-size: 0.9rem;
        border-top: 1px solid #ddd;
        margin-top: 3rem;
    }
    
    /* Badge styling */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-supervisor {
        background: #667eea;
        color: white;
    }
    .badge-manager {
        background: #f5576c;
        color: white;
    }
    
    /* Manager stats card */
    .manager-stats {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .manager-stats h2 {
        margin: 0;
        color: #f5576c;
        font-size: 2.5rem;
    }
    .manager-stats p {
        color: #666;
        margin: 0.5rem 0 0 0;
    }
    
    /* Shift badge styling */
    .shift-badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .shift-a {
        background: #4CAF50;
        color: white;
    }
    .shift-b {
        background: #FF9800;
        color: white;
    }
    .shift-c {
        background: #f44336;
        color: white;
    }
    
    /* Duplicate warning */
    .duplicate-warning {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    
    /* Chart container */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- CONSTANTS --------------------
STATIONS = ["Modjo East", "Koka", "Bote", "Meki", "Batu"]
SHIFTS = ["A", "B", "C"]
STATION_COLORS = {
    "Modjo East": "#667eea",
    "Koka": "#f093fb",
    "Bote": "#4CAF50",
    "Meki": "#FF9800",
    "Batu": "#f44336"
}
SHIFT_COLORS = {
    "A": "#4CAF50",
    "B": "#FF9800",
    "C": "#f44336"
}

# -------------------- DATABASE SETUP --------------------
DB_FILE = "toll_operations.db"

def init_database():
    """Initialize SQLite database with tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            station TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create reports table with date and shift columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date DATE,
            shift TEXT,
            timestamp TIMESTAMP NOT NULL,
            supervisor TEXT NOT NULL,
            station TEXT NOT NULL,
            exit_sys INTEGER DEFAULT 0,
            entry_sys INTEGER DEFAULT 0,
            exit_man INTEGER DEFAULT 0,
            entry_man INTEGER DEFAULT 0,
            exit_etc INTEGER DEFAULT 0,
            entry_etc INTEGER DEFAULT 0,
            cash_sys REAL DEFAULT 0,
            cash_man REAL DEFAULT 0,
            etc REAL DEFAULT 0,
            thermal_in INTEGER DEFAULT 0,
            thermal_out INTEGER DEFAULT 0,
            gen_fuel REAL DEFAULT 0,
            veh_fuel REAL DEFAULT 0,
            no_card INTEGER DEFAULT 0,
            forged_count INTEGER DEFAULT 0,
            forged_amt REAL DEFAULT 0,
            overload_count INTEGER DEFAULT 0,
            overload_amt REAL DEFAULT 0,
            gen_hour REAL DEFAULT 0,
            good_notes TEXT,
            problems TEXT,
            FOREIGN KEY (supervisor) REFERENCES users(username),
            UNIQUE(station, report_date, shift)
        )
    ''')
    
    # Create password change history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    conn.commit()
    conn.close()

def migrate_database():
    """Migrate existing database to add new columns"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(reports)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    new_columns = {
        'report_date': 'DATE',
        'shift': 'TEXT',
        'exit_etc': 'INTEGER DEFAULT 0',
        'entry_etc': 'INTEGER DEFAULT 0'
    }
    
    for col, col_type in new_columns.items():
        if col not in columns:
            try:
                cursor.execute(f'ALTER TABLE reports ADD COLUMN {col} {col_type}')
                if col == 'report_date':
                    cursor.execute('UPDATE reports SET report_date = DATE(timestamp) WHERE report_date IS NULL')
                elif col == 'shift':
                    cursor.execute('UPDATE reports SET shift = "A" WHERE shift IS NULL')
            except sqlite3.OperationalError:
                pass
    
    # Create unique index if it doesn't exist
    try:
        cursor.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_report 
            ON reports(station, report_date, shift)
        ''')
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user():
    """Create only the admin user if it doesn't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if admin already exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    admin_exists = cursor.fetchone()[0]
    
    if not admin_exists:
        # Create admin user
        cursor.execute('''
            INSERT INTO users (username, password_hash, station, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', hash_password('admin123'), 'All Stations', 'manager'))
        print("✅ Admin user created successfully!")
    else:
        print("ℹ️ Admin user already exists.")
    
    conn.commit()
    conn.close()

def get_user(username):
    """Get user from database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT username, password_hash, station, role FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "username": user[0],
            "password_hash": user[1],
            "station": user[2],
            "role": user[3]
        }
    return None

def update_password(username, new_password):
    """Update user password"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users SET password_hash = ? WHERE username = ?
    ''', (hash_password(new_password), username))
    cursor.execute('''
        INSERT INTO password_history (username) VALUES (?)
    ''', (username,))
    conn.commit()
    conn.close()

def save_report(record):
    """Save report to database with duplicate prevention"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if duplicate exists
        cursor.execute('''
            SELECT COUNT(*) FROM reports 
            WHERE station = ? AND report_date = ? AND shift = ?
        ''', (record['station'], record['report_date'], record['shift']))
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Update existing record
            cursor.execute('''
                UPDATE reports SET
                    timestamp = ?,
                    supervisor = ?,
                    exit_sys = ?,
                    entry_sys = ?,
                    exit_man = ?,
                    entry_man = ?,
                    exit_etc = ?,
                    entry_etc = ?,
                    cash_sys = ?,
                    cash_man = ?,
                    etc = ?,
                    thermal_in = ?,
                    thermal_out = ?,
                    gen_fuel = ?,
                    veh_fuel = ?,
                    no_card = ?,
                    forged_count = ?,
                    forged_amt = ?,
                    overload_count = ?,
                    overload_amt = ?,
                    gen_hour = ?,
                    good_notes = ?,
                    problems = ?
                WHERE station = ? AND report_date = ? AND shift = ?
            ''', (
                record['timestamp'],
                record['supervisor'],
                record['exit_sys'],
                record['entry_sys'],
                record['exit_man'],
                record['entry_man'],
                record['exit_etc'],
                record['entry_etc'],
                record['cash_sys'],
                record['cash_man'],
                record['etc'],
                record['thermal_in'],
                record['thermal_out'],
                record['gen_fuel'],
                record['veh_fuel'],
                record['no_card'],
                record['forged_count'],
                record['forged_amt'],
                record['overload_count'],
                record['overload_amt'],
                record['gen_hour'],
                record['good_notes'],
                record['problems'],
                record['station'],
                record['report_date'],
                record['shift']
            ))
            conn.commit()
            result = "updated"
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO reports (
                    report_date, shift, timestamp, supervisor, station, 
                    exit_sys, entry_sys, exit_man, entry_man, exit_etc, entry_etc,
                    cash_sys, cash_man, etc, thermal_in, thermal_out, gen_fuel, veh_fuel,
                    no_card, forged_count, forged_amt, overload_count, overload_amt, gen_hour,
                    good_notes, problems
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record['report_date'], record['shift'], record['timestamp'], 
                record['supervisor'], record['station'],
                record['exit_sys'], record['entry_sys'], record['exit_man'], record['entry_man'],
                record['exit_etc'], record['entry_etc'],
                record['cash_sys'], record['cash_man'], record['etc'],
                record['thermal_in'], record['thermal_out'],
                record['gen_fuel'], record['veh_fuel'],
                record['no_card'],
                record['forged_count'], record['forged_amt'],
                record['overload_count'], record['overload_amt'],
                record['gen_hour'],
                record['good_notes'], record['problems']
            ))
            conn.commit()
            result = "inserted"
    
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            result = "duplicate"
        else:
            raise e
    
    conn.close()
    return result

def get_reports(station=None, start_date=None, end_date=None, supervisor=None, shift=None):
    """Get reports with optional filters"""
    conn = sqlite3.connect(DB_FILE)
    
    query = 'SELECT * FROM reports WHERE 1=1'
    params = []
    
    if station and station != "All Stations":
        query += ' AND station = ?'
        params.append(station)
    
    if supervisor:
        query += ' AND supervisor = ?'
        params.append(supervisor)
    
    if shift:
        query += ' AND shift = ?'
        params.append(shift)
    
    if start_date:
        query += ' AND report_date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND report_date <= ?'
        params.append(end_date)
    
    query += ' ORDER BY report_date DESC, shift ASC, timestamp DESC'
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
    except pd.errors.DatabaseError:
        query = 'SELECT * FROM reports WHERE 1=1'
        params = []
        
        if station and station != "All Stations":
            query += ' AND station = ?'
            params.append(station)
        
        if supervisor:
            query += ' AND supervisor = ?'
            params.append(supervisor)
        
        query += ' ORDER BY timestamp DESC'
        df = pd.read_sql_query(query, conn, params=params)
    
    conn.close()
    return df

def get_all_users():
    """Get all users from database"""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT username, station, role, created_at FROM users ORDER BY username', conn)
    conn.close()
    return df

def get_station_stats(station=None, shift=None, start_date=None, end_date=None):
    """Get statistics for a station or all stations with filters"""
    conn = sqlite3.connect(DB_FILE)
    
    params = []
    where_clause = "WHERE 1=1"
    
    if station:
        where_clause += " AND station = ?"
        params.append(station)
    
    if shift:
        where_clause += " AND shift = ?"
        params.append(shift)
    
    if start_date:
        where_clause += " AND report_date >= ?"
        params.append(start_date)
    
    if end_date:
        where_clause += " AND report_date <= ?"
        params.append(end_date)
    
    try:
        if station:
            query = f'''
                SELECT 
                    COUNT(*) as total_reports,
                    COALESCE(SUM(exit_sys), 0) + COALESCE(SUM(entry_sys), 0) + COALESCE(SUM(exit_etc), 0) + COALESCE(SUM(entry_etc), 0) as total_traffic,
                    COALESCE(SUM(cash_sys), 0) + COALESCE(SUM(cash_man), 0) + COALESCE(SUM(etc), 0) as total_revenue,
                    COALESCE(SUM(gen_fuel), 0) + COALESCE(SUM(veh_fuel), 0) as total_fuel,
                    COALESCE(SUM(no_card), 0) as total_no_card,
                    COALESCE(SUM(forged_count), 0) as total_forged,
                    COALESCE(SUM(forged_amt), 0) as total_forged_amt,
                    COALESCE(SUM(overload_count), 0) as total_overload,
                    COALESCE(SUM(overload_amt), 0) as total_overload_amt,
                    COALESCE(SUM(thermal_in), 0) as total_thermal_in,
                    COALESCE(SUM(thermal_out), 0) as total_thermal_out
                FROM reports {where_clause}
            '''
            df = pd.read_sql_query(query, conn, params=params)
        else:
            query = f'''
                SELECT 
                    station,
                    COUNT(*) as total_reports,
                    COALESCE(SUM(exit_sys), 0) + COALESCE(SUM(entry_sys), 0) + COALESCE(SUM(exit_etc), 0) + COALESCE(SUM(entry_etc), 0) as total_traffic,
                    COALESCE(SUM(cash_sys), 0) + COALESCE(SUM(cash_man), 0) + COALESCE(SUM(etc), 0) as total_revenue,
                    COALESCE(SUM(gen_fuel), 0) + COALESCE(SUM(veh_fuel), 0) as total_fuel,
                    COALESCE(SUM(no_card), 0) as total_no_card,
                    COALESCE(SUM(forged_count), 0) as total_forged,
                    COALESCE(SUM(forged_amt), 0) as total_forged_amt,
                    COALESCE(SUM(overload_count), 0) as total_overload,
                    COALESCE(SUM(overload_amt), 0) as total_overload_amt,
                    COALESCE(SUM(thermal_in), 0) as total_thermal_in,
                    COALESCE(SUM(thermal_out), 0) as total_thermal_out
                FROM reports {where_clause}
                GROUP BY station
            '''
            df = pd.read_sql_query(query, conn, params=params)
    except pd.errors.DatabaseError:
        if station:
            query = f'''
                SELECT 
                    COUNT(*) as total_reports,
                    COALESCE(SUM(exit_sys), 0) + COALESCE(SUM(entry_sys), 0) as total_traffic,
                    COALESCE(SUM(cash_sys), 0) + COALESCE(SUM(cash_man), 0) + COALESCE(SUM(etc), 0) as total_revenue,
                    COALESCE(SUM(gen_fuel), 0) + COALESCE(SUM(veh_fuel), 0) as total_fuel,
                    COALESCE(SUM(no_card), 0) as total_no_card,
                    COALESCE(SUM(forged_count), 0) as total_forged,
                    COALESCE(SUM(forged_amt), 0) as total_forged_amt,
                    COALESCE(SUM(overload_count), 0) as total_overload,
                    COALESCE(SUM(overload_amt), 0) as total_overload_amt
                FROM reports WHERE station = ?
            '''
            df = pd.read_sql_query(query, conn, params=(station,))
        else:
            query = f'''
                SELECT 
                    station,
                    COUNT(*) as total_reports,
                    COALESCE(SUM(exit_sys), 0) + COALESCE(SUM(entry_sys), 0) as total_traffic,
                    COALESCE(SUM(cash_sys), 0) + COALESCE(SUM(cash_man), 0) + COALESCE(SUM(etc), 0) as total_revenue,
                    COALESCE(SUM(gen_fuel), 0) + COALESCE(SUM(veh_fuel), 0) as total_fuel,
                    COALESCE(SUM(no_card), 0) as total_no_card,
                    COALESCE(SUM(forged_count), 0) as total_forged,
                    COALESCE(SUM(forged_amt), 0) as total_forged_amt,
                    COALESCE(SUM(overload_count), 0) as total_overload,
                    COALESCE(SUM(overload_amt), 0) as total_overload_amt
                FROM reports
                GROUP BY station
            '''
            df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df

def delete_report(report_id):
    """Delete a report by ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM reports WHERE id = ?', (report_id,))
    conn.commit()
    conn.close()
    return True

def delete_duplicate_reports(station, report_date, shift):
    """Delete duplicate reports for a specific station, date, and shift"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM reports 
        WHERE station = ? AND report_date = ? AND shift = ?
        ORDER BY id
    ''', (station, report_date, shift))
    rows = cursor.fetchall()
    
    deleted_count = 0
    if len(rows) > 1:
        for row in rows[1:]:
            cursor.execute('DELETE FROM reports WHERE id = ?', (row[0],))
            deleted_count += 1
    
    conn.commit()
    conn.close()
    return deleted_count

def check_shift_exists(report_date, shift, station):
    """Check if a report already exists for this date, shift, and station"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM reports 
            WHERE report_date = ? AND shift = ? AND station = ?
        ''', (report_date, shift, station))
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0
    conn.close()
    return count > 0

# -------------------- INIT DATABASE --------------------
init_database()
migrate_database()
create_admin_user()

# -------------------- INIT SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.station = ""
    st.session_state.role = ""
    st.session_state.page = "Dashboard"

# -------------------- LOGIN --------------------
def login():
    st.markdown("""
    <div class="main-header" style="text-align: center;">
        <h1 style="font-size: 3rem; margin: 0;">🚦 Toll Operations Manager</h1>
        <p style="font-size: 1.2rem; margin-top: 0.5rem;">Daily Shift Report System</p>
        <p style="font-size: 1rem; margin-top: 0.2rem; opacity: 0.9;">Modjo East • Koka • Bote • Meki • Batu</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2.5rem; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #333;">🔐 Login</h2>
            <p style="text-align: center; color: #666; font-size: 0.9rem;">Admin or Supervisor</p>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("👤 Username", key="login_username", placeholder="Enter your username")
        password = st.text_input("🔑 Password", type="password", key="login_password", placeholder="Enter your password")
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button("🚀 Login", key="login_button", use_container_width=True):
                user = get_user(username)
                if user and user["password_hash"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.station = user["station"]
                    st.session_state.role = user["role"]
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
        
        st.markdown("""
        <div style="margin-top: 1.5rem; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
            <p style="font-size: 0.8rem; color: #666; text-align: center; margin: 0;">
                <strong>Admin:</strong> admin (password: admin123)<br>
                <strong>Supervisors:</strong> Must be created by admin
            </p>
        </div>
        """, unsafe_allow_html=True)

# -------------------- TOP MENU --------------------
def top_menu():
    is_manager = st.session_state.role == "manager"
    
    st.markdown("""
    <div style="background: white; padding: 1rem 2rem; border-radius: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 2rem;">
    """, unsafe_allow_html=True)
    
    if is_manager:
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.2, 1.2, 1.2, 1.2, 1.2, 1])
        with col2:
            if st.button("📊 Dashboard", key="menu_dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
        with col3:
            if st.button("📈 Reports", key="menu_reports", use_container_width=True):
                st.session_state.page = "Reports"
                st.rerun()
        with col4:
            if st.button("📊 Analytics", key="menu_analytics", use_container_width=True):
                st.session_state.page = "Analytics"
                st.rerun()
        with col5:
            if st.button("📋 Consolidated", key="menu_consolidated", use_container_width=True):
                st.session_state.page = "Consolidated"
                st.rerun()
        with col6:
            if st.button("👥 Users", key="menu_users", use_container_width=True):
                st.session_state.page = "Users"
                st.rerun()
    else:
        col1, col2, col3, col4, col5 = st.columns([1, 1.5, 1.5, 1.5, 1])
        with col2:
            if st.button("📊 Dashboard", key="menu_dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
        with col3:
            if st.button("📝 Submit Report", key="menu_submit", use_container_width=True):
                st.session_state.page = "Submit Report"
                st.rerun()
        with col4:
            if st.button("📈 My Reports", key="menu_reports", use_container_width=True):
                st.session_state.page = "Reports"
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------- CHANGE PASSWORD --------------------
def change_password():
    with st.sidebar:
        st.markdown("---")
        st.subheader("🔑 Change Password")
        old = st.text_input("Current Password", type="password", key="old_pass")
        new = st.text_input("New Password", type="password", key="new_pass")
        confirm = st.text_input("Confirm New Password", type="password", key="confirm_pass")
        
        if st.button("Update Password", key="update_pass_btn", use_container_width=True):
            user = get_user(st.session_state.username)
            if user and user["password_hash"] == hash_password(old):
                if new != confirm:
                    st.error("New passwords do not match")
                elif len(new) < 4:
                    st.error("New password must be at least 4 characters")
                else:
                    update_password(st.session_state.username, new)
                    st.success("✅ Password updated successfully!")
            else:
                st.error("Current password is incorrect")

# -------------------- ANALYTICS CHARTS FUNCTIONS --------------------
def create_traffic_charts(df):
    """Create traffic-related charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # 1. Traffic by Station - Bar Chart
    traffic_by_station = df.groupby("station").agg({
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "exit_man": "sum",
        "entry_man": "sum"
    }).reset_index()
    
    traffic_by_station["System"] = traffic_by_station["exit_sys"] + traffic_by_station["entry_sys"]
    traffic_by_station["ETC"] = traffic_by_station["exit_etc"] + traffic_by_station["entry_etc"]
    traffic_by_station["Manual"] = traffic_by_station["exit_man"] + traffic_by_station["entry_man"]
    
    fig1 = px.bar(traffic_by_station, 
                  x="station", 
                  y=["System", "ETC", "Manual"],
                  title="Traffic Volume by Station (System vs ETC vs Manual)",
                  barmode="group",
                  color_discrete_sequence=["#667eea", "#4CAF50", "#FF9800"])
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # 2. Traffic Distribution Pie Chart
    total_system = traffic_by_station["System"].sum()
    total_etc = traffic_by_station["ETC"].sum()
    total_manual = traffic_by_station["Manual"].sum()
    
    if total_system > 0 or total_etc > 0 or total_manual > 0:
        fig2 = px.pie(values=[total_system, total_etc, total_manual],
                      names=["System", "ETC", "Manual"],
                      title="Traffic Distribution (System vs ETC vs Manual)",
                      color_discrete_sequence=["#667eea", "#4CAF50", "#FF9800"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
        charts.append(fig2)
    
    return charts

def create_revenue_charts(df):
    """Create revenue-related charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # Revenue by Station
    revenue_by_station = df.groupby("station").agg({
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum"
    }).reset_index()
    
    revenue_by_station["Cash System"] = revenue_by_station["cash_sys"]
    revenue_by_station["Cash Manual"] = revenue_by_station["cash_man"]
    revenue_by_station["ETC"] = revenue_by_station["etc"]
    
    fig1 = px.bar(revenue_by_station, 
                  x="station", 
                  y=["Cash System", "Cash Manual", "ETC"],
                  title="Revenue by Station (Cash System vs Cash Manual vs ETC)",
                  barmode="group",
                  color_discrete_sequence=["#667eea", "#4CAF50", "#f093fb"])
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # Revenue Distribution Pie
    total_cash_sys = revenue_by_station["cash_sys"].sum()
    total_cash_man = revenue_by_station["cash_man"].sum()
    total_etc = revenue_by_station["etc"].sum()
    
    if total_cash_sys > 0 or total_cash_man > 0 or total_etc > 0:
        fig2 = px.pie(values=[total_cash_sys, total_cash_man, total_etc],
                      names=["Cash System", "Cash Manual", "ETC"],
                      title="Revenue Distribution",
                      color_discrete_sequence=["#667eea", "#4CAF50", "#f093fb"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
        charts.append(fig2)
    
    return charts

def create_shift_charts(df):
    """Create shift-based charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # Traffic by Shift
    shift_traffic = df.groupby("shift").agg({
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum"
    }).reset_index()
    shift_traffic["Total"] = shift_traffic["exit_sys"] + shift_traffic["entry_sys"] + shift_traffic["exit_etc"] + shift_traffic["entry_etc"]
    
    fig1 = px.bar(shift_traffic, 
                  x="shift", 
                  y="Total",
                  title="Traffic by Shift",
                  color="shift",
                  color_discrete_sequence=["#4CAF50", "#FF9800", "#f44336"])
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # Revenue by Shift
    shift_revenue = df.groupby("shift").agg({
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum"
    }).reset_index()
    shift_revenue["Total"] = shift_revenue["cash_sys"] + shift_revenue["cash_man"] + shift_revenue["etc"]
    
    fig2 = px.pie(shift_revenue, 
                  values="Total", 
                  names="shift",
                  title="Revenue by Shift",
                  color="shift",
                  color_discrete_sequence=["#4CAF50", "#FF9800", "#f44336"])
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig2)
    
    return charts

def create_trend_charts(df):
    """Create trend charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # Daily Trends
    daily_data = df.groupby("report_date").agg({
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum"
    }).reset_index()
    
    daily_data["Total Traffic"] = daily_data["exit_sys"] + daily_data["entry_sys"] + daily_data["exit_etc"] + daily_data["entry_etc"]
    daily_data["Total Revenue"] = daily_data["cash_sys"] + daily_data["cash_man"] + daily_data["etc"]
    
    fig1 = px.line(daily_data, 
                   x="report_date", 
                   y=["Total Traffic", "Total Revenue"],
                   title="Daily Traffic and Revenue Trends",
                   color_discrete_sequence=["#667eea", "#f5576c"])
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # Daily Traffic Breakdown
    fig2 = px.area(daily_data, 
                   x="report_date", 
                   y=["exit_sys", "entry_sys", "exit_etc", "entry_etc"],
                   title="Daily Traffic Breakdown (System Exit, System Entry, ETC Exit, ETC Entry)",
                   color_discrete_sequence=["#667eea", "#f093fb", "#4CAF50", "#FF9800"])
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig2)
    
    return charts

def create_anomaly_charts(df):
    """Create anomaly/issue charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # No Card Vehicles by Station
    no_card_by_station = df.groupby("station")["no_card"].sum().reset_index()
    
    fig1 = px.bar(no_card_by_station, 
                  x="station", 
                  y="no_card",
                  title="No Card Vehicles by Station",
                  color="station",
                  color_discrete_sequence=px.colors.qualitative.Set2)
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # Forged & Overloaded Summary
    anomaly_data = df.groupby("station").agg({
        "forged_count": "sum",
        "overload_count": "sum"
    }).reset_index()
    anomaly_data["Total Issues"] = anomaly_data["forged_count"] + anomaly_data["overload_count"]
    
    if anomaly_data["Total Issues"].sum() > 0:
        fig2 = px.bar(anomaly_data, 
                      x="station", 
                      y=["forged_count", "overload_count"],
                      title="Forged Tickets and Overloaded Vehicles by Station",
                      barmode="group",
                      color_discrete_sequence=["#f44336", "#FF9800"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
        charts.append(fig2)
    
    return charts

def create_thermal_fuel_charts(df):
    """Create thermal and fuel charts"""
    charts = []
    
    if df.empty:
        return charts
    
    # Thermal Paper Usage
    thermal_data = df.groupby("station").agg({
        "thermal_in": "sum",
        "thermal_out": "sum"
    }).reset_index()
    
    fig1 = px.bar(thermal_data, 
                  x="station", 
                  y=["thermal_in", "thermal_out"],
                  title="Thermal Paper Usage by Station (Entry vs Exit)",
                  barmode="group",
                  color_discrete_sequence=["#667eea", "#f093fb"])
    fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig1)
    
    # Fuel Consumption
    fuel_data = df.groupby("station").agg({
        "gen_fuel": "sum",
        "veh_fuel": "sum"
    }).reset_index()
    
    fig2 = px.bar(fuel_data, 
                  x="station", 
                  y=["gen_fuel", "veh_fuel"],
                  title="Fuel Consumption by Station (Generator vs Vehicle)",
                  barmode="group",
                  color_discrete_sequence=["#FF6B6B", "#4CAF50"])
    fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=400)
    charts.append(fig2)
    
    return charts

def create_sunburst_chart(df):
    """Create sunburst chart for hierarchical data"""
    if df.empty:
        return None
    
    # Prepare data for sunburst
    sunburst_data = df.groupby(["station", "shift"]).agg({
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum"
    }).reset_index()
    
    sunburst_data["Total Traffic"] = sunburst_data["exit_sys"] + sunburst_data["entry_sys"] + sunburst_data["exit_etc"] + sunburst_data["entry_etc"]
    sunburst_data["Total Revenue"] = sunburst_data["cash_sys"] + sunburst_data["cash_man"] + sunburst_data["etc"]
    
    if sunburst_data["Total Traffic"].sum() > 0:
        fig = px.sunburst(sunburst_data, 
                          path=["station", "shift"], 
                          values="Total Traffic",
                          title="Traffic Distribution: Station → Shift Hierarchy",
                          color="station",
                          color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=500)
        return fig
    return None

def create_scatter_chart(df):
    """Create scatter plot for traffic vs revenue correlation"""
    if df.empty:
        return None
    
    scatter_data = df.groupby(["station", "report_date"]).agg({
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum"
    }).reset_index()
    
    scatter_data["Total Traffic"] = scatter_data["exit_sys"] + scatter_data["entry_sys"] + scatter_data["exit_etc"] + scatter_data["entry_etc"]
    scatter_data["Total Revenue"] = scatter_data["cash_sys"] + scatter_data["cash_man"] + scatter_data["etc"]
    
    if scatter_data["Total Traffic"].sum() > 0 and scatter_data["Total Revenue"].sum() > 0:
        fig = px.scatter(scatter_data, 
                         x="Total Traffic", 
                         y="Total Revenue",
                         color="station",
                         size="Total Revenue",
                         title="Traffic vs Revenue Correlation by Station",
                         color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=500)
        return fig
    return None

# -------------------- DASHBOARD --------------------
def dashboard():
    is_manager = st.session_state.role == "manager"
    
    if is_manager:
        st.markdown("""
        <div class="manager-header">
            <h1 style="margin: 0;">📊 Manager Dashboard</h1>
            <p style="margin: 0.5rem 0 0 0;">Welcome, {}! Here's your comprehensive overview of all stations</p>
        </div>
        """.format(st.session_state.username), unsafe_allow_html=True)
        
        # Filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            filter_shift = st.selectbox("Filter by Shift", ["All", "A", "B", "C"], key="dash_shift")
        with col_filter2:
            filter_start = st.date_input("Start Date", value=date.today().replace(day=1), key="dash_start")
        with col_filter3:
            filter_end = st.date_input("End Date", value=date.today(), key="dash_end")
        
        shift_param = None if filter_shift == "All" else filter_shift
        
        # Get data
        df = get_reports(
            shift=shift_param,
            start_date=filter_start.strftime("%Y-%m-%d") if filter_start else None,
            end_date=filter_end.strftime("%Y-%m-%d") if filter_end else None
        )
        
        stats_df = get_station_stats(
            shift=shift_param,
            start_date=filter_start.strftime("%Y-%m-%d") if filter_start else None,
            end_date=filter_end.strftime("%Y-%m-%d") if filter_end else None
        )
        
        # Metrics
        total_reports = int(stats_df["total_reports"].sum()) if not stats_df.empty and not pd.isna(stats_df["total_reports"].sum()) else 0
        total_traffic = float(stats_df["total_traffic"].sum()) if not stats_df.empty and not pd.isna(stats_df["total_traffic"].sum()) else 0
        total_revenue = float(stats_df["total_revenue"].sum()) if not stats_df.empty and not pd.isna(stats_df["total_revenue"].sum()) else 0
        total_fuel = float(stats_df["total_fuel"].sum()) if not stats_df.empty and not pd.isna(stats_df["total_fuel"].sum()) else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f5576c;">
                <h3 style="color: #f5576c; margin: 0;">📋</h3>
                <h2 style="margin: 0.2rem 0;">{total_reports}</h2>
                <p style="color: #666; margin: 0;">Total Reports</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f093fb;">
                <h3 style="color: #f093fb; margin: 0;">🚗</h3>
                <h2 style="margin: 0.2rem 0;">{int(total_traffic):,}</h2>
                <p style="color: #666; margin: 0;">Total Traffic</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #4CAF50;">
                <h3 style="color: #4CAF50; margin: 0;">💰</h3>
                <h2 style="margin: 0.2rem 0;">Br {total_revenue:,.2f}</h2>
                <p style="color: #666; margin: 0;">Total Collection</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #FF6B6B;">
                <h3 style="color: #FF6B6B; margin: 0;">⛽</h3>
                <h2 style="margin: 0.2rem 0;">{total_fuel:.1f} L</h2>
                <p style="color: #666; margin: 0;">Total Fuel Used</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        if not df.empty:
            # Row 1: Traffic Analysis
            st.subheader("📊 Traffic Analysis")
            col1, col2 = st.columns(2)
            
            traffic_charts = create_traffic_charts(df)
            if len(traffic_charts) >= 2:
                with col1:
                    st.plotly_chart(traffic_charts[0], use_container_width=True)
                with col2:
                    st.plotly_chart(traffic_charts[1], use_container_width=True)
            
            # Row 2: Revenue Analysis
            st.subheader("💰 Revenue Analysis")
            col3, col4 = st.columns(2)
            
            revenue_charts = create_revenue_charts(df)
            if len(revenue_charts) >= 2:
                with col3:
                    st.plotly_chart(revenue_charts[0], use_container_width=True)
                with col4:
                    st.plotly_chart(revenue_charts[1], use_container_width=True)
            
            # Row 3: Shift Analysis
            st.subheader("🕐 Shift Analysis")
            col5, col6 = st.columns(2)
            
            shift_charts = create_shift_charts(df)
            if len(shift_charts) >= 2:
                with col5:
                    st.plotly_chart(shift_charts[0], use_container_width=True)
                with col6:
                    st.plotly_chart(shift_charts[1], use_container_width=True)
            
            # Row 4: Sunburst and Scatter
            st.subheader("📊 Advanced Analytics")
            col7, col8 = st.columns(2)
            
            sunburst = create_sunburst_chart(df)
            scatter = create_scatter_chart(df)
            
            if sunburst:
                with col7:
                    st.plotly_chart(sunburst, use_container_width=True)
            if scatter:
                with col8:
                    st.plotly_chart(scatter, use_container_width=True)
            
            # Row 5: Trends
            st.subheader("📈 Trends Over Time")
            trend_charts = create_trend_charts(df)
            if trend_charts:
                for chart in trend_charts:
                    st.plotly_chart(chart, use_container_width=True)
            
            # Row 6: Anomalies and Issues
            st.subheader("⚠️ Anomalies & Issues")
            col9, col10 = st.columns(2)
            
            anomaly_charts = create_anomaly_charts(df)
            if len(anomaly_charts) >= 2:
                with col9:
                    st.plotly_chart(anomaly_charts[0], use_container_width=True)
                with col10:
                    st.plotly_chart(anomaly_charts[1], use_container_width=True)
            elif len(anomaly_charts) == 1:
                st.plotly_chart(anomaly_charts[0], use_container_width=True)
            
            # Row 7: Thermal and Fuel
            st.subheader("🧾 Thermal & Fuel Analysis")
            col11, col12 = st.columns(2)
            
            thermal_fuel_charts = create_thermal_fuel_charts(df)
            if len(thermal_fuel_charts) >= 2:
                with col11:
                    st.plotly_chart(thermal_fuel_charts[0], use_container_width=True)
                with col12:
                    st.plotly_chart(thermal_fuel_charts[1], use_container_width=True)
            elif len(thermal_fuel_charts) == 1:
                st.plotly_chart(thermal_fuel_charts[0], use_container_width=True)
            
            # Issues Summary
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            st.subheader("📋 Issues & Incidents Summary")
            
            issues_data = df[df["problems"].notna() & (df["problems"] != "")]
            if not issues_data.empty:
                st.warning(f"⚠️ {len(issues_data)} issues reported")
                st.dataframe(issues_data[["report_date", "shift", "station", "supervisor", "problems"]], use_container_width=True)
            else:
                st.success("✅ No issues reported. All stations operating smoothly!")
            
        else:
            st.info("📭 No reports submitted yet. Start by submitting your first report!")
    
    else:
        # Supervisor Dashboard (simplified)
        st.markdown("""
        <div class="main-header">
            <h1 style="margin: 0;">📊 Dashboard</h1>
            <p style="margin: 0.5rem 0 0 0;">Welcome back, {}! Here's your station overview</p>
        </div>
        """.format(st.session_state.username), unsafe_allow_html=True)
        
        stats_df = get_station_stats(station=st.session_state.station)
        
        if not stats_df.empty:
            total_reports = int(stats_df["total_reports"].iloc[0]) if not pd.isna(stats_df["total_reports"].iloc[0]) else 0
            total_traffic = float(stats_df["total_traffic"].iloc[0]) if not pd.isna(stats_df["total_traffic"].iloc[0]) else 0
            total_revenue = float(stats_df["total_revenue"].iloc[0]) if not pd.isna(stats_df["total_revenue"].iloc[0]) else 0
            total_fuel = float(stats_df["total_fuel"].iloc[0]) if not pd.isna(stats_df["total_fuel"].iloc[0]) else 0
        else:
            total_reports = 0
            total_traffic = 0
            total_revenue = 0
            total_fuel = 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="color: #667eea; margin: 0;">📋</h3>
                <h2 style="margin: 0.2rem 0;">{total_reports}</h2>
                <p style="color: #666; margin: 0;">Total Reports</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f093fb;">
                <h3 style="color: #f093fb; margin: 0;">🚗</h3>
                <h2 style="margin: 0.2rem 0;">{int(total_traffic):,}</h2>
                <p style="color: #666; margin: 0;">Total Traffic</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #4CAF50;">
                <h3 style="color: #4CAF50; margin: 0;">💰</h3>
                <h2 style="margin: 0.2rem 0;">Br {total_revenue:,.2f}</h2>
                <p style="color: #666; margin: 0;">Total Collection</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #FF6B6B;">
                <h3 style="color: #FF6B6B; margin: 0;">⛽</h3>
                <h2 style="margin: 0.2rem 0;">{total_fuel:.1f} L</h2>
                <p style="color: #666; margin: 0;">Total Fuel Used</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
        
        # Show recent reports for supervisor
        try:
            recent_reports = get_reports(station=st.session_state.station).head(10)
            if not recent_reports.empty:
                st.subheader("📋 Recent Reports")
                display_cols = []
                for col in ["report_date", "shift", "exit_sys", "entry_sys", "exit_etc", "entry_etc", "cash_sys", "etc"]:
                    if col in recent_reports.columns:
                        display_cols.append(col)
                st.dataframe(recent_reports[display_cols], use_container_width=True)
            else:
                st.info("📭 No reports submitted yet. Click 'Submit Report' to get started!")
        except:
            st.info("📭 No reports submitted yet. Click 'Submit Report' to get started!")

# -------------------- REPORT FORM --------------------
def submit_report():
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0;">📝 Submit Shift Report</h1>
        <p style="margin: 0.5rem 0 0 0;">Station: {}</p>
    </div>
    """.format(st.session_state.station), unsafe_allow_html=True)
    
    with st.form(key="shift_report_form", clear_on_submit=False):
        st.markdown("### 📅 Date & Shift Information")
        st.info("ℹ️ Each station can have only ONE report per day per shift (A, B, C)")
        
        col_date, col_shift = st.columns(2)
        with col_date:
            report_date = st.date_input("Report Date", value=date.today(), key="report_date")
        with col_shift:
            shift = st.selectbox(
                "Shift", 
                ["A", "B", "C"],
                help="A: Morning (6AM-2PM), B: Afternoon (2PM-10PM), C: Night (10PM-6AM)",
                key="shift"
            )
        
        # Check if report already exists for this date, shift, and station
        exists = check_shift_exists(report_date.strftime("%Y-%m-%d"), shift, st.session_state.station)
        if exists:
            st.markdown(f"""
            <div class="duplicate-warning">
                ⚠️ <strong>Report already exists!</strong><br>
                A report already exists for <strong>{st.session_state.station}</strong> on 
                <strong>{report_date.strftime('%Y-%m-%d')}</strong> - Shift <strong>{shift}</strong>.<br>
                Submitting this form will <strong>UPDATE</strong> the existing report.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.success(f"✅ No existing report found for {st.session_state.station} on {report_date.strftime('%Y-%m-%d')} - Shift {shift}")
        
        st.markdown("### 1️⃣ Exit & Entry Traffic Volume")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Exit**")
            exit_sys = st.number_input("System", min_value=0, step=1, key="exit_sys")
            exit_etc = st.number_input("ETC", min_value=0, step=1, key="exit_etc")
        with col2:
            st.markdown("**Entry**")
            entry_sys = st.number_input("System", min_value=0, step=1, key="entry_sys")
            entry_etc = st.number_input("ETC", min_value=0, step=1, key="entry_etc")
        
        col1b, col2b = st.columns(2)
        with col1b:
            exit_man = st.number_input("Exit (Manual)", min_value=0, step=1, key="exit_man")
        with col2b:
            entry_man = st.number_input("Entry (Manual)", min_value=0, step=1, key="entry_man")
        
        st.markdown("### 2️⃣ Exit Cash Collection")
        col3, col4 = st.columns(2)
        with col3:
            cash_sys = st.number_input("Cash (System)", min_value=0.0, step=0.01, key="cash_sys")
            etc = st.number_input("ETC Collection", min_value=0.0, step=0.01, key="etc")
        with col4:
            cash_man = st.number_input("Cash (Manual)", min_value=0.0, step=0.01, key="cash_man")
        
        col5, col6 = st.columns(2)
        with col5:
            st.markdown("### 3️⃣ Entrance Thermal Paper")
            thermal_in = st.number_input("Rolls used", min_value=0, step=1, key="thermal_in")
            
            st.markdown("### 5️⃣ Generator Fuel")
            gen_fuel = st.number_input("Fuel Taken (Liters)", min_value=0.0, step=0.1, key="gen_fuel")
            
            st.markdown("### 7️⃣ No Card Vehicles")
            no_card = st.number_input("Number of vehicles", min_value=0, step=1, key="no_card")
            
            st.markdown("### 8️⃣ Forged Tickets (ተጭበረበረ ትኬት)")
            forged_count = st.number_input("Count", min_value=0, step=1, value=0, key="forged_count")
            forged_amt = st.number_input("Amount (Birr)", min_value=0.0, step=0.01, value=0.0, key="forged_amt")
            
            st.markdown("### 🔟 Generator Hour")
            gen_hour = st.number_input("Meter Reading", min_value=0.0, step=0.1, key="gen_hour")
        
        with col6:
            st.markdown("### 4️⃣ Exit Thermal Paper")
            thermal_out = st.number_input("Rolls used", min_value=0, step=1, key="thermal_out")
            
            st.markdown("### 6️⃣ Vehicle Fuel")
            veh_fuel = st.number_input("Fuel Taken (Liters)", min_value=0.0, step=0.1, key="veh_fuel")
            
            st.markdown("### 9️⃣ Overloaded Vehicles (ትርፍ ጭነት)")
            overload_count = st.number_input("Count", min_value=0, step=1, value=0, key="overload_count")
            overload_amt = st.number_input("Amount (Birr)", min_value=0.0, step=0.01, value=0.0, key="overload_amt")
        
        st.markdown("### 1️⃣1️⃣ Good Things / Positive Observations")
        good_notes = st.text_area("What went well during the shift?", key="good_notes", height=100)
        
        st.markdown("### 1️⃣2️⃣ Problems Encountered")
        problems = st.text_area("Issues, incidents, or equipment failures", key="problems", height=100)
        
        submitted = st.form_submit_button("✅ Submit Report", use_container_width=True)
        
        if submitted:
            record = {
                "report_date": report_date.strftime("%Y-%m-%d"),
                "shift": shift,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "supervisor": st.session_state.username,
                "station": st.session_state.station,
                "exit_sys": exit_sys,
                "entry_sys": entry_sys,
                "exit_man": exit_man,
                "entry_man": entry_man,
                "exit_etc": exit_etc,
                "entry_etc": entry_etc,
                "cash_sys": cash_sys,
                "cash_man": cash_man,
                "etc": etc,
                "thermal_in": thermal_in,
                "thermal_out": thermal_out,
                "gen_fuel": gen_fuel,
                "veh_fuel": veh_fuel,
                "no_card": no_card,
                "forged_count": forged_count,
                "forged_amt": forged_amt,
                "overload_count": overload_count,
                "overload_amt": overload_amt,
                "gen_hour": gen_hour,
                "good_notes": good_notes,
                "problems": problems,
            }
            
            result = save_report(record)
            
            if result == "inserted":
                st.success(f"✅ Report submitted successfully for {report_date.strftime('%Y-%m-%d')} - Shift {shift}! 🎉")
                st.balloons()
            elif result == "updated":
                st.success(f"✅ Report updated successfully for {report_date.strftime('%Y-%m-%d')} - Shift {shift}! 🔄")
            elif result == "duplicate":
                st.error("❌ Duplicate report detected! Please check your entries.")

# -------------------- REPORTS VIEW --------------------
def view_reports():
    is_manager = st.session_state.role == "manager"
    
    if is_manager:
        st.markdown("""
        <div class="manager-header">
            <h1 style="margin: 0;">📈 Reports - All Stations</h1>
            <p style="margin: 0.5rem 0 0 0;">View and analyze reports from all stations</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_station = st.selectbox("Station", ["All"] + STATIONS, key="filter_station")
        with col2:
            filter_shift = st.selectbox("Shift", ["All", "A", "B", "C"], key="filter_shift")
        with col3:
            filter_start = st.date_input("Start Date", value=date.today().replace(day=1), key="filter_start")
        with col4:
            filter_end = st.date_input("End Date", value=date.today(), key="filter_end")
        
        station_param = None if filter_station == "All" else filter_station
        shift_param = None if filter_shift == "All" else filter_shift
        
        df = get_reports(
            station=station_param,
            shift=shift_param,
            start_date=filter_start.strftime("%Y-%m-%d") if filter_start else None,
            end_date=filter_end.strftime("%Y-%m-%d") if filter_end else None
        )
        
        tab1, tab2, tab3 = st.tabs(["📊 Summary", "📋 All Reports", "🗑️ Delete Duplicates"])
        
        with tab1:
            st.subheader("📊 Station Performance Summary")
            if not df.empty:
                stats_df = df.groupby("station").agg({
                    "supervisor": "count",
                    "exit_sys": "sum",
                    "entry_sys": "sum",
                    "exit_etc": "sum",
                    "entry_etc": "sum",
                    "cash_sys": "sum",
                    "cash_man": "sum",
                    "etc": "sum"
                }).reset_index()
                stats_df["Total Traffic"] = stats_df["exit_sys"] + stats_df["entry_sys"] + stats_df["exit_etc"] + stats_df["entry_etc"]
                stats_df["Total Revenue"] = stats_df["cash_sys"] + stats_df["cash_man"] + stats_df["etc"]
                st.dataframe(stats_df, use_container_width=True)
                
                st.download_button(
                    "📥 Download Summary Report",
                    stats_df.to_csv(index=False),
                    "station_summary.csv",
                    key="download_summary"
                )
            else:
                st.info("No data available for the selected filters")
        
        with tab2:
            st.subheader("📋 All Reports")
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                
                st.download_button(
                    "📥 Download All Reports",
                    df.to_csv(index=False),
                    "all_reports.csv",
                    key="download_all"
                )
            else:
                st.info("No reports found for the selected filters")
        
        with tab3:
            st.subheader("🗑️ Delete Duplicate Reports")
            st.warning("⚠️ This tool helps you find and remove duplicate reports.")
            st.info("ℹ️ Each station should have only ONE report per day per shift (A, B, C).")
            
            col_del1, col_del2, col_del3 = st.columns(3)
            with col_del1:
                del_station = st.selectbox("Select Station", STATIONS, key="del_station")
            with col_del2:
                del_date = st.date_input("Select Date", value=date.today(), key="del_date")
            with col_del3:
                del_shift = st.selectbox("Select Shift", ["A", "B", "C"], key="del_shift")
            
            # Check for duplicates
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, supervisor, timestamp FROM reports 
                WHERE station = ? AND report_date = ? AND shift = ?
                ORDER BY id
            ''', (del_station, del_date.strftime("%Y-%m-%d"), del_shift))
            rows = cursor.fetchall()
            conn.close()
            
            if len(rows) > 1:
                st.warning(f"⚠️ Found {len(rows)} duplicate reports for {del_station} on {del_date.strftime('%Y-%m-%d')} - Shift {del_shift}")
                
                # Show duplicates
                dup_data = []
                for i, row in enumerate(rows):
                    dup_data.append({
                        "Index": i + 1,
                        "Report ID": row[0],
                        "Supervisor": row[1],
                        "Timestamp": row[2],
                        "Action": "Keep" if i == 0 else "Delete"
                    })
                dup_df = pd.DataFrame(dup_data)
                st.dataframe(dup_df, use_container_width=True)
                
                st.info("💡 The first report (Index 1) will be kept. All others will be deleted.")
                
                if st.button("🗑️ Delete Duplicates", key="delete_duplicates_btn"):
                    deleted = delete_duplicate_reports(del_station, del_date.strftime("%Y-%m-%d"), del_shift)
                    if deleted > 0:
                        st.success(f"✅ Successfully deleted {deleted} duplicate report(s)!")
                        st.rerun()
                    else:
                        st.info("No duplicates found to delete.")
            else:
                st.success(f"✅ No duplicates found for {del_station} on {del_date.strftime('%Y-%m-%d')} - Shift {del_shift}")
    
    else:
        st.markdown("""
        <div class="main-header">
            <h1 style="margin: 0;">📈 My Reports</h1>
            <p style="margin: 0.5rem 0 0 0;">View and analyze your shift reports</p>
        </div>
        """, unsafe_allow_html=True)
        
        df = get_reports(station=st.session_state.station)
        
        if not df.empty:
            st.subheader(f"📋 Reports for {st.session_state.station}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Reports", len(df), delta=None)
            with col2:
                total_traffic = df["exit_sys"].sum() + df["entry_sys"].sum() + df["exit_etc"].sum() + df["entry_etc"].sum()
                st.metric("Total Traffic", f"{int(total_traffic):,}", delta=None)
            with col3:
                total_cash = df["cash_sys"].sum() + df["cash_man"].sum() + df["etc"].sum()
                st.metric("Total Collection", f"Br {total_cash:,.2f}", delta=None)
            
            st.dataframe(df, use_container_width=True)
            
            st.download_button(
                "📥 Download My Reports",
                df.to_csv(index=False),
                f"{st.session_state.station}_reports.csv",
                key="download_station"
            )
        else:
            st.info(f"No reports found for {st.session_state.station}")

# -------------------- ANALYTICS (Manager Only) --------------------
def analytics():
    st.markdown("""
    <div class="manager-header">
        <h1 style="margin: 0;">📊 Advanced Analytics</h1>
        <p style="margin: 0.5rem 0 0 0;">Comprehensive analysis of all station performance</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_shift = st.selectbox("Shift", ["All", "A", "B", "C"], key="ana_shift")
    with col2:
        filter_start = st.date_input("Start Date", value=date.today().replace(day=1), key="ana_start")
    with col3:
        filter_end = st.date_input("End Date", value=date.today(), key="ana_end")
    with col4:
        filter_station = st.selectbox("Station", ["All"] + STATIONS, key="ana_station")
    
    shift_param = None if filter_shift == "All" else filter_shift
    station_param = None if filter_station == "All" else filter_station
    
    df = get_reports(
        station=station_param,
        shift=shift_param,
        start_date=filter_start.strftime("%Y-%m-%d") if filter_start else None,
        end_date=filter_end.strftime("%Y-%m-%d") if filter_end else None
    )
    
    if df.empty:
        st.info("📭 No data available for analytics.")
        return
    
    # KPI Cards
    st.subheader("📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_reports = len(df)
        st.markdown(f"""
        <div class="manager-stats">
            <h2>{total_reports}</h2>
            <p>📋 Total Reports</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_vehicles = int(df["exit_sys"].sum() + df["entry_sys"].sum() + df["exit_etc"].sum() + df["entry_etc"].sum())
        st.markdown(f"""
        <div class="manager-stats">
            <h2>{total_vehicles:,}</h2>
            <p>🚗 Total Vehicles</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_revenue = df["cash_sys"].sum() + df["cash_man"].sum() + df["etc"].sum()
        st.markdown(f"""
        <div class="manager-stats">
            <h2>Br {total_revenue:,.0f}</h2>
            <p>💰 Total Revenue</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_per_report = total_revenue / total_reports if total_reports > 0 else 0
        st.markdown(f"""
        <div class="manager-stats">
            <h2>Br {avg_per_report:,.0f}</h2>
            <p>📈 Avg Revenue/Report</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # All charts in tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Traffic", "💰 Revenue", "🕐 Shifts", "📈 Trends", "⚠️ Issues"])
    
    with tab1:
        traffic_charts = create_traffic_charts(df)
        for chart in traffic_charts:
            st.plotly_chart(chart, use_container_width=True)
    
    with tab2:
        revenue_charts = create_revenue_charts(df)
        for chart in revenue_charts:
            st.plotly_chart(chart, use_container_width=True)
    
    with tab3:
        shift_charts = create_shift_charts(df)
        for chart in shift_charts:
            st.plotly_chart(chart, use_container_width=True)
        # Add sunburst
        sunburst = create_sunburst_chart(df)
        if sunburst:
            st.plotly_chart(sunburst, use_container_width=True)
    
    with tab4:
        trend_charts = create_trend_charts(df)
        for chart in trend_charts:
            st.plotly_chart(chart, use_container_width=True)
        # Add scatter
        scatter = create_scatter_chart(df)
        if scatter:
            st.plotly_chart(scatter, use_container_width=True)
    
    with tab5:
        anomaly_charts = create_anomaly_charts(df)
        for chart in anomaly_charts:
            st.plotly_chart(chart, use_container_width=True)
        thermal_fuel_charts = create_thermal_fuel_charts(df)
        for chart in thermal_fuel_charts:
            st.plotly_chart(chart, use_container_width=True)

# -------------------- CONSOLIDATED REPORT (Manager Only) --------------------
def consolidated_report():
    st.markdown("""
    <div class="manager-header">
        <h1 style="margin: 0;">📋 Consolidated Report</h1>
        <p style="margin: 0.5rem 0 0 0;">Complete summary of all station operations</p>
        <p style="margin: 0.2rem 0 0 0; opacity: 0.9;">Modjo East • Koka • Bote • Meki • Batu</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_start = st.date_input("Start Date", value=date.today().replace(day=1), key="cons_start")
    with col2:
        filter_end = st.date_input("End Date", value=date.today(), key="cons_end")
    with col3:
        filter_shift = st.selectbox("Shift", ["All", "A", "B", "C"], key="cons_shift")
    
    shift_param = None if filter_shift == "All" else filter_shift
    
    df = get_reports(
        shift=shift_param,
        start_date=filter_start.strftime("%Y-%m-%d") if filter_start else None,
        end_date=filter_end.strftime("%Y-%m-%d") if filter_end else None
    )
    
    if df.empty:
        st.info("📭 No data available for consolidated report.")
        return
    
    # Overall summary
    st.subheader("🏢 Overall Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Reports", len(df), delta=None)
    with col2:
        total_traffic = int(df["exit_sys"].sum() + df["entry_sys"].sum() + df["exit_etc"].sum() + df["entry_etc"].sum())
        st.metric("Total Traffic", f"{total_traffic:,}", delta=None)
    with col3:
        total_revenue = df["cash_sys"].sum() + df["cash_man"].sum() + df["etc"].sum()
        st.metric("Total Revenue", f"Br {total_revenue:,.2f}", delta=None)
    with col4:
        total_fuel = df["gen_fuel"].sum() + df["veh_fuel"].sum()
        st.metric("Total Fuel", f"{total_fuel:.1f} L", delta=None)
    with col5:
        unique_stations = df["station"].nunique()
        st.metric("Active Stations", unique_stations, delta=None)
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Shift-wise breakdown
    if 'shift' in df.columns:
        st.subheader("🕐 Shift-wise Breakdown")
        shift_summary = df.groupby("shift").agg({
            "station": "count",
            "exit_sys": "sum",
            "entry_sys": "sum",
            "exit_etc": "sum",
            "entry_etc": "sum",
            "cash_sys": "sum",
            "cash_man": "sum",
            "etc": "sum"
        }).reset_index()
        shift_summary["Total Traffic"] = shift_summary["exit_sys"] + shift_summary["entry_sys"] + shift_summary["exit_etc"] + shift_summary["entry_etc"]
        shift_summary["Total Revenue"] = shift_summary["cash_sys"] + shift_summary["cash_man"] + shift_summary["etc"]
        st.dataframe(shift_summary, use_container_width=True)
        st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Station-wise breakdown
    st.subheader("🏪 Station-wise Breakdown")
    
    station_summary = df.groupby("station").agg({
        "supervisor": "count",
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_man": "sum",
        "entry_man": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum",
        "gen_fuel": "sum",
        "veh_fuel": "sum",
        "no_card": "sum",
        "forged_count": "sum",
        "overload_count": "sum",
        "thermal_in": "sum",
        "thermal_out": "sum"
    }).reset_index()
    
    station_summary["Total Traffic"] = station_summary["exit_sys"] + station_summary["entry_sys"] + station_summary["exit_etc"] + station_summary["entry_etc"]
    station_summary["Total Manual Traffic"] = station_summary["exit_man"] + station_summary["entry_man"]
    station_summary["Total Collection"] = station_summary["cash_sys"] + station_summary["cash_man"] + station_summary["etc"]
    station_summary["Total Fuel"] = station_summary["gen_fuel"] + station_summary["veh_fuel"]
    
    display_cols = ["station", "Total Traffic", "Total Manual Traffic", "Total Collection", "Total Fuel", "no_card", "thermal_in", "thermal_out"]
    display_df = station_summary[display_cols]
    display_df.columns = ["Station", "Traffic (Sys)", "Traffic (Man)", "Revenue", "Fuel (L)", "No Card", "Thermal In", "Thermal Out"]
    
    st.dataframe(display_df, use_container_width=True)
    
    st.download_button(
        "📥 Download Consolidated Report",
        station_summary.to_csv(index=False),
        "consolidated_report.csv",
        key="download_consolidated",
        use_container_width=True
    )
    
    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
    
    # Issues summary
    st.subheader("⚠️ Issues & Incidents Summary")
    
    issues_data = df[df["problems"].notna() & (df["problems"] != "")][["report_date", "shift", "station", "supervisor", "problems"]]
    if not issues_data.empty:
        st.warning(f"⚠️ {len(issues_data)} issues reported")
        st.dataframe(issues_data, use_container_width=True)
    else:
        st.success("✅ No issues reported. All stations operating smoothly!")

# -------------------- USER MANAGEMENT (Manager Only) --------------------
def user_management():
    st.markdown("""
    <div class="manager-header">
        <h1 style="margin: 0;">👥 User Management</h1>
        <p style="margin: 0.5rem 0 0 0;">Manage all system users</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 All Users", "➕ Add New User"])
    
    with tab1:
        users_df = get_all_users()
        if not users_df.empty:
            st.dataframe(users_df, use_container_width=True)
            
            # Option to reset password
            st.subheader("🔑 Reset User Password")
            col1, col2 = st.columns(2)
            with col1:
                selected_user = st.selectbox("Select User", users_df["username"].tolist())
            with col2:
                new_password = st.text_input("New Password", type="password")
                if st.button("Reset Password", key="reset_pass_btn"):
                    if new_password and len(new_password) >= 4:
                        update_password(selected_user, new_password)
                        st.success(f"✅ Password reset for {selected_user}")
                    else:
                        st.error("Password must be at least 4 characters")
        else:
            st.info("No users found")
    
    with tab2:
        st.subheader("➕ Add New User")
        st.info("📝 Create supervisor or manager accounts manually")
        with st.form(key="add_user_form"):
            new_username = st.text_input("Username", placeholder="Enter username (e.g., modjoeast1)")
            new_password = st.text_input("Password", type="password", placeholder="Enter password")
            new_station = st.selectbox("Station", STATIONS)
            new_role = st.selectbox("Role", ["supervisor", "manager"])
            
            if st.form_submit_button("Add User", use_container_width=True):
                if new_username and new_password:
                    existing_user = get_user(new_username)
                    if existing_user:
                        st.error("❌ Username already exists! Please choose a different username.")
                    elif len(new_password) < 4:
                        st.error("❌ Password must be at least 4 characters")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        try:
                            cursor.execute('''
                                INSERT INTO users (username, password_hash, station, role)
                                VALUES (?, ?, ?, ?)
                            ''', (new_username, hash_password(new_password), new_station, new_role))
                            conn.commit()
                            st.success(f"✅ User '{new_username}' created successfully!")
                            st.info(f"📋 Username: {new_username} | Password: {new_password} | Station: {new_station} | Role: {new_role}")
                        except sqlite3.IntegrityError:
                            st.error("❌ Username already exists!")
                        finally:
                            conn.close()
                else:
                    st.error("❌ Username and password are required")

# -------------------- SIDEBAR --------------------
def sidebar():
    with st.sidebar:
        is_manager = st.session_state.role == "manager"
        
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: white; margin: 0;">🚦 Toll Ops</h2>
            <p style="color: #aaa; margin: 0.2rem 0;">Shift Report System</p>
            <hr style="border-color: #555;">
            <p style="color: white; font-size: 0.9rem;">👤 {}</p>
            <p style="color: #aaa; font-size: 0.8rem;">📍 {}</p>
            <p><span class="badge {}">{}</span></p>
        </div>
        """.format(
            st.session_state.username,
            st.session_state.station,
            "badge-manager" if is_manager else "badge-supervisor",
            "👑 Manager" if is_manager else "🛡️ Supervisor"
        ), unsafe_allow_html=True)
        
        change_password()
        
        st.markdown("---")
        if st.button("🚪 Logout", key="logout_btn", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.station = ""
            st.session_state.role = ""
            st.session_state.page = "Dashboard"
            st.rerun()

# -------------------- MAIN APP --------------------
def main():
    if not st.session_state.logged_in:
        login()
    else:
        sidebar()
        top_menu()
        
        is_manager = st.session_state.role == "manager"
        
        if st.session_state.page == "Dashboard":
            dashboard()
        elif st.session_state.page == "Submit Report" and not is_manager:
            submit_report()
        elif st.session_state.page == "Reports":
            view_reports()
        elif st.session_state.page == "Analytics" and is_manager:
            analytics()
        elif st.session_state.page == "Consolidated" and is_manager:
            consolidated_report()
        elif st.session_state.page == "Users" and is_manager:
            user_management()
        else:
            dashboard()
        
        st.markdown("""
        <div class="footer">
            © 2026 Toll Operations Manager | Built with ❤️ using Streamlit
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()