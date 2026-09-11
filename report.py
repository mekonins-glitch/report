"""
Toll Operations Manager - Complete Application
Single File: toll_operations.py
"""

import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import plotly.express as px
import os
import base64
from PIL import Image
import io

# -------------------- PAGE CONFIG --------------------
st.set_page_config(
    page_title="🚦Modjo-Hawassa Toll Operations",
    page_icon="🚦",
    layout="wide"
)

# -------------------- SIMPLE CSS --------------------
st.markdown("""
<style>
    .stApp {
        background: #f5f7fa;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .manager-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .stButton > button {
        background: #667eea;
        color: white;
        border: none;
        border-radius: 20px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background: #764ba2;
    }
    .stForm {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-left: 4px solid #667eea;
        text-align: center;
    }
    .footer {
        text-align: center;
        padding: 1rem;
        color: #999;
        font-size: 0.8rem;
        border-top: 1px solid #ddd;
        margin-top: 2rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 15px;
        font-size: 0.7rem;
        font-weight: bold;
    }
    .badge-manager {
        background: #f5576c;
        color: white;
    }
    .badge-supervisor {
        background: #667eea;
        color: white;
    }
    .settled-box {
        background: #fff3cd;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        text-align: center;
    }
    .settled-box h3 {
        color: #856404;
        margin: 0;
    }
    .settled-box p {
        color: #856404;
        margin: 0.5rem 0 0 0;
    }
</style>
""", unsafe_allow_html=True)

# -------------------- CONSTANTS --------------------
STATIONS = ["Modjo East", "Koka", "Bote", "Meki", "Batu"]
SHIFTS = ["A", "B", "C"]
VEHICLE_TYPES = ["V1", "V2", "V3", "V4", "V5", "V6", "V7"]

# -------------------- DATABASE --------------------
DB_FILE = "toll_operations.db"

def init_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
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
            solution TEXT,
            is_settled INTEGER DEFAULT 0,
            settled_at TIMESTAMP,
            settled_by TEXT,
            UNIQUE(station, report_date, shift)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unpaid_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_number TEXT NOT NULL,
            vehicle_type TEXT,
            station TEXT NOT NULL,
            report_date DATE NOT NULL,
            shift TEXT NOT NULL,
            supervisor TEXT NOT NULL,
            amount REAL DEFAULT 0,
            reason TEXT,
            status TEXT DEFAULT 'unpaid',
            paid_date DATE,
            image_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def migrate_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(reports)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_settled' not in columns:
        try:
            cursor.execute('ALTER TABLE reports ADD COLUMN is_settled INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass
    
    if 'settled_at' not in columns:
        try:
            cursor.execute('ALTER TABLE reports ADD COLUMN settled_at TIMESTAMP')
        except sqlite3.OperationalError:
            pass
    
    if 'settled_by' not in columns:
        try:
            cursor.execute('ALTER TABLE reports ADD COLUMN settled_by TEXT')
        except sqlite3.OperationalError:
            pass
    
    cursor.execute("PRAGMA table_info(unpaid_vehicles)")
    unpaid_cols = [column[1] for column in cursor.fetchall()]
    if 'image_data' not in unpaid_cols:
        try:
            cursor.execute('ALTER TABLE unpaid_vehicles ADD COLUMN image_data TEXT')
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_user():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO users (username, password_hash, station, role) VALUES (?, ?, ?, ?)',
                      ('admin', hash_password('admin123'), 'All Stations', 'manager'))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT username, password_hash, station, role FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"username": user[0], "password_hash": user[1], "station": user[2], "role": user[3]}
    return None

def update_password(username, new_password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hash_password(new_password), username))
    conn.commit()
    conn.close()

def save_report(record):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, is_settled FROM reports 
            WHERE station = ? AND report_date = ? AND shift = ?
        ''', (record['station'], record['report_date'], record['shift']))
        result = cursor.fetchone()
        
        if result:
            if result[1] == 1:
                conn.close()
                return "settled"
            
            cursor.execute('''
                UPDATE reports SET
                    timestamp = ?, supervisor = ?,
                    exit_sys = ?, entry_sys = ?, exit_man = ?, entry_man = ?,
                    exit_etc = ?, entry_etc = ?,
                    cash_sys = ?, cash_man = ?, etc = ?,
                    thermal_in = ?, thermal_out = ?,
                    gen_fuel = ?, veh_fuel = ?,
                    no_card = ?,
                    forged_count = ?, forged_amt = ?,
                    overload_count = ?, overload_amt = ?,
                    gen_hour = ?,
                    good_notes = ?, problems = ?, solution = ?
                WHERE station = ? AND report_date = ? AND shift = ?
            ''', (
                record['timestamp'], record['supervisor'],
                record['exit_sys'], record['entry_sys'], record['exit_man'], record['entry_man'],
                record['exit_etc'], record['entry_etc'],
                record['cash_sys'], record['cash_man'], record['etc'],
                record['thermal_in'], record['thermal_out'],
                record['gen_fuel'], record['veh_fuel'],
                record['no_card'],
                record['forged_count'], record['forged_amt'],
                record['overload_count'], record['overload_amt'],
                record['gen_hour'],
                record['good_notes'], record['problems'], record['solution'],
                record['station'], record['report_date'], record['shift']
            ))
            conn.commit()
            return "updated"
        else:
            cursor.execute('''
                INSERT INTO reports (
                    report_date, shift, timestamp, supervisor, station, 
                    exit_sys, entry_sys, exit_man, entry_man, exit_etc, entry_etc,
                    cash_sys, cash_man, etc, thermal_in, thermal_out, gen_fuel, veh_fuel,
                    no_card, forged_count, forged_amt, overload_count, overload_amt, gen_hour,
                    good_notes, problems, solution, is_settled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                record['good_notes'], record['problems'], record['solution'],
                0
            ))
            conn.commit()
            return "inserted"
    except Exception as e:
        return "error"
    finally:
        conn.close()

def settle_report(report_id, admin_username):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reports 
        SET is_settled = 1, settled_at = ?, settled_by = ?
        WHERE id = ?
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), admin_username, report_id))
    conn.commit()
    conn.close()
    return True

def unsettle_report(report_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reports 
        SET is_settled = 0, settled_at = NULL, settled_by = NULL
        WHERE id = ?
    ''', (report_id,))
    conn.commit()
    conn.close()
    return True

def get_report_status(report_date, shift, station):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*), COALESCE(MAX(is_settled), 0) FROM reports 
        WHERE report_date = ? AND shift = ? AND station = ?
    ''', (report_date, shift, station))
    result = cursor.fetchone()
    conn.close()
    exists = result[0] > 0
    is_settled = result[1] == 1 if exists else False
    return exists, is_settled

def get_reports(station=None, start_date=None, end_date=None, shift=None):
    conn = sqlite3.connect(DB_FILE)
    query = 'SELECT * FROM reports WHERE 1=1'
    params = []
    if station and station != "All Stations":
        query += ' AND station = ?'
        params.append(station)
    if shift:
        query += ' AND shift = ?'
        params.append(shift)
    if start_date:
        query += ' AND report_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND report_date <= ?'
        params.append(end_date)
    query += ' ORDER BY report_date DESC, shift ASC'
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query('SELECT username, station, role, created_at FROM users ORDER BY username', conn)
    conn.close()
    return df

def get_station_stats(station=None, start_date=None, end_date=None):
    conn = sqlite3.connect(DB_FILE)
    params = []
    where = "WHERE 1=1"
    if station:
        where += " AND station = ?"
        params.append(station)
    if start_date:
        where += " AND report_date >= ?"
        params.append(start_date)
    if end_date:
        where += " AND report_date <= ?"
        params.append(end_date)
    
    query = f'''
        SELECT 
            COUNT(*) as total_reports,
            COALESCE(SUM(exit_sys), 0) + COALESCE(SUM(entry_sys), 0) + COALESCE(SUM(exit_etc), 0) + COALESCE(SUM(entry_etc), 0) as total_traffic,
            COALESCE(SUM(cash_sys), 0) + COALESCE(SUM(cash_man), 0) + COALESCE(SUM(etc), 0) as total_revenue,
            COALESCE(SUM(gen_fuel), 0) + COALESCE(SUM(veh_fuel), 0) as total_fuel
        FROM reports {where}
    '''
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# -------------------- UNPAID VEHICLE FUNCTIONS --------------------
def add_unpaid_vehicle(vehicle_number, vehicle_type, station, report_date, shift, supervisor, amount, reason, image_data=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO unpaid_vehicles (vehicle_number, vehicle_type, station, report_date, shift, supervisor, amount, reason, status, image_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (vehicle_number, vehicle_type, station, report_date, shift, supervisor, amount, reason, 'unpaid', image_data))
    conn.commit()
    conn.close()
    return True

def get_unpaid_vehicles(station=None, start_date=None, end_date=None, status=None):
    conn = sqlite3.connect(DB_FILE)
    query = 'SELECT * FROM unpaid_vehicles WHERE 1=1'
    params = []
    if station:
        query += ' AND station = ?'
        params.append(station)
    if status and status != "All":
        query += ' AND status = ?'
        params.append(status)
    if start_date:
        query += ' AND report_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND report_date <= ?'
        params.append(end_date)
    query += ' ORDER BY report_date DESC, created_at DESC'
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_unpaid_vehicle_status(vehicle_id, status, paid_date=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if status == 'paid' and paid_date:
        cursor.execute('UPDATE unpaid_vehicles SET status = ?, paid_date = ? WHERE id = ?', (status, paid_date, vehicle_id))
    else:
        cursor.execute('UPDATE unpaid_vehicles SET status = ? WHERE id = ?', (status, vehicle_id))
    conn.commit()
    conn.close()
    return True

def delete_unpaid_vehicle(vehicle_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM unpaid_vehicles WHERE id = ?', (vehicle_id,))
    conn.commit()
    conn.close()
    return True

def process_image(uploaded_file):
    """
    Process uploaded image:
    1. Convert any mode (RGBA, P, LA, etc.) to RGB
    2. Resize to max 800x800
    3. Encode to base64 JPEG
    
    Returns: (base64_string, PIL_Image_object)
    """
    try:
        image = Image.open(uploaded_file)
        
        # Convert to RGB (JPEG doesn't support transparency)
        if image.mode in ("RGBA", "LA", "P"):
            if image.mode == "P":
                image = image.convert("RGBA")
            
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "RGBA":
                rgb_image.paste(image, mask=image.split()[3])
            else:
                rgb_image.paste(image)
            image = rgb_image
        elif image.mode != "RGB":
            image = image.convert("RGB")
        
        # Resize
        image.thumbnail((800, 800))
        
        # Save to bytes as JPEG
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=70)
        
        # Encode to base64
        image_data = base64.b64encode(buffered.getvalue()).decode()
        
        return image_data, image
    except Exception as e:
        return None, str(e)

def display_vehicle_image(img):
    """
    Display vehicle image from base64 string stored in DB.
    Decodes base64 to bytes before passing to st.image()
    """
    # Handle None
    if img is None:
        st.info("📷 No image")
        return
    
    # Handle NaN
    try:
        if pd.isna(img):
            st.info("📷 No image")
            return
    except:
        pass
    
    # Handle bytes
    if isinstance(img, bytes):
        try:
            st.image(img, use_container_width=True)
            return
        except Exception:
            st.info("📷 No image")
            return
    
    # Handle base64 string
    if isinstance(img, str):
        if len(img.strip()) < 100:
            st.info("📷 No image")
            return
        try:
            # Remove data URL prefix if present
            if img.startswith("data:image"):
                img = img.split(",", 1)[1]
            
            # Decode base64 to bytes
            img_bytes = base64.b64decode(img)
            
            # Display bytes
            st.image(img_bytes, use_container_width=True)
            return
        except Exception:
            st.info("📷 No image")
            return
    
    st.info("📷 No image")

# -------------------- INIT --------------------
init_database()
migrate_database()
create_admin_user()

# -------------------- SESSION --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.station = ""
    st.session_state.role = ""
    st.session_state.page = "Dashboard"

# -------------------- LOGIN --------------------
def login():
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 2.5rem; margin: 0;">🚦 Toll Operations</h1>
        <p style="font-size: 1rem; margin: 0.2rem 0 0 0;">Shift Report System</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 5px 20px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #333;">🔐 Login</h2>
        </div>
        """, unsafe_allow_html=True)
        
        username = st.text_input("Username", key="login_username", placeholder="Enter username")
        password = st.text_input("Password", type="password", key="login_password", placeholder="Enter password")
        
        if st.button("Login", use_container_width=True):
            user = get_user(username)
            if user and user["password_hash"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.station = user["station"]
                st.session_state.role = user["role"]
                st.rerun()
            else:
                st.error("Invalid username or password")

# -------------------- SIDEBAR --------------------
def sidebar():
    with st.sidebar:
        is_manager = st.session_state.role == "manager"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 0.5rem 0;">
            <h3 style="color: white; margin: 0;">🚦 Toll Ops</h3>
            <p style="color: #aaa; font-size: 0.8rem; margin: 0.2rem 0;">{st.session_state.username}</p>
            <p style="color: #aaa; font-size: 0.8rem;">📍 {st.session_state.station}</p>
            <p><span class="badge {'badge-manager' if is_manager else 'badge-supervisor'}">
                {'👑 Manager' if is_manager else '🛡️ Supervisor'}
            </span></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if is_manager:
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
            if st.button("📈 Reports", use_container_width=True):
                st.session_state.page = "Reports"
                st.rerun()
            if st.button("🔒 Settle Shifts", use_container_width=True):
                st.session_state.page = "Settle"
                st.rerun()
            if st.button("📊 Analytics", use_container_width=True):
                st.session_state.page = "Analytics"
                st.rerun()
            if st.button("📋 Consolidated", use_container_width=True):
                st.session_state.page = "Consolidated"
                st.rerun()
            if st.button("🚫 Unpaid", use_container_width=True):
                st.session_state.page = "Unpaid"
                st.rerun()
            if st.button("👥 Users", use_container_width=True):
                st.session_state.page = "Users"
                st.rerun()
        else:
            if st.button("📊 Dashboard", use_container_width=True):
                st.session_state.page = "Dashboard"
                st.rerun()
            if st.button("📝 Submit Report", use_container_width=True):
                st.session_state.page = "Submit"
                st.rerun()
            if st.button("📋 My Data", use_container_width=True):
                st.session_state.page = "MyData"
                st.rerun()
            if st.button("🚫 Unpaid Vehicle", use_container_width=True):
                st.session_state.page = "UserUnpaid"
                st.rerun()
        
        st.markdown("---")
        
        old = st.text_input("Current Password", type="password", key="old_pass")
        new = st.text_input("New Password", type="password", key="new_pass")
        confirm = st.text_input("Confirm", type="password", key="confirm_pass")
        
        if st.button("Change Password", use_container_width=True):
            user = get_user(st.session_state.username)
            if user and user["password_hash"] == hash_password(old):
                if new != confirm:
                    st.error("Passwords don't match")
                elif len(new) < 4:
                    st.error("Min 4 characters")
                else:
                    update_password(st.session_state.username, new)
                    st.success("✅ Password updated!")
            else:
                st.error("Current password incorrect")
        
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.station = ""
            st.session_state.role = ""
            st.rerun()

# ===================================================================
# USER VIEWS
# ===================================================================

def user_dashboard():
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 2rem; margin: 0;">📊 My Dashboard</h1>
        <p style="margin: 0.2rem 0 0 0;">Welcome, {}</p>
    </div>
    """.format(st.session_state.username), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    df = get_reports(
        station=st.session_state.station,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    stats = get_station_stats(
        station=st.session_state.station,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if not stats.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3 style="margin: 0; color: #667eea;">{int(stats['total_reports'].iloc[0])}</h3>
                <p style="margin: 0; color: #666;">Reports</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f093fb;">
                <h3 style="margin: 0; color: #f093fb;">{int(stats['total_traffic'].iloc[0]):,}</h3>
                <p style="margin: 0; color: #666;">Traffic</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #4CAF50;">
                <h3 style="margin: 0; color: #4CAF50;">Br {stats['total_revenue'].iloc[0]:,.2f}</h3>
                <p style="margin: 0; color: #666;">Revenue</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if not df.empty:
        st.subheader("📋 My Data")
        display_cols = ["report_date", "shift", "exit_sys", "entry_sys", "exit_etc", "entry_etc", "cash_sys", "etc", "is_settled"]
        available_cols = [c for c in display_cols if c in df.columns]
        df_display = df[available_cols].copy()
        
        if 'is_settled' in df_display.columns:
            df_display['is_settled'] = df_display['is_settled'].apply(lambda x: '🔒 Locked' if x == 1 else '✏️ Editable')
        
        st.dataframe(df_display, use_container_width=True)
        st.download_button("📥 Download", df.to_csv(index=False), "my_data.csv")
    else:
        st.info("No data found")

def user_submit():
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 2rem; margin: 0;">📝 Submit Report</h1>
        <p style="margin: 0.2rem 0 0 0;">Station: {}</p>
    </div>
    """.format(st.session_state.station), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        report_date = st.date_input("Date", value=date.today(), key="check_date")
    with col2:
        shift = st.selectbox("Shift", ["A", "B", "C"], key="check_shift")
    
    exists, is_settled = get_report_status(
        report_date.strftime("%Y-%m-%d"), 
        shift, 
        st.session_state.station
    )
    
    if exists and is_settled:
        st.markdown("""
        <div class="settled-box">
            <h3>🔒 Shift Settled & Locked</h3>
            <p>This shift has been settled by the admin.</p>
            <p>You <strong>cannot edit</strong> this report.</p>
            <p>Please contact your administrator if changes are needed.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    if exists:
        st.warning("⚠️ A report already exists for this date/shift. You can **update** it until it's settled by admin.")
    else:
        st.success("✅ No report exists yet. You can submit a new report.")
    
    with st.form("report_form"):
        st.markdown("### Traffic")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Exit**")
            exit_sys = st.number_input("System", min_value=0, step=1, value=None, placeholder="Enter value", key="f_exit_sys")
            exit_etc = st.number_input("ETC", min_value=0, step=1, value=None, placeholder="Enter value", key="f_exit_etc")
            exit_man = st.number_input("Manual", min_value=0, step=1, value=None, placeholder="Enter value", key="f_exit_man")
        with col2:
            st.markdown("**Entry**")
            entry_sys = st.number_input("System", min_value=0, step=1, value=None, placeholder="Enter value", key="f_entry_sys")
            entry_etc = st.number_input("ETC", min_value=0, step=1, value=None, placeholder="Enter value", key="f_entry_etc")
            entry_man = st.number_input("Manual", min_value=0, step=1, value=None, placeholder="Enter value", key="f_entry_man")
        
        st.markdown("### Cash")
        col1, col2 = st.columns(2)
        with col1:
            cash_sys = st.number_input("Cash System", min_value=0.0, step=0.01, value=None, placeholder="Enter amount", key="f_cash_sys")
            cash_man = st.number_input("Cash Manual", min_value=0.0, step=0.01, value=None, placeholder="Enter amount", key="f_cash_man")
        with col2:
            etc = st.number_input("ETC Collection", min_value=0.0, step=0.01, value=None, placeholder="Enter amount", key="f_etc")
        
        st.markdown("### Other")
        col1, col2 = st.columns(2)
        with col1:
            thermal_in = st.number_input("Thermal In", min_value=0, step=1, value=None, placeholder="Enter rolls", key="f_thermal_in")
            gen_fuel = st.number_input("Generator Fuel", min_value=0.0, step=0.1, value=None, placeholder="Enter liters", key="f_gen_fuel")
            no_card = st.number_input("No Card", min_value=0, step=1, value=None, placeholder="Enter count", key="f_no_card")
            forged_count = st.number_input("Forged Count", min_value=0, step=1, value=None, placeholder="Enter count", key="f_forged_count")
            forged_amt = st.number_input("Forged Amount", min_value=0.0, step=0.01, value=None, placeholder="Enter amount", key="f_forged_amt")
        with col2:
            thermal_out = st.number_input("Thermal Out", min_value=0, step=1, value=None, placeholder="Enter rolls", key="f_thermal_out")
            veh_fuel = st.number_input("Vehicle Fuel", min_value=0.0, step=0.1, value=None, placeholder="Enter liters", key="f_veh_fuel")
            overload_count = st.number_input("Overload Count", min_value=0, step=1, value=None, placeholder="Enter count", key="f_overload_count")
            overload_amt = st.number_input("Overload Amount", min_value=0.0, step=0.01, value=None, placeholder="Enter amount", key="f_overload_amt")
            gen_hour = st.number_input("Generator Hour", min_value=0.0, step=0.1, value=None, placeholder="Enter reading", key="f_gen_hour")
        
        st.markdown("### Notes")
        good_notes = st.text_area("Good Things", height=60, key="f_good")
        problems = st.text_area("Problems", height=60, key="f_problems")
        solution = st.text_area("Solution", height=60, key="f_solution")
        
        submitted = st.form_submit_button("✅ Submit", use_container_width=True)
        
        if submitted:
            record = {
                "report_date": report_date.strftime("%Y-%m-%d"),
                "shift": shift,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "supervisor": st.session_state.username,
                "station": st.session_state.station,
                "exit_sys": exit_sys if exit_sys is not None else 0,
                "entry_sys": entry_sys if entry_sys is not None else 0,
                "exit_man": exit_man if exit_man is not None else 0,
                "entry_man": entry_man if entry_man is not None else 0,
                "exit_etc": exit_etc if exit_etc is not None else 0,
                "entry_etc": entry_etc if entry_etc is not None else 0,
                "cash_sys": cash_sys if cash_sys is not None else 0,
                "cash_man": cash_man if cash_man is not None else 0,
                "etc": etc if etc is not None else 0,
                "thermal_in": thermal_in if thermal_in is not None else 0,
                "thermal_out": thermal_out if thermal_out is not None else 0,
                "gen_fuel": gen_fuel if gen_fuel is not None else 0,
                "veh_fuel": veh_fuel if veh_fuel is not None else 0,
                "no_card": no_card if no_card is not None else 0,
                "forged_count": forged_count if forged_count is not None else 0,
                "forged_amt": forged_amt if forged_amt is not None else 0,
                "overload_count": overload_count if overload_count is not None else 0,
                "overload_amt": overload_amt if overload_amt is not None else 0,
                "gen_hour": gen_hour if gen_hour is not None else 0,
                "good_notes": good_notes,
                "problems": problems,
                "solution": solution
            }
            
            result = save_report(record)
            
            if result == "inserted":
                st.success("✅ Report submitted successfully!")
                st.balloons()
                st.rerun()
            elif result == "updated":
                st.success("✅ Report updated successfully!")
                st.rerun()
            elif result == "settled":
                st.error("🔒 This shift has been settled by admin. You cannot edit it.")
            else:
                st.error("❌ Error submitting report")

def user_mydata():
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 2rem; margin: 0;">📋 My Data</h1>
        <p style="margin: 0.2rem 0 0 0;">All your reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="my_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="my_end")
    
    df = get_reports(
        station=st.session_state.station,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if not df.empty:
        if 'is_settled' in df.columns:
            df['Status'] = df['is_settled'].apply(lambda x: '🔒 Locked' if x == 1 else '✏️ Editable')
        
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download", df.to_csv(index=False), "my_data.csv")
    else:
        st.info("No data found")

def user_unpaid():
    """Unpaid Vehicle page for END USERS (supervisors)"""
    st.markdown("""
    <div class="main-header">
        <h1 style="font-size: 2rem; margin: 0;">🚫 Unpaid Vehicles</h1>
        <p style="margin: 0.2rem 0 0 0;">Station: {}</p>
    </div>
    """.format(st.session_state.station), unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 My Unpaid List", "➕ Add Unpaid Vehicle"])
    
    with tab1:
        st.subheader("📋 Unpaid Vehicles")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="u_start")
        with col2:
            end_date = st.date_input("End Date", value=date.today(), key="u_end")
        
        status_filter = st.selectbox("Status", ["All", "unpaid", "paid"], key="u_status")
        
        df = get_unpaid_vehicles(
            station=st.session_state.station,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            status=status_filter
        )
        
        if not df.empty:
            total_unpaid = len(df[df["status"] == "unpaid"])
            total_paid = len(df[df["status"] == "paid"])
            total_amount = df["amount"].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vehicles", len(df))
            with col2:
                st.metric("Unpaid", total_unpaid)
            with col3:
                st.metric("Total Amount", f"Br {total_amount:,.2f}")
            
            st.markdown("---")
            
            for idx, row in df.iterrows():
                status_icon = "✅" if row['status'] == "paid" else "⏳"
                
                with st.expander(f"{status_icon} {row['vehicle_number']} ({row['vehicle_type']}) - {row['status'].upper()} - Br {row['amount']:,.2f}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Vehicle Number:** {row['vehicle_number']}")
                        st.write(f"**Vehicle Type:** {row['vehicle_type']}")
                        st.write(f"**Date:** {row['report_date']}")
                        st.write(f"**Shift:** {row['shift']}")
                        st.write(f"**Amount:** Br {row['amount']:,.2f}")
                        st.write(f"**Reason:** {row['reason'] if row['reason'] else 'N/A'}")
                        st.write(f"**Status:** {row['status'].upper()}")
                        if row.get('paid_date'):
                            st.write(f"**Paid Date:** {row['paid_date']}")
                    
                    with col2:
                        st.markdown("**Vehicle Image:**")
                        try:
                            img = row['image_data']
                        except:
                            img = None
                        display_vehicle_image(img)
            
            st.download_button(
                "📥 Download My Unpaid Vehicles",
                df.to_csv(index=False),
                f"unpaid_{st.session_state.station}.csv",
                use_container_width=True
            )
        else:
            st.info("No unpaid vehicles found for the selected filters.")
    
    with tab2:
        st.subheader("➕ Add Unpaid Vehicle")
        
        with st.form("user_unpaid_form"):
            col1, col2 = st.columns(2)
            with col1:
                vehicle_number = st.text_input("Vehicle Number", placeholder="e.g., AA-1234")
                vehicle_type = st.selectbox("Vehicle Type", VEHICLE_TYPES)
                st.info(f"📍 Station: {st.session_state.station}")
            with col2:
                report_date = st.date_input("Date", value=date.today())
                shift = st.selectbox("Shift", ["A", "B", "C"])
                amount = st.number_input("Amount (Birr)", min_value=0.0, step=1.0)
            
            reason = st.text_area("Reason for Unpaid", placeholder="e.g., No card, Insufficient balance, etc.")
            
            uploaded_file = st.file_uploader("📷 Upload Vehicle Image (Optional)", type=["jpg", "jpeg", "png"])
            
            image_data = None
            pil_image = None
            if uploaded_file is not None:
                image_data, result = process_image(uploaded_file)
                if image_data:
                    pil_image = result
                    st.image(pil_image, caption="Uploaded Image Preview", width=200)
                    st.success("✅ Image ready to save!")
                else:
                    st.error(f"Error: {result}")
            
            if st.form_submit_button("➕ Add Unpaid Vehicle", use_container_width=True):
                if vehicle_number:
                    add_unpaid_vehicle(
                        vehicle_number=vehicle_number,
                        vehicle_type=vehicle_type,
                        station=st.session_state.station,
                        report_date=report_date.strftime("%Y-%m-%d"),
                        shift=shift,
                        supervisor=st.session_state.username,
                        amount=amount,
                        reason=reason,
                        image_data=image_data
                    )
                    st.success(f"✅ Unpaid vehicle {vehicle_number} added successfully!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Vehicle Number is required!")

# ===================================================================
# ADMIN VIEWS
# ===================================================================

def admin_settle():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">🔒 Settle Shifts</h1>
        <p style="margin: 0.2rem 0 0 0;">Lock shifts so supervisors cannot edit them</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("ℹ️ Once a shift is settled, supervisors cannot edit it. You can unlock it if needed.")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=7), key="settle_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="settle_end")
    
    station = st.selectbox("Station", ["All"] + STATIONS, key="settle_station")
    station_param = None if station == "All" else station
    
    df = get_reports(
        station=station_param,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if df.empty:
        st.info("No reports found for the selected filters")
        return
    
    total = len(df)
    settled = len(df[df["is_settled"] == 1]) if "is_settled" in df.columns else 0
    unsettled = total - settled
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reports", total)
    with col2:
        st.metric("🔒 Settled", settled)
    with col3:
        st.metric("✏️ Unsettled", unsettled)
    
    st.markdown("---")
    
    st.subheader("⚡ Bulk Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔒 Settle ALL Unsettled", use_container_width=True):
            unsettled_df = df[df["is_settled"] == 0] if "is_settled" in df.columns else df
            for _, row in unsettled_df.iterrows():
                settle_report(row["id"], st.session_state.username)
            st.success(f"✅ Settled {len(unsettled_df)} reports!")
            st.rerun()
    
    with col2:
        if st.button("🔓 Unsettle ALL", use_container_width=True):
            settled_df = df[df["is_settled"] == 1] if "is_settled" in df.columns else pd.DataFrame()
            for _, row in settled_df.iterrows():
                unsettle_report(row["id"])
            st.success(f"✅ Unsettled {len(settled_df)} reports!")
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("📋 Individual Reports")
    
    for _, row in df.iterrows():
        is_settled = row.get("is_settled", 0) == 1
        status_icon = "🔒" if is_settled else "✏️"
        status_text = "Settled" if is_settled else "Editable"
        
        with st.expander(f"{status_icon} {row['station']} | {row['report_date']} | Shift {row['shift']} | {status_text}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Supervisor:** {row['supervisor']}")
                st.write(f"**Traffic:** {int(row['exit_sys'] + row['entry_sys'] + row['exit_etc'] + row['entry_etc'])}")
                st.write(f"**Revenue:** Br {row['cash_sys'] + row['cash_man'] + row['etc']:,.2f}")
                
                if is_settled:
                    st.write(f"**Settled At:** {row.get('settled_at', 'N/A')}")
                    st.write(f"**Settled By:** {row.get('settled_by', 'N/A')}")
            
            with col2:
                if is_settled:
                    if st.button(f"🔓 Unsettle", key=f"unsettle_{row['id']}", use_container_width=True):
                        unsettle_report(row['id'])
                        st.success("✅ Unsettled!")
                        st.rerun()
                else:
                    if st.button(f"🔒 Settle", key=f"settle_{row['id']}", use_container_width=True):
                        settle_report(row['id'], st.session_state.username)
                        st.success("✅ Settled!")
                        st.rerun()

def admin_dashboard():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">📊 Admin Dashboard</h1>
        <p style="margin: 0.2rem 0 0 0;">Welcome, {}</p>
    </div>
    """.format(st.session_state.username), unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="adm_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="adm_end")
    
    df = get_reports(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    stats = get_station_stats(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if not stats.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f5576c;">
                <h3 style="margin: 0; color: #f5576c;">{int(stats['total_reports'].sum())}</h3>
                <p style="margin: 0; color: #666;">Reports</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #f093fb;">
                <h3 style="margin: 0; color: #f093fb;">{int(stats['total_traffic'].sum()):,}</h3>
                <p style="margin: 0; color: #666;">Traffic</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #4CAF50;">
                <h3 style="margin: 0; color: #4CAF50;">Br {stats['total_revenue'].sum():,.2f}</h3>
                <p style="margin: 0; color: #666;">Revenue</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #FF6B6B;">
                <h3 style="margin: 0; color: #FF6B6B;">{stats['total_fuel'].sum():.1f} L</h3>
                <p style="margin: 0; color: #666;">Fuel</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if not df.empty:
        if 'is_settled' in df.columns:
            settled = len(df[df['is_settled'] == 1])
            unsettled = len(df) - settled
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔒 Settled Shifts", settled)
            with col2:
                st.metric("✏️ Unsettled Shifts", unsettled)
            
            st.markdown("---")
        
        st.subheader("📋 Report Data")
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download", df.to_csv(index=False), "admin_report.csv")
    else:
        st.info("No data found")

def admin_reports():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">📈 Reports</h1>
        <p style="margin: 0.2rem 0 0 0;">All station reports</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="rep_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="rep_end")
    
    station = st.selectbox("Station", ["All"] + STATIONS)
    shift = st.selectbox("Shift", ["All", "A", "B", "C"])
    status = st.selectbox("Status", ["All", "Settled", "Editable"])
    
    station_param = None if station == "All" else station
    shift_param = None if shift == "All" else shift
    
    df = get_reports(
        station=station_param,
        shift=shift_param,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if not df.empty and 'is_settled' in df.columns:
        if status == "Settled":
            df = df[df['is_settled'] == 1]
        elif status == "Editable":
            df = df[df['is_settled'] == 0]
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download", df.to_csv(index=False), "reports.csv")
        
        st.markdown("---")
        st.subheader("⚠️ Problems & Solutions")
        issues = df[df["problems"].notna() & (df["problems"] != "")]
        if not issues.empty:
            for _, row in issues.iterrows():
                st.markdown(f"""
                <div style="background: #fff3cd; padding: 0.8rem; border-radius: 8px; border-left: 4px solid #f44336; margin-bottom: 0.5rem;">
                    <strong>🚨 {row['station']}</strong> | {row['report_date']} | {row['shift']}<br>
                    <strong>Problem:</strong> {row['problems']}<br>
                    <strong>Solution:</strong> {row['solution'] if row['solution'] else 'No solution recorded'}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No problems reported")
    else:
        st.info("No data found")

def admin_analytics():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">📊 Analytics</h1>
        <p style="margin: 0.2rem 0 0 0;">Charts & graphs</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="ana_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="ana_end")
    
    station = st.selectbox("Station", ["All"] + STATIONS, key="ana_station")
    station_param = None if station == "All" else station
    
    df = get_reports(
        station=station_param,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if df.empty:
        st.info("No data available")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Reports", len(df))
    with col2:
        st.metric("Vehicles", int(df["exit_sys"].sum() + df["entry_sys"].sum() + df["exit_etc"].sum() + df["entry_etc"].sum()))
    with col3:
        st.metric("Revenue", f"Br {df['cash_sys'].sum() + df['cash_man'].sum() + df['etc'].sum():,.0f}")
    with col4:
        st.metric("Fuel", f"{df['gen_fuel'].sum() + df['veh_fuel'].sum():.1f} L")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚗 Traffic by Station")
        traffic = df.groupby("station").agg({
            "exit_sys": "sum", "entry_sys": "sum",
            "exit_etc": "sum", "entry_etc": "sum"
        }).reset_index()
        traffic["Total"] = traffic["exit_sys"] + traffic["entry_sys"] + traffic["exit_etc"] + traffic["entry_etc"]
        fig = px.bar(traffic, x="station", y="Total", color="station", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🥧 Traffic Distribution")
        total_sys = df["exit_sys"].sum() + df["entry_sys"].sum()
        total_etc = df["exit_etc"].sum() + df["entry_etc"].sum()
        total_man = df["exit_man"].sum() + df["entry_man"].sum()
        if total_sys > 0 or total_etc > 0 or total_man > 0:
            fig = px.pie(values=[total_sys, total_etc, total_man], names=["System", "ETC", "Manual"],
                        color_discrete_sequence=["#667eea", "#4CAF50", "#FF9800"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Revenue by Station")
        rev = df.groupby("station").agg({"cash_sys": "sum", "cash_man": "sum", "etc": "sum"}).reset_index()
        rev["Total"] = rev["cash_sys"] + rev["cash_man"] + rev["etc"]
        fig = px.bar(rev, x="station", y="Total", color="station", color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)", height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🥧 Revenue Distribution")
        total_cash = df["cash_sys"].sum() + df["cash_man"].sum()
        total_etc = df["etc"].sum()
        if total_cash > 0 or total_etc > 0:
            fig = px.pie(values=[total_cash, total_etc], names=["Cash", "ETC"],
                        color_discrete_sequence=["#667eea", "#f093fb"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📈 Daily Trends")
    daily = df.groupby("report_date").agg({
        "exit_sys": "sum", "entry_sys": "sum",
        "exit_etc": "sum", "entry_etc": "sum",
        "cash_sys": "sum", "cash_man": "sum", "etc": "sum"
    }).reset_index()
    daily["Traffic"] = daily["exit_sys"] + daily["entry_sys"] + daily["exit_etc"] + daily["entry_etc"]
    daily["Revenue"] = daily["cash_sys"] + daily["cash_man"] + daily["etc"]
    
    fig = px.line(daily, x="report_date", y=["Traffic", "Revenue"],
                  color_discrete_sequence=["#667eea", "#f5576c"])
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", height=350)
    st.plotly_chart(fig, use_container_width=True)

def admin_consolidated():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">📋 Consolidated Report</h1>
        <p style="margin: 0.2rem 0 0 0;">Summary by station</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="cons_start")
    with col2:
        end_date = st.date_input("End Date", value=date.today(), key="cons_end")
    
    df = get_reports(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    if df.empty:
        st.info("No data available")
        return
    
    summary = df.groupby("station").agg({
        "supervisor": "count",
        "exit_sys": "sum",
        "entry_sys": "sum",
        "exit_etc": "sum",
        "entry_etc": "sum",
        "cash_sys": "sum",
        "cash_man": "sum",
        "etc": "sum",
        "gen_fuel": "sum",
        "veh_fuel": "sum",
        "no_card": "sum"
    }).reset_index()
    
    summary["Traffic"] = summary["exit_sys"] + summary["entry_sys"] + summary["exit_etc"] + summary["entry_etc"]
    summary["Revenue"] = summary["cash_sys"] + summary["cash_man"] + summary["etc"]
    summary["Fuel"] = summary["gen_fuel"] + summary["veh_fuel"]
    
    display = summary[["station", "supervisor", "Traffic", "Revenue", "Fuel", "no_card"]]
    display.columns = ["Station", "Reports", "Traffic", "Revenue", "Fuel (L)", "No Card"]
    
    st.dataframe(display, use_container_width=True)
    st.download_button("📥 Download", summary.to_csv(index=False), "consolidated.csv")

def admin_unpaid():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">🚫 Unpaid Vehicles</h1>
        <p style="margin: 0.2rem 0 0 0;">Manage unpaid vehicles</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 List", "➕ Add"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30), key="unp_start")
        with col2:
            end_date = st.date_input("End Date", value=date.today(), key="unp_end")
        
        station = st.selectbox("Station", ["All"] + STATIONS, key="unp_station")
        station_param = None if station == "All" else station
        
        df = get_unpaid_vehicles(
            station=station_param,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if not df.empty:
            total_unpaid = len(df[df["status"] == "unpaid"])
            total_paid = len(df[df["status"] == "paid"])
            total_amount = df["amount"].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vehicles", len(df))
            with col2:
                st.metric("Unpaid", total_unpaid)
            with col3:
                st.metric("Total Amount", f"Br {total_amount:,.2f}")
            
            st.markdown("---")
            st.subheader("📋 Vehicle Records")
            
            for idx, row in df.iterrows():
                status_icon = "✅" if row['status'] == "paid" else "⏳"
                
                with st.expander(f"{status_icon} {row['vehicle_number']} ({row['vehicle_type']}) | {row['station']} | Br {row['amount']:,.2f}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Vehicle Number:** {row['vehicle_number']}")
                        st.write(f"**Vehicle Type:** {row['vehicle_type']}")
                        st.write(f"**Station:** {row['station']}")
                        st.write(f"**Date:** {row['report_date']}")
                        st.write(f"**Shift:** {row['shift']}")
                        st.write(f"**Supervisor:** {row['supervisor']}")
                        st.write(f"**Amount:** Br {row['amount']:,.2f}")
                        st.write(f"**Reason:** {row['reason'] if row['reason'] else 'N/A'}")
                        st.write(f"**Status:** {row['status'].upper()}")
                        if row.get('paid_date'):
                            st.write(f"**Paid Date:** {row['paid_date']}")
                    
                    with col2:
                        st.markdown("**Vehicle Image:**")
                        try:
                            img = row['image_data']
                        except:
                            img = None
                        display_vehicle_image(img)
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        new_status = "paid" if row['status'] == "unpaid" else "unpaid"
                        if st.button(f"Mark as {new_status.upper()}", key=f"status_{row['id']}"):
                            update_unpaid_vehicle_status(row['id'], new_status, date.today().strftime("%Y-%m-%d") if new_status == "paid" else None)
                            st.success(f"✅ Marked as {new_status}!")
                            st.rerun()
                    with col4:
                        if st.button("🗑️ Delete", key=f"delete_{row['id']}"):
                            delete_unpaid_vehicle(row['id'])
                            st.success("✅ Deleted!")
                            st.rerun()
            
            st.download_button("📥 Download", df.to_csv(index=False), "unpaid.csv")
        else:
            st.info("No unpaid vehicles found")
    
    with tab2:
        with st.form("unpaid_form"):
            col1, col2 = st.columns(2)
            with col1:
                vehicle_number = st.text_input("Vehicle Number")
                vehicle_type = st.selectbox("Vehicle Type", VEHICLE_TYPES)
                station = st.selectbox("Station", STATIONS)
            with col2:
                report_date = st.date_input("Date", value=date.today())
                shift = st.selectbox("Shift", ["A", "B", "C"])
                amount = st.number_input("Amount", min_value=0.0, step=1.0)
            
            reason = st.text_area("Reason")
            uploaded_file = st.file_uploader("Image", type=["jpg", "png", "jpeg"])
            
            image_data = None
            pil_image = None
            if uploaded_file:
                image_data, result = process_image(uploaded_file)
                if image_data:
                    pil_image = result
                    st.image(pil_image, width=150)
                    st.success("✅ Image ready!")
                else:
                    st.error(f"Error: {result}")
            
            if st.form_submit_button("Add", use_container_width=True):
                if vehicle_number:
                    add_unpaid_vehicle(
                        vehicle_number, vehicle_type, station,
                        report_date.strftime("%Y-%m-%d"), shift,
                        st.session_state.username, amount, reason, image_data
                    )
                    st.success("✅ Added successfully!")
                    st.rerun()
                else:
                    st.error("Vehicle number required")

def admin_users():
    st.markdown("""
    <div class="manager-header">
        <h1 style="font-size: 2rem; margin: 0;">👥 Users</h1>
        <p style="margin: 0.2rem 0 0 0;">Manage users</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 All Users", "➕ Add User"])
    
    with tab1:
        df = get_all_users()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
    
    with tab2:
        with st.form("user_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            station = st.selectbox("Station", STATIONS)
            role = st.selectbox("Role", ["supervisor", "manager"])
            
            if st.form_submit_button("Add User", use_container_width=True):
                if username and password:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    try:
                        cursor.execute('INSERT INTO users (username, password_hash, station, role) VALUES (?, ?, ?, ?)',
                                      (username, hash_password(password), station, role))
                        conn.commit()
                        st.success(f"✅ User {username} created!")
                    except:
                        st.error("Username already exists")
                    conn.close()
                else:
                    st.error("Username and password required")

# -------------------- MAIN --------------------
def main():
    if not st.session_state.logged_in:
        login()
    else:
        sidebar()
        
        is_manager = st.session_state.role == "manager"
        
        if is_manager:
            if st.session_state.page == "Dashboard":
                admin_dashboard()
            elif st.session_state.page == "Reports":
                admin_reports()
            elif st.session_state.page == "Settle":
                admin_settle()
            elif st.session_state.page == "Analytics":
                admin_analytics()
            elif st.session_state.page == "Consolidated":
                admin_consolidated()
            elif st.session_state.page == "Unpaid":
                admin_unpaid()
            elif st.session_state.page == "Users":
                admin_users()
            else:
                admin_dashboard()
        else:
            if st.session_state.page == "Dashboard":
                user_dashboard()
            elif st.session_state.page == "Submit":
                user_submit()
            elif st.session_state.page == "MyData":
                user_mydata()
            elif st.session_state.page == "UserUnpaid":
                user_unpaid()
            else:
                user_dashboard()
        
        st.markdown('<div class="footer">© 2026 Toll Operations Manager</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
