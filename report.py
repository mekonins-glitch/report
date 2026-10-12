"""
Toll Operations Manager  (v2)
Single file: toll_operations.py

Run:   streamlit run toll_operations.py
Needs: streamlit>=1.37, pandas, plotly, pillow
"""

import base64
import hashlib
import hmac
import html
import io
import os
import re
import secrets
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

# -------------------- PAGE CONFIG (must be first st call) --------------------
st.set_page_config(page_title="Toll Operations", page_icon="🚦", layout="wide")

# -------------------- CONSTANTS --------------------
DB_FILE = os.environ.get("TOLL_DB", "toll_operations.db")
STATIONS = ["Modjo East", "Koka", "Bote", "Meki", "Batu"]
ALL_STATIONS = "All Stations"
SHIFTS = ["A", "B", "C"]
VEHICLE_TYPES = ["V1", "V2", "V3", "V4", "V5", "V6", "V7"]
ROLE_SUPERVISOR = "supervisor"
ROLE_STATION = "station_manager"
ROLE_ADMIN = "manager"  # stored value kept for existing databases; shown as "Super Admin"
ROLE_LABELS = {
    ROLE_SUPERVISOR: "🛡️ Supervisor",
    ROLE_STATION: "🏢 Station Manager",
    ROLE_ADMIN: "👑 Super Admin",
}
MIN_PASSWORD = 6
PBKDF2_ITERS = 200_000
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

INT_FIELDS = [
    "exit_sys", "entry_sys", "exit_man", "entry_man", "exit_etc", "entry_etc",
    "thermal_exit", "thermal_entry", "no_card", "forged_count", "overload_count",
]
FLOAT_FIELDS = [
    "cash_sys", "cash_man", "etc", "gen_fuel", "veh_fuel", "veh_odo",
    "forged_amt", "overload_amt", "gen_hour",
]
NUM_FIELDS = INT_FIELDS + FLOAT_FIELDS
TEXT_FIELDS = ["gen_operator", "gen_remark", "good_notes", "problems", "solution"]

# Traffic = system + ETC + manual lanes, entry and exit.
TRAFFIC_COLS = ["exit_sys", "entry_sys", "exit_etc", "entry_etc", "exit_man", "entry_man"]
REVENUE_COLS = ["cash_sys", "cash_man", "etc"]
FUEL_COLS = ["gen_fuel", "veh_fuel"]

# -------------------- STYLE (theme-neutral: works in light and dark) --------------------
st.markdown(
    """
<style>
    .page-header {
        padding: 1.2rem 1.5rem; border-radius: 12px; color: white;
        margin-bottom: 1rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .page-header.manager { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .page-header h1 { margin: 0; padding: 0; font-size: 1.8rem; color: white; }
    .page-header p { margin: 0.2rem 0 0 0; opacity: 0.9; }
    .locked-box {
        padding: 1.2rem; border-radius: 12px; text-align: center;
        background: rgba(255, 193, 7, 0.15); border-left: 4px solid #ffc107;
    }
    .block-container { padding-top: 2rem; }
</style>
""",
    unsafe_allow_html=True,
)


def header(title: str, subtitle: str = "", manager: bool = False):
    cls = "page-header manager" if manager else "page-header"
    st.markdown(
        f'<div class="{cls}"><h1>{html.escape(title)}</h1>'
        f"<p>{html.escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


# ===================================================================
# DATABASE
# ===================================================================
@contextmanager
def db():
    """Connection that commits on success, rolls back on error, always closes."""
    conn = sqlite3.connect(DB_FILE, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fname TEXT NOT NULL DEFAULT '',
    lname TEXT NOT NULL DEFAULT '',
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    station TEXT NOT NULL,
    role TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    must_change_password INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date DATE,
    shift TEXT,
    timestamp TIMESTAMP NOT NULL,
    supervisor TEXT NOT NULL,
    station TEXT NOT NULL,
    exit_sys INTEGER DEFAULT 0, entry_sys INTEGER DEFAULT 0,
    exit_man INTEGER DEFAULT 0, entry_man INTEGER DEFAULT 0,
    exit_etc INTEGER DEFAULT 0, entry_etc INTEGER DEFAULT 0,
    cash_sys REAL DEFAULT 0, cash_man REAL DEFAULT 0, etc REAL DEFAULT 0,
    thermal_in INTEGER DEFAULT 0, thermal_out INTEGER DEFAULT 0,
    thermal_exit INTEGER DEFAULT 0, thermal_entry INTEGER DEFAULT 0,
    gen_fuel REAL DEFAULT 0, gen_operator TEXT, gen_remark TEXT,
    veh_fuel REAL DEFAULT 0, veh_odo REAL DEFAULT 0,
    no_card INTEGER DEFAULT 0,
    forged_count INTEGER DEFAULT 0, forged_amt REAL DEFAULT 0,
    overload_count INTEGER DEFAULT 0, overload_amt REAL DEFAULT 0,
    gen_hour REAL DEFAULT 0,
    good_notes TEXT, problems TEXT, solution TEXT,
    is_settled INTEGER DEFAULT 0,
    settled_at TIMESTAMP,
    settled_by TEXT,
    UNIQUE(station, report_date, shift)
);
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
    paid_by TEXT,
    image_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username TEXT NOT NULL,
    role TEXT,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    target_name TEXT,
    details TEXT,
    station TEXT,
    ip_address TEXT
);
"""

# Columns older versions of the database may be missing.
MIGRATIONS = {
    "users": {
        "fname": "TEXT DEFAULT ''",
        "lname": "TEXT DEFAULT ''",
        "is_active": "INTEGER DEFAULT 1",
        "must_change_password": "INTEGER DEFAULT 0",
        "updated_at": "TIMESTAMP",
    },
    "reports": {
        "thermal_exit": "INTEGER DEFAULT 0",
        "thermal_entry": "INTEGER DEFAULT 0",
        "gen_operator": "TEXT",
        "gen_remark": "TEXT",
        "veh_odo": "REAL DEFAULT 0",
        "is_settled": "INTEGER DEFAULT 0",
        "settled_at": "TIMESTAMP",
        "settled_by": "TEXT",
    },
    "unpaid_vehicles": {"image_data": "TEXT", "paid_by": "TEXT"},
}

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_reports_date ON reports(report_date)",
    "CREATE INDEX IF NOT EXISTS idx_reports_station ON reports(station, report_date)",
    "CREATE INDEX IF NOT EXISTS idx_unpaid_station ON unpaid_vehicles(station, report_date)",
    "CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(username, action)",
]


# -------------------- PASSWORDS --------------------
def hash_password(password: str) -> str:
    """Salted PBKDF2. Format: pbkdf2$iterations$salt$hash"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERS).hex()
    return f"pbkdf2${PBKDF2_ITERS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2$"):
        try:
            _, iters, salt, digest = stored.split("$")
            calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters)).hex()
            return hmac.compare_digest(calc, digest)
        except ValueError:
            return False
    # Legacy unsalted SHA-256 (from the original app); upgraded on next login.
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


def setup_database():
    with db() as conn:
        conn.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
        for stmt in INDEXES:
            conn.execute(stmt)
        # Fill "paid by" for vehicles marked paid before this column existed (from the audit log).
        conn.execute(
            """UPDATE unpaid_vehicles SET paid_by = (
                   SELECT username FROM audit_log
                   WHERE action = 'UPDATE_UNPAID_STATUS' AND target_id = CAST(unpaid_vehicles.id AS TEXT)
                     AND details LIKE '% as paid'
                   ORDER BY id DESC LIMIT 1)
               WHERE status = 'paid' AND paid_by IS NULL"""
        )
        # A Super Admin sees every station. Older "manager" accounts tied to one station were
        # really station managers, so convert them.
        conn.execute(
            "UPDATE users SET role = 'station_manager' WHERE role = 'manager' AND station != ?",
            (ALL_STATIONS,),
        )
        if not conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone():
            conn.execute(
                """INSERT INTO users (fname, lname, username, password_hash, station, role,
                                      is_active, must_change_password)
                   VALUES ('System', 'Admin', 'admin', ?, ?, 'manager', 1, 1)""",
                (hash_password("admin123"), ALL_STATIONS),
            )


@st.cache_resource
def init_once(schema_version: int = 4):
    setup_database()
    return True


# -------------------- AUDIT LOG --------------------
def actor():
    u = st.session_state.get("_user")
    return (u["username"], u["role"]) if u else ("anonymous", None)


def log_action(who, action, target_type=None, target_id=None, target_name=None,
               details=None, station=None, conn=None):
    username, role = who
    sql = """INSERT INTO audit_log
             (timestamp, username, role, action, target_type, target_id, target_name, details, station)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    args = (now_str(), username, role, action, target_type,
            None if target_id is None else str(target_id), target_name, details, station)
    try:
        if conn is not None:
            conn.execute(sql, args)
        else:
            with db() as c:
                c.execute(sql, args)
    except sqlite3.Error:
        pass  # never break the app because logging failed


def get_audit_log(limit=200, username=None, action=None, start_date=None, end_date=None):
    query, params = "SELECT * FROM audit_log WHERE 1=1", []
    if username:
        query += " AND username = ?"
        params.append(username)
    if action:
        query += " AND action = ?"
        params.append(action)
    if start_date:
        query += " AND DATE(timestamp) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND DATE(timestamp) <= ?"
        params.append(end_date)
    query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit)
    with db() as conn:
        return pd.read_sql_query(query, conn, params=params)


def recent_failed_logins(username: str) -> int:
    cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    with db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) FROM audit_log
               WHERE action = 'LOGIN_FAILED' AND username = ? AND timestamp >= ?
                 AND timestamp > COALESCE((SELECT MAX(timestamp) FROM audit_log
                                           WHERE action = 'LOGIN' AND username = ?), '')""",
            (username, cutoff, username),
        ).fetchone()
    return row[0]


# -------------------- USERS --------------------
def get_user(username=None, user_id=None):
    with db() as conn:
        if user_id is not None:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_all_users() -> pd.DataFrame:
    with db() as conn:
        return pd.read_sql_query(
            """SELECT id, fname, lname, username, station, role, is_active, created_at, updated_at
               FROM users ORDER BY is_active DESC, username""",
            conn,
        )


def username_taken(username: str, exclude_id=None) -> bool:
    with db() as conn:
        if exclude_id:
            row = conn.execute("SELECT 1 FROM users WHERE username = ? AND id != ?",
                               (username, exclude_id)).fetchone()
        else:
            row = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    return row is not None


def create_user(fname, lname, username, password, station, role, who):
    if role == ROLE_ADMIN:
        station = ALL_STATIONS
    try:
        with db() as conn:
            cur = conn.execute(
                """INSERT INTO users (fname, lname, username, password_hash, station, role,
                                      is_active, must_change_password)
                   VALUES (?, ?, ?, ?, ?, ?, 1, 1)""",
                (fname, lname, username, hash_password(password), station, role),
            )
            log_action(who, "CREATE_USER", "USER", cur.lastrowid, username,
                       f"Created {role}: {fname} {lname} ({username}) at {station}", conn=conn)
        return True, "User created"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except sqlite3.Error as e:
        return False, str(e)


def update_user(user_id, fname, lname, username, station, role, new_password, who):
    if role == ROLE_ADMIN:
        station = ALL_STATIONS
    try:
        with db() as conn:
            old = conn.execute("SELECT fname, lname, username FROM users WHERE id = ?",
                               (user_id,)).fetchone()
            if not old:
                return False, "User not found"
            if new_password:
                conn.execute(
                    """UPDATE users SET fname=?, lname=?, username=?, station=?, role=?,
                              password_hash=?, must_change_password=1, updated_at=? WHERE id=?""",
                    (fname, lname, username, station, role, hash_password(new_password), now_str(), user_id),
                )
            else:
                conn.execute(
                    """UPDATE users SET fname=?, lname=?, username=?, station=?, role=?,
                              updated_at=? WHERE id=?""",
                    (fname, lname, username, station, role, now_str(), user_id),
                )
            note = " (password reset)" if new_password else ""
            log_action(who, "UPDATE_USER", "USER", user_id, username,
                       f"{old['fname']} {old['lname']} ({old['username']}) → "
                       f"{fname} {lname} ({username}), {role} @ {station}{note}", conn=conn)
        return True, "User updated"
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    except sqlite3.Error as e:
        return False, str(e)


def set_user_active(user_id, active: bool, who):
    me = st.session_state.get("_user_id")
    if not active and user_id == me:
        return False, "You cannot deactivate your own account"
    with db() as conn:
        u = conn.execute("SELECT fname, lname, username FROM users WHERE id = ?", (user_id,)).fetchone()
        if not u:
            return False, "User not found"
        conn.execute("UPDATE users SET is_active=?, updated_at=? WHERE id=?",
                     (1 if active else 0, now_str(), user_id))
        word = "activated" if active else "deactivated"
        log_action(who, "ACTIVATE_USER" if active else "DEACTIVATE_USER", "USER", user_id,
                   u["username"], f"User {word}: {u['fname']} {u['lname']} ({u['username']})", conn=conn)
    return True, f"User {word}"


def change_password(user_id, new_password, who):
    with db() as conn:
        conn.execute(
            "UPDATE users SET password_hash=?, must_change_password=0, updated_at=? WHERE id=?",
            (hash_password(new_password), now_str(), user_id),
        )
        log_action(who, "CHANGE_PASSWORD", "USER", user_id, who[0], "Changed own password", conn=conn)


# -------------------- REPORTS --------------------
@st.cache_data(ttl=60, show_spinner=False)
def get_reports(station=None, start_date=None, end_date=None, shift=None) -> pd.DataFrame:
    query, params = "SELECT * FROM reports WHERE 1=1", []
    if station and station != ALL_STATIONS:
        query += " AND station = ?"
        params.append(station)
    if shift:
        query += " AND shift = ?"
        params.append(shift)
    if start_date:
        query += " AND report_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND report_date <= ?"
        params.append(end_date)
    query += " ORDER BY report_date DESC, station, shift"
    with db() as conn:
        return pd.read_sql_query(query, conn, params=params)


def get_report(station, report_date, shift):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM reports WHERE station=? AND report_date=? AND shift=?",
            (station, report_date, shift),
        ).fetchone()
    return dict(row) if row else None


def save_partial(station, report_date, shift, supervisor, fields: dict, label: str, who) -> str:
    """Save only the given fields of a shift report (creates the report row if needed)."""
    allowed = set(NUM_FIELDS + TEXT_FIELDS)
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return "error"
    try:
        with db() as conn:
            existing = conn.execute(
                "SELECT id, is_settled FROM reports WHERE station=? AND report_date=? AND shift=?",
                (station, report_date, shift),
            ).fetchone()
            target = f"{station} {report_date} Shift {shift}"
            if existing:
                if existing["is_settled"] == 1:
                    return "settled"
                cols = ["timestamp", "supervisor"] + list(fields)
                sets = ", ".join(f"{c} = ?" for c in cols)
                conn.execute(f"UPDATE reports SET {sets} WHERE id = ?",
                             [now_str(), supervisor] + list(fields.values()) + [existing["id"]])
                log_action(who, "UPDATE_REPORT", "REPORT", existing["id"], target,
                           f"Saved {label}", station, conn=conn)
                result = "updated"
            else:
                cols = ["report_date", "shift", "timestamp", "supervisor", "station"] + list(fields)
                marks = ", ".join("?" for _ in cols)
                cur = conn.execute(
                    f"INSERT INTO reports ({', '.join(cols)}) VALUES ({marks})",
                    [report_date, shift, now_str(), supervisor, station] + list(fields.values()),
                )
                log_action(who, "CREATE_REPORT", "REPORT", cur.lastrowid, target,
                           f"Created report with {label}", station, conn=conn)
                result = "inserted"
        st.cache_data.clear()
        return result
    except sqlite3.Error:
        return "error"


def set_settled(report_ids, settled: bool, who) -> int:
    """Settle / unsettle many reports in one transaction."""
    ids = [int(i) for i in report_ids]
    if not ids:
        return 0
    marks = ",".join("?" for _ in ids)
    with db() as conn:
        rows = conn.execute(
            f"SELECT id, station, report_date, shift FROM reports WHERE id IN ({marks})", ids
        ).fetchall()
        if settled:
            conn.execute(
                f"UPDATE reports SET is_settled=1, settled_at=?, settled_by=? WHERE id IN ({marks})",
                [now_str(), who[0]] + ids,
            )
        else:
            conn.execute(
                f"UPDATE reports SET is_settled=0, settled_at=NULL, settled_by=NULL WHERE id IN ({marks})",
                ids,
            )
        for r in rows:
            log_action(who, "SETTLE_REPORT" if settled else "UNSETTLE_REPORT", "REPORT", r["id"],
                       f"{r['station']} {r['report_date']} Shift {r['shift']}",
                       "Settled shift" if settled else "Unsettled shift", r["station"], conn=conn)
    st.cache_data.clear()
    return len(rows)


# -------------------- UNPAID VEHICLES --------------------
@st.cache_data(ttl=60, show_spinner=False)
def get_unpaid(station=None, start_date=None, end_date=None, status=None) -> pd.DataFrame:
    """List query. Images are NOT loaded here (they are large) - see get_unpaid_image."""
    query = """SELECT id, vehicle_number, vehicle_type, station, report_date, shift, supervisor,
                      amount, reason, status, paid_date, paid_by, created_at,
                      (image_data IS NOT NULL AND image_data != '') AS has_image
               FROM unpaid_vehicles WHERE 1=1"""
    params = []
    if station and station != ALL_STATIONS:
        query += " AND station = ?"
        params.append(station)
    if status and status != "All":
        query += " AND status = ?"
        params.append(status)
    if start_date:
        query += " AND report_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND report_date <= ?"
        params.append(end_date)
    query += " ORDER BY report_date DESC, created_at DESC"
    with db() as conn:
        df = pd.read_sql_query(query, conn, params=params)
    df["has_image"] = df["has_image"].astype(bool)
    return df


def get_unpaid_image(vehicle_id: int):
    with db() as conn:
        row = conn.execute("SELECT image_data FROM unpaid_vehicles WHERE id = ?", (vehicle_id,)).fetchone()
    return row["image_data"] if row else None


def add_unpaid(vehicle_number, vehicle_type, station, report_date, shift, amount, reason, image_data, who):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO unpaid_vehicles (vehicle_number, vehicle_type, station, report_date, shift,
                                            supervisor, amount, reason, status, image_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unpaid', ?)""",
            (vehicle_number, vehicle_type, station, report_date, shift, who[0], amount, reason, image_data),
        )
        log_action(who, "CREATE_UNPAID", "UNPAID_VEHICLE", cur.lastrowid, vehicle_number,
                   f"Added unpaid vehicle {vehicle_number} ({vehicle_type}) - Br {amount:,.2f}",
                   station, conn=conn)
    st.cache_data.clear()


def set_unpaid_status(vehicle_id, status, who):
    with db() as conn:
        row = conn.execute("SELECT vehicle_number, station FROM unpaid_vehicles WHERE id=?",
                           (vehicle_id,)).fetchone()
        if not row:
            return
        paid_date = date.today().isoformat() if status == "paid" else None
        paid_by = who[0] if status == "paid" else None
        conn.execute("UPDATE unpaid_vehicles SET status=?, paid_date=?, paid_by=? WHERE id=?",
                     (status, paid_date, paid_by, vehicle_id))
        log_action(who, "UPDATE_UNPAID_STATUS", "UNPAID_VEHICLE", vehicle_id, row["vehicle_number"],
                   f"Marked {row['vehicle_number']} as {status}", row["station"], conn=conn)
    st.cache_data.clear()


def delete_unpaid(vehicle_id, who):
    with db() as conn:
        row = conn.execute("SELECT vehicle_number, station FROM unpaid_vehicles WHERE id=?",
                           (vehicle_id,)).fetchone()
        if not row:
            return
        conn.execute("DELETE FROM unpaid_vehicles WHERE id=?", (vehicle_id,))
        log_action(who, "DELETE_UNPAID", "UNPAID_VEHICLE", vehicle_id, row["vehicle_number"],
                   f"Deleted unpaid vehicle {row['vehicle_number']}", row["station"], conn=conn)
    st.cache_data.clear()


# -------------------- IMAGES --------------------
MAX_UPLOAD_MB = 8


def process_image(uploaded_file):
    """Returns (base64_jpeg, None) or (None, error_message)."""
    if uploaded_file.size > MAX_UPLOAD_MB * 1024 * 1024:
        return None, f"Image is larger than {MAX_UPLOAD_MB} MB"
    try:
        image = Image.open(uploaded_file)
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGBA")
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((800, 800))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode(), None
    except Exception as e:  # noqa: BLE001
        return None, f"Could not read image: {e}"


def show_vehicle_image(vehicle_id: int):
    data = get_unpaid_image(vehicle_id)
    if not data or len(data.strip()) < 100:
        st.caption("📷 No image")
        return
    try:
        if data.startswith("data:image"):
            data = data.split(",", 1)[1]
        st.image(base64.b64decode(data), use_container_width=True)
    except Exception:  # noqa: BLE001
        st.caption("📷 Image could not be displayed")


# ===================================================================
# UI HELPERS
# ===================================================================
def flash(message: str, icon: str = "✅"):
    """Queue a toast that survives st.rerun()."""
    st.session_state.setdefault("_flash", []).append((message, icon))


def show_flash():
    for message, icon in st.session_state.pop("_flash", []):
        st.toast(message, icon=icon)


def current_user():
    """Fresh user row from the DB on every run, so deactivation/role changes apply immediately."""
    uid = st.session_state.get("_user_id")
    if uid is None:
        return None
    user = get_user(user_id=uid)
    if not user or not user["is_active"]:
        for k in ("_user_id", "_user"):
            st.session_state.pop(k, None)
        return None
    st.session_state["_user"] = user
    return user


def display_name(user) -> str:
    return f"{user['fname']} {user['lname']}".strip() or user["username"]


def date_range(key: str, days: int = 30, label: str = "Date range"):
    today = date.today()
    rng = st.date_input(label, value=(today - timedelta(days=days), today), key=key)
    if not isinstance(rng, (list, tuple)) or len(rng) != 2:
        st.info("Pick both a start date and an end date.")
        st.stop()
    return rng[0].isoformat(), rng[1].isoformat()


def is_admin(user) -> bool:
    """Super Admin: sees everything, manages users. Must not be tied to a single station."""
    return user["role"] == ROLE_ADMIN and user["station"] == ALL_STATIONS


def can_manage(user) -> bool:
    """Super Admin or Station Manager: settle shifts, manage unpaid vehicles, view reports."""
    return user["role"] in (ROLE_ADMIN, ROLE_STATION)


def own_station(user):
    """Station filter for the user (None = all stations)."""
    if is_admin(user) or user["station"] == ALL_STATIONS:
        return None
    return user["station"]


def station_filter(user, key, container=None, label="Station"):
    """Station picker. Super Admin chooses; a Station Manager is locked to their own station.
    Returns the station name, or None for all stations."""
    box = container if container is not None else st
    if is_admin(user):
        pick = box.selectbox(label, [ALL_STATIONS] + STATIONS, key=key)
        return None if pick == ALL_STATIONS else pick
    box.selectbox(label, [user["station"]], key=key, disabled=True)
    return user["station"]


def with_totals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Entry"] = df["entry_sys"] + df["entry_etc"] + df["entry_man"]
    df["Exit"] = df["exit_sys"] + df["exit_etc"] + df["exit_man"]
    df["tr_sys"] = df["entry_sys"] + df["exit_sys"]
    df["tr_etc"] = df["entry_etc"] + df["exit_etc"]
    df["tr_man"] = df["entry_man"] + df["exit_man"]
    df["Traffic"] = df[TRAFFIC_COLS].sum(axis=1)
    df["Revenue"] = df[REVENUE_COLS].sum(axis=1)
    df["Fuel"] = df[FUEL_COLS].sum(axis=1)
    df["Status"] = df["is_settled"].map({1: "🔒 Settled", 0: "✏️ Open"})
    return df


def kpi_row(df: pd.DataFrame):
    d = with_totals(df) if not df.empty else df
    values = [
        ("Reports", f"{len(df):,}"),
        ("Traffic", f"{int(d['Traffic'].sum()):,}" if not df.empty else "0"),
        ("Revenue", f"Br {d['Revenue'].sum():,.2f}" if not df.empty else "Br 0.00"),
        ("Fuel", f"{d['Fuel'].sum():,.1f} L" if not df.empty else "0.0 L"),
    ]
    for col, (label, value) in zip(st.columns(4), values):
        with col, st.container(border=True):
            st.metric(label, value)


REPORT_CONFIG = {
    "report_date": st.column_config.TextColumn("Date"),
    "shift": st.column_config.TextColumn("Shift", width="small"),
    "station": st.column_config.TextColumn("Station"),
    "supervisor": st.column_config.TextColumn("Supervisor"),
    "Entry": st.column_config.NumberColumn("Entry", format="%d"),
    "Exit": st.column_config.NumberColumn("Exit", format="%d"),
    "Traffic": st.column_config.NumberColumn("Total Traffic", format="%d"),
    "tr_sys": st.column_config.NumberColumn("Traffic System", format="%d"),
    "tr_etc": st.column_config.NumberColumn("Traffic ETC", format="%d"),
    "tr_man": st.column_config.NumberColumn("Traffic Manual", format="%d"),
    "cash_sys": st.column_config.NumberColumn("Cash System", format="%.2f"),
    "etc": st.column_config.NumberColumn("Cash ETC", format="%.2f"),
    "cash_man": st.column_config.NumberColumn("Cash Manual", format="%.2f"),
    "Revenue": st.column_config.NumberColumn("Total Revenue (Br)", format="%.2f"),
    "gen_fuel": st.column_config.NumberColumn("Generator Fuel (L)", format="%.1f"),
    "gen_hour": st.column_config.NumberColumn("Generator Hours", format="%.1f"),
    "gen_operator": st.column_config.TextColumn("Generator Operator"),
    "gen_remark": st.column_config.TextColumn("Generator Remark"),
    "veh_fuel": st.column_config.NumberColumn("Vehicle Fuel (L)", format="%.1f"),
    "veh_odo": st.column_config.NumberColumn("Vehicle Odometer (km)", format="%.1f"),
    "Status": st.column_config.TextColumn("Status"),
}

REPORT_COLS = [
    "Entry", "Exit", "Traffic", "tr_sys", "tr_etc", "tr_man",
    "cash_sys", "etc", "cash_man", "Revenue",
    "gen_fuel", "gen_hour", "gen_operator", "gen_remark",
    "veh_fuel", "veh_odo", "Status",
]


def report_table(df: pd.DataFrame, key: str, selectable: bool = False, show_station: bool = True):
    """Formatted report table. Returns the selection event when selectable."""
    d = with_totals(df)
    cols = ["report_date", "shift"] + (["station"] if show_station else []) + ["supervisor"] + REPORT_COLS
    kwargs = dict(hide_index=True, use_container_width=True, column_config=REPORT_CONFIG, key=key)
    if selectable:
        return st.dataframe(d[cols], on_select="rerun", selection_mode="multi-row", **kwargs)
    st.dataframe(d[cols], **kwargs)
    return None


def problems_section(df: pd.DataFrame):
    issues = df[df["problems"].fillna("").str.strip() != ""]
    st.subheader("⚠️ Problems & solutions")
    if issues.empty:
        st.success("No problems reported in this range.")
        return
    for _, r in issues.iterrows():
        with st.container(border=True):
            st.markdown(f"**🚨 {r['station']}** · {r['report_date']} · Shift {r['shift']}")
            st.write(f"**Problem:** {r['problems']}")
            st.write(f"**Solution:** {r['solution'] or '_No solution recorded_'}")


def confirm_password_rules(new: str, confirm: str):
    if new != confirm:
        return "Passwords don't match"
    if len(new) < MIN_PASSWORD:
        return f"Password must be at least {MIN_PASSWORD} characters"
    return None


# ===================================================================
# LOGIN / ACCOUNT
# ===================================================================
def login_view():
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        header("🚦 Toll Operations", "Shift report system")
        with st.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

        if not submitted:
            return
        username = username.strip()
        if not username or not password:
            st.error("Enter your username and password.")
            return

        if recent_failed_logins(username) >= MAX_FAILED_LOGINS:
            st.error(f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.")
            return

        user = get_user(username=username)
        if user and verify_password(password, user["password_hash"]):
            if not user["is_active"]:
                st.error("🚫 Your account is deactivated. Contact the administrator.")
                log_action((username, user["role"]), "LOGIN_FAILED", "USER", user["id"], username,
                           "Login attempt on deactivated account")
                return
            with db() as conn:
                # Upgrade legacy hash, and force a change if the default admin password is still in use.
                if not user["password_hash"].startswith("pbkdf2$"):
                    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                                 (hash_password(password), user["id"]))
                if password == "admin123":
                    conn.execute("UPDATE users SET must_change_password=1 WHERE id=?", (user["id"],))
            st.session_state["_user_id"] = user["id"]
            log_action((username, user["role"]), "LOGIN", "USER", user["id"], username,
                       f"Logged in from {user['station']}")
            st.rerun()
        else:
            log_action((username, user["role"] if user else None), "LOGIN_FAILED", "USER",
                       user["id"] if user else None, username,
                       "Wrong password" if user else "Unknown username")
            st.error("Invalid username or password")


def force_password_view(user):
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        header("🔐 Set a new password", f"Welcome, {display_name(user)}")
        st.info("For security you must choose a new password before continuing.")
        with st.form("force_pw"):
            new = st.text_input("New password", type="password")
            confirm = st.text_input("Confirm new password", type="password")
            if st.form_submit_button("Save password", type="primary", use_container_width=True):
                err = confirm_password_rules(new, confirm)
                if err:
                    st.error(err)
                elif new == "admin123":
                    st.error("Choose a different password.")
                else:
                    change_password(user["id"], new, (user["username"], user["role"]))
                    flash("Password updated")
                    st.rerun()
        if st.button("Logout"):
            logout(user)


def logout(user):
    log_action((user["username"], user["role"]), "LOGOUT", "USER", user["id"], user["username"], "Logged out")
    for k in ("_user_id", "_user"):
        st.session_state.pop(k, None)
    st.rerun()


def sidebar_footer(user):
    with st.sidebar:
        st.divider()
        st.markdown(f"**{display_name(user)}**")
        st.caption(f"@{user['username']} · 📍 {user['station']}")
        st.caption(ROLE_LABELS.get(user["role"], user["role"]))

        with st.expander("🔑 Change password"):
            with st.form("change_pw", clear_on_submit=True):
                old = st.text_input("Current password", type="password")
                new = st.text_input("New password", type="password")
                confirm = st.text_input("Confirm", type="password")
                if st.form_submit_button("Update", use_container_width=True):
                    if not verify_password(old, user["password_hash"]):
                        st.error("Current password is incorrect")
                    elif (err := confirm_password_rules(new, confirm)):
                        st.error(err)
                    else:
                        change_password(user["id"], new, (user["username"], user["role"]))
                        st.success("Password updated")
        if st.button("🚪 Logout", use_container_width=True):
            logout(user)


# ===================================================================
# SHARED PAGES
# ===================================================================
def dashboard_page():
    user = current_user()
    is_mgr = can_manage(user)
    header("📊 Dashboard", f"Welcome, {user['fname'] or user['username']}", manager=is_mgr)

    c1, c2 = st.columns([2, 1])
    with c1:
        start, end = date_range("dash_range", days=30 if is_mgr else 7)
    station = own_station(user)
    if is_admin(user):
        with c2:
            station = station_filter(user, "dash_station")

    df = get_reports(station=station, start_date=start, end_date=end)
    kpi_row(df)

    if df.empty:
        st.info("No reports in this date range.")
        return

    if is_mgr:
        settled = int(df["is_settled"].sum())
        st.progress(settled / len(df), text=f"🔒 {settled} of {len(df)} shifts settled · "
                                            f"✏️ {len(df) - settled} still open")

    d = with_totals(df)
    daily = d.groupby("report_date")[["Traffic", "Revenue"]].sum().reset_index()
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(daily, x="report_date", y="Traffic", title="Daily traffic",
                     color_discrete_sequence=["#667eea"])
        fig.update_layout(height=320, margin=dict(t=50, b=10), xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(daily, x="report_date", y="Revenue", title="Daily revenue (Br)", markers=True,
                      color_discrete_sequence=["#f5576c"])
        fig.update_layout(height=320, margin=dict(t=50, b=10), xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Reports")
    report_table(df, key="dash_table", show_station=station is None)
    st.download_button("📥 Download CSV", df.to_csv(index=False), "reports.csv", mime="text/csv")


def unpaid_page():
    user = current_user()
    is_mgr = can_manage(user)
    header("🚫 Unpaid Vehicles",
           "Manage unpaid vehicles" if is_mgr else f"Station: {user['station']}", manager=is_mgr)
    list_tab, add_tab = st.tabs(["📋 List", "➕ Add vehicle"])

    with list_tab:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            start, end = date_range("unp_range", days=30)
        with c2:
            status = st.selectbox("Status", ["All", "unpaid", "paid"], key="unp_status")
        station = own_station(user)
        if is_admin(user):
            with c3:
                station = station_filter(user, "unp_station")

        df = get_unpaid(station=station, start_date=start, end_date=end, status=status).reset_index(drop=True)
        if df.empty:
            st.info("No unpaid vehicles found for these filters.")
        else:
            outstanding = df.loc[df["status"] == "unpaid", "amount"]
            m = st.columns(4)
            m[0].metric("Vehicles", len(df))
            m[1].metric("Still unpaid", len(outstanding))
            m[2].metric("Outstanding", f"Br {outstanding.sum():,.2f}")
            m[3].metric("Total amount", f"Br {df['amount'].sum():,.2f}")

            view = df[["report_date", "shift", "station", "vehicle_number", "vehicle_type",
                       "amount", "status", "has_image"]]
            event = st.dataframe(
                view, hide_index=True, use_container_width=True,
                on_select="rerun", selection_mode="single-row", key="unp_table",
                column_config={
                    "report_date": "Date", "shift": st.column_config.TextColumn("Shift", width="small"),
                    "station": "Station", "vehicle_number": "Vehicle",
                    "vehicle_type": st.column_config.TextColumn("Type", width="small"),
                    "amount": st.column_config.NumberColumn("Amount (Br)", format="%.2f"),
                    "status": "Status", "has_image": st.column_config.CheckboxColumn("Photo", width="small"),
                },
            )
            st.caption("Select a row to see details" + (" and take action." if is_mgr else "."))

            rows = event.selection.rows
            if rows:
                row = df.iloc[rows[0]]
                with st.container(border=True):
                    left, right = st.columns([2, 1])
                    with left:
                        st.subheader(f"{row['vehicle_number']} ({row['vehicle_type']})")
                        st.write(f"**Station:** {row['station']} · **Date:** {row['report_date']} · "
                                 f"**Shift:** {row['shift']}")
                        st.write(f"**Supervisor:** {row['supervisor']}")
                        st.write(f"**Amount:** Br {row['amount']:,.2f}")
                        st.write(f"**Reason:** {row['reason'] or 'N/A'}")
                        st.write(f"**Status:** {str(row['status']).upper()}"
                                 + (f" (paid {row['paid_date']}" + (f" by {row['paid_by']}" if row["paid_by"] else "")
                                 + ")" if row["paid_date"] else ""))
                        if is_mgr:
                            b1, b2 = st.columns(2)
                            new_status = "paid" if row["status"] == "unpaid" else "unpaid"
                            if b1.button(f"Mark as {new_status}", key=f"st_{row['id']}", type="primary",
                                         use_container_width=True):
                                set_unpaid_status(int(row["id"]), new_status, actor())
                                flash(f"{row['vehicle_number']} marked {new_status}")
                                st.rerun()
                            if b2.button("🗑️ Delete", key=f"del_{row['id']}", use_container_width=True):
                                confirm_delete_unpaid(int(row["id"]), row["vehicle_number"])
                    with right:
                        if row["has_image"]:
                            show_vehicle_image(int(row["id"]))
                        else:
                            st.caption("📷 No image")

            st.download_button("📥 Download CSV", df.to_csv(index=False), "unpaid_vehicles.csv",
                               mime="text/csv")

    with add_tab:
        with st.form("unpaid_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                number = st.text_input("Vehicle number", placeholder="e.g., AA-1234")
                vtype = st.selectbox("Vehicle type", VEHICLE_TYPES)
                if is_admin(user) or user["station"] == ALL_STATIONS:
                    station_in = st.selectbox("Station", STATIONS)
                else:
                    station_in = user["station"]
                    st.text_input("Station", value=station_in, disabled=True)
            with c2:
                rdate = st.date_input("Date", value=date.today(), max_value=date.today())
                shift = st.selectbox("Shift", SHIFTS)
                amount = st.number_input("Amount (Birr)", min_value=0.0, step=1.0)
            reason = st.text_area("Reason", placeholder="e.g., No card, insufficient balance")
            photo = st.file_uploader("📷 Vehicle photo (optional)", type=["jpg", "jpeg", "png"])

            if st.form_submit_button("➕ Add unpaid vehicle", type="primary", use_container_width=True):
                number = number.strip().upper()
                if not number:
                    st.error("Vehicle number is required.")
                else:
                    image_data, err = (None, None)
                    if photo is not None:
                        image_data, err = process_image(photo)
                    if err:
                        st.error(err)
                    else:
                        add_unpaid(number, vtype, station_in, rdate.isoformat(), shift, amount,
                                   reason.strip(), image_data, actor())
                        flash(f"Unpaid vehicle {number} added")
                        st.rerun()


@st.dialog("Delete unpaid vehicle")
def confirm_delete_unpaid(vehicle_id: int, number: str):
    st.warning(f"Permanently delete **{number}**? This cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("Delete", type="primary", use_container_width=True):
        delete_unpaid(vehicle_id, actor())
        flash(f"{number} deleted", "🗑️")
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


# ===================================================================
# SUPERVISOR PAGES
# ===================================================================
def submit_page():
    user = current_user()
    header("📝 Submit Report", f"Station: {user['station']}")

    if user["station"] == ALL_STATIONS:
        station = st.selectbox("Station", STATIONS)
    else:
        station = user["station"]

    c1, c2 = st.columns(2)
    report_date = c1.date_input("Date", value=date.today(), max_value=date.today()).isoformat()
    shift = c2.selectbox("Shift", SHIFTS)

    existing = get_report(station, report_date, shift)

    if existing and existing["is_settled"] == 1:
        st.markdown(
            "<div class='locked-box'><h3>🔒 Shift settled &amp; locked</h3>"
            "<p>This shift was settled by the manager and can no longer be edited.<br>"
            "Contact your manager if changes are needed.</p></div>",
            unsafe_allow_html=True,
        )
        return

    if existing:
        st.warning(f"A report already exists for this date and shift (last saved {existing['timestamp']}). "
                   "Each tab saves on its own and updates the report until the manager settles it.")
    else:
        st.success("No report yet for this date and shift — fill in any tab and press its Save button.")

    prefix = f"rep_{station}_{report_date}_{shift}"  # fresh widget state per report

    def num(label, field, ph):
        val = existing[field] if existing and existing.get(field) is not None else None
        if field in INT_FIELDS:
            return st.number_input(label, min_value=0, step=1, value=int(val) if val is not None else None,
                                   placeholder=ph, key=f"{prefix}_{field}")
        step = 0.1 if field in ("gen_fuel", "veh_fuel", "veh_odo", "gen_hour") else 0.01
        return st.number_input(label, min_value=0.0, step=step,
                               value=float(val) if val is not None else None,
                               placeholder=ph, key=f"{prefix}_{field}")

    def line(label, field, ph=""):
        return st.text_input(label, value=(existing or {}).get(field) or "", placeholder=ph,
                             key=f"{prefix}_{field}")

    def area(label, field):
        return st.text_area(label, value=(existing or {}).get(field) or "", height=90,
                            key=f"{prefix}_{field}")

    def save_section(title: str, vals: dict):
        clean = {f: ((v or "").strip() if f in TEXT_FIELDS else (v or 0)) for f, v in vals.items()}
        if not existing and not any(clean.values()):
            st.error("Enter at least one value before saving.")
            return
        result = save_partial(station, report_date, shift, user["username"], clean, title, actor())
        if result in ("inserted", "updated"):
            st.success(f"✅ {title} saved.")
            st.toast(f"{title} saved", icon="✅")
        elif result == "settled":
            st.error("🔒 This shift was just settled by the manager. You cannot edit it.")
        else:
            st.error("❌ Could not save. Please try again.")

    # Each tab is its own form with its own save button (no st.rerun, so the selected tab stays put).
    tabs = st.tabs(["🚗 Traffic", "💰 Cash", "🧾 Thermal Paper", "⚡ Generator",
                    "⛽ Vehicle Fuel", "📝 Notes"])

    with tabs[0]:
        with st.form(f"{prefix}_f_traffic"):
            v = {}
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Exit**")
                v["exit_sys"] = num("System", "exit_sys", "0")
                v["exit_etc"] = num("ETC", "exit_etc", "0")
                v["exit_man"] = num("Manual", "exit_man", "0")
            with c2:
                st.markdown("**Entry**")
                v["entry_sys"] = num("System", "entry_sys", "0")
                v["entry_etc"] = num("ETC", "entry_etc", "0")
                v["entry_man"] = num("Manual", "entry_man", "0")
            go = st.form_submit_button("💾 Save traffic", type="primary", use_container_width=True)
        if go:
            save_section("Traffic", v)

    with tabs[1]:
        with st.form(f"{prefix}_f_cash"):
            v = {}
            c1, c2 = st.columns(2)
            with c1:
                v["cash_sys"] = num("Cash — system", "cash_sys", "Amount")
                v["cash_man"] = num("Cash — manual", "cash_man", "Amount")
            with c2:
                v["etc"] = num("ETC collection", "etc", "Amount")
            go = st.form_submit_button("💾 Save cash", type="primary", use_container_width=True)
        if go:
            save_section("Cash", v)

    with tabs[2]:
        with st.form(f"{prefix}_f_thermal"):
            v = {}
            c1, c2 = st.columns(2)
            with c1:
                v["thermal_exit"] = num("Exit lanes — rolls", "thermal_exit", "Rolls")
            with c2:
                v["thermal_entry"] = num("Entry lanes — rolls", "thermal_entry", "Rolls")
            go = st.form_submit_button("💾 Save thermal paper", type="primary", use_container_width=True)
        if go:
            save_section("Thermal paper", v)

    with tabs[3]:
        with st.form(f"{prefix}_f_gen"):
            v = {}
            c1, c2 = st.columns(2)
            with c1:
                v["gen_fuel"] = num("Fuel (litres)", "gen_fuel", "Litres")
                v["gen_operator"] = line("Operator name (who gave the fuel)", "gen_operator", "Full name")
            with c2:
                v["gen_hour"] = num("Generator hour meter", "gen_hour", "Hours")
                v["gen_remark"] = line("Remark", "gen_remark", "Optional")
            go = st.form_submit_button("💾 Save generator", type="primary", use_container_width=True)
        if go:
            save_section("Generator", v)

    with tabs[4]:
        with st.form(f"{prefix}_f_veh"):
            v = {}
            c1, c2 = st.columns(2)
            with c1:
                v["veh_fuel"] = num("Fuel (litres)", "veh_fuel", "Litres")
            with c2:
                v["veh_odo"] = num("Odometer (km)", "veh_odo", "Reading")
            go = st.form_submit_button("💾 Save vehicle fuel", type="primary", use_container_width=True)
        if go:
            save_section("Vehicle fuel", v)

    with tabs[5]:
        with st.form(f"{prefix}_f_notes"):
            v = {
                "good_notes": area("Good things", "good_notes"),
                "problems": area("Problems", "problems"),
                "solution": area("Solution", "solution"),
            }
            go = st.form_submit_button("💾 Save notes", type="primary", use_container_width=True)
        if go:
            save_section("Notes", v)


def my_reports_page():
    user = current_user()
    header("📋 My Reports", f"All reports for {user['station']}")
    start, end = date_range("my_range", days=30)
    df = get_reports(station=own_station(user), start_date=start, end_date=end)
    if df.empty:
        st.info("No reports in this date range.")
        return
    report_table(df, key="my_table", show_station=own_station(user) is None)
    st.download_button("📥 Download CSV", df.to_csv(index=False), "my_reports.csv", mime="text/csv")
    st.divider()
    problems_section(df)


# ===================================================================
# MANAGER PAGES
# ===================================================================
def reports_page():
    user = current_user()
    header("📈 Reports", "All station reports", manager=True)
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        start, end = date_range("rep_range")
    station = station_filter(user, "rep_station", container=c2) or ALL_STATIONS
    shift = c3.selectbox("Shift", ["All"] + SHIFTS, key="rep_shift")
    status = c4.selectbox("Status", ["All", "Settled", "Open"], key="rep_status")

    df = get_reports(station=None if station == ALL_STATIONS else station,
                     shift=None if shift == "All" else shift, start_date=start, end_date=end)
    if status != "All":
        df = df[df["is_settled"] == (1 if status == "Settled" else 0)]
    if df.empty:
        st.info("No reports found.")
        return

    report_table(df, key="rep_table")
    st.download_button("📥 Download CSV (all columns)", df.to_csv(index=False), "reports.csv",
                       mime="text/csv")
    st.divider()
    problems_section(df)


def settle_page():
    user = current_user()
    header("🔒 Settle Shifts", "Lock shifts so supervisors can no longer edit them", manager=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        start, end = date_range("settle_range", days=7)
    station = station_filter(user, "settle_station", container=c2) or ALL_STATIONS

    df = get_reports(station=None if station == ALL_STATIONS else station,
                     start_date=start, end_date=end).reset_index(drop=True)
    if df.empty:
        st.info("No reports found for these filters.")
        return

    settled = int(df["is_settled"].sum())
    m = st.columns(3)
    m[0].metric("Total", len(df))
    m[1].metric("🔒 Settled", settled)
    m[2].metric("✏️ Open", len(df) - settled)

    st.caption("Select one or more rows, then settle or unsettle them.")
    event = report_table(df, key="settle_table", selectable=True)
    picked = df.iloc[event.selection.rows] if event and event.selection.rows else df.iloc[0:0]

    b1, b2, b3 = st.columns(3)
    to_settle = picked[picked["is_settled"] == 0]
    to_unsettle = picked[picked["is_settled"] == 1]
    if b1.button(f"🔒 Settle selected ({len(to_settle)})", disabled=to_settle.empty,
                 type="primary", use_container_width=True):
        n = set_settled(to_settle["id"].tolist(), True, actor())
        flash(f"Settled {n} report(s)", "🔒")
        st.rerun()
    if b2.button(f"🔓 Unsettle selected ({len(to_unsettle)})", disabled=to_unsettle.empty,
                 use_container_width=True):
        n = set_settled(to_unsettle["id"].tolist(), False, actor())
        flash(f"Unsettled {n} report(s)", "🔓")
        st.rerun()
    open_ids = df.loc[df["is_settled"] == 0, "id"].tolist()
    if b3.button(f"⚡ Settle all open ({len(open_ids)})", disabled=not open_ids, use_container_width=True):
        confirm_settle_all(open_ids)


@st.dialog("Settle all open shifts")
def confirm_settle_all(ids):
    st.warning(f"This will lock **{len(ids)}** shift report(s) in the current filter.")
    c1, c2 = st.columns(2)
    if c1.button("Settle all", type="primary", use_container_width=True):
        n = set_settled(ids, True, actor())
        flash(f"Settled {n} report(s)", "🔒")
        st.rerun()
    if c2.button("Cancel", use_container_width=True):
        st.rerun()


def analytics_page():
    user = current_user()
    header("📊 Analytics", "Charts & comparisons", manager=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        start, end = date_range("ana_range")
    station = station_filter(user, "ana_station", container=c2) or ALL_STATIONS
    df = get_reports(station=None if station == ALL_STATIONS else station, start_date=start, end_date=end)
    if df.empty:
        st.info("No data available.")
        return

    d = with_totals(df)
    kpi_row(df)
    st.divider()

    by_station = d.groupby("station")[["Traffic", "Revenue"]].sum().reset_index()
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(by_station, x="station", y="Traffic", color="station", title="Traffic by station",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False, height=340, xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(by_station, x="station", y="Revenue", color="station", title="Revenue by station (Br)",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False, height=340, xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        lanes = {
            "System": df["exit_sys"].sum() + df["entry_sys"].sum(),
            "ETC": df["exit_etc"].sum() + df["entry_etc"].sum(),
            "Manual": df["exit_man"].sum() + df["entry_man"].sum(),
        }
        if sum(lanes.values()) > 0:
            fig = px.pie(values=list(lanes.values()), names=list(lanes.keys()), hole=0.45,
                         title="Traffic by lane type",
                         color_discrete_sequence=["#667eea", "#4CAF50", "#FF9800"])
            fig.update_layout(height=340)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        pay = {"Cash": df["cash_sys"].sum() + df["cash_man"].sum(), "ETC": df["etc"].sum()}
        if sum(pay.values()) > 0:
            fig = px.pie(values=list(pay.values()), names=list(pay.keys()), hole=0.45,
                         title="Revenue by payment type", color_discrete_sequence=["#667eea", "#f093fb"])
            fig.update_layout(height=340)
            st.plotly_chart(fig, use_container_width=True)

    by_shift = d.groupby(["station", "shift"])["Revenue"].sum().reset_index()
    fig = px.bar(by_shift, x="station", y="Revenue", color="shift", barmode="group",
                 title="Revenue by station and shift", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(height=340, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    daily = d.groupby("report_date")[["Traffic", "Revenue"]].sum().reset_index()
    fig = px.line(daily, x="report_date", y=["Traffic", "Revenue"], markers=True, title="Daily trends",
                  color_discrete_sequence=["#667eea", "#f5576c"])
    fig.update_layout(height=340, xaxis_title=None, legend_title=None)
    st.plotly_chart(fig, use_container_width=True)


def consolidated_page():
    header("📋 Consolidated Report", "Summary by station", manager=True)
    start, end = date_range("cons_range")
    df = get_reports(station=own_station(current_user()), start_date=start, end_date=end)
    if df.empty:
        st.info("No data available.")
        return

    d = with_totals(df)
    summary = d.groupby("station").agg(
        Reports=("id", "count"), Entry=("Entry", "sum"), Exit=("Exit", "sum"),
        Traffic=("Traffic", "sum"), TrSys=("tr_sys", "sum"), TrEtc=("tr_etc", "sum"),
        TrMan=("tr_man", "sum"), CashSys=("cash_sys", "sum"), CashEtc=("etc", "sum"),
        CashMan=("cash_man", "sum"), Revenue=("Revenue", "sum"),
        GenFuel=("gen_fuel", "sum"), VehFuel=("veh_fuel", "sum"),
    ).reset_index()
    total = summary.drop(columns="station").sum().to_frame().T
    total.insert(0, "station", "TOTAL")
    summary = pd.concat([summary, total], ignore_index=True)

    n = lambda label, fmt="%d": st.column_config.NumberColumn(label, format=fmt)
    st.dataframe(
        summary, hide_index=True, use_container_width=True,
        column_config={
            "station": "Station", "Entry": n("Entry"), "Exit": n("Exit"), "Traffic": n("Total Traffic"),
            "TrSys": n("Traffic System"), "TrEtc": n("Traffic ETC"), "TrMan": n("Traffic Manual"),
            "CashSys": n("Cash System", "%.2f"), "CashEtc": n("Cash ETC", "%.2f"),
            "CashMan": n("Cash Manual", "%.2f"), "Revenue": n("Total Revenue (Br)", "%.2f"),
            "GenFuel": n("Generator Fuel (L)", "%.1f"), "VehFuel": n("Vehicle Fuel (L)", "%.1f"),
        },
    )
    st.download_button("📥 Download CSV", summary.to_csv(index=False), "consolidated.csv", mime="text/csv")

    st.subheader("Revenue by station and shift")
    pivot = d.pivot_table(index="station", columns="shift", values="Revenue", aggfunc="sum",
                          fill_value=0, margins=True, margins_name="Total")
    st.dataframe(pivot, use_container_width=True,
                 column_config={c: st.column_config.NumberColumn(format="%.2f") for c in pivot.columns})


def by_station(df: pd.DataFrame, columns: dict) -> pd.DataFrame:
    """Sum the given {label: column} per station (all stations listed), with a TOTAL row."""
    order = STATIONS + [x for x in df["station"].unique() if x not in STATIONS]
    g = df.groupby("station")[list(columns.values())].sum().reindex(order, fill_value=0)
    g.columns = list(columns.keys())
    if len(columns) > 1:
        g["Total"] = g.sum(axis=1)
    g = g.reset_index().rename(columns={"station": "Station"})
    total = g.drop(columns="Station").sum().to_frame().T
    total.insert(0, "Station", "TOTAL")
    return pd.concat([g, total], ignore_index=True)


def station_report(df: pd.DataFrame, key: str, title: str, columns: dict, unit: str, fmt: str = "%d"):
    table = by_station(df, columns)
    st.dataframe(
        table, hide_index=True, use_container_width=True,
        column_config={c: st.column_config.NumberColumn(c, format=fmt)
                       for c in table.columns if c != "Station"},
    )
    body = table[table["Station"] != "TOTAL"]
    parts = list(columns.keys())
    if len(parts) == 1:
        fig = px.bar(body, x="Station", y=parts[0], color="Station", title=f"{title} ({unit})",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(showlegend=False)
    else:
        long = body.melt(id_vars="Station", value_vars=parts, var_name="Type", value_name=unit)
        fig = px.bar(long, x="Station", y=unit, color="Type", barmode="stack", title=title,
                     color_discrete_sequence=["#667eea", "#4CAF50", "#FF9800"])
    fig.update_layout(height=340, xaxis_title=None, margin=dict(t=50, b=10))
    st.plotly_chart(fig, use_container_width=True, key=f"{key}_chart")
    st.download_button("📥 Download CSV", table.to_csv(index=False), f"{key}.csv", mime="text/csv",
                       key=f"{key}_dl")


def station_reports_page():
    header("🏢 Station Reports", "Entry, exit, fuel and paper totals by station", manager=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        start, end = date_range("sr_range")
    shift = c2.selectbox("Shift", ["All"] + SHIFTS, key="sr_shift")
    df = get_reports(station=own_station(current_user()), start_date=start, end_date=end,
                     shift=None if shift == "All" else shift)
    if df.empty:
        st.info("No reports in this date range.")
        return

    tabs = st.tabs(["⬇️ Entry Traffic", "⬇️ Entry by Type", "⬆️ Exit Traffic", "⬆️ Exit by Type",
                    "⚡ Generator Fuel", "⛽ Vehicle Fuel", "🧾 Exit Paper", "🧾 Entry Paper"])
    by_type = lambda side: {"System": f"{side}_sys", "ETC": f"{side}_etc", "Manual": f"{side}_man"}

    with tabs[0]:
        d = df.assign(entry_total=df["entry_sys"] + df["entry_etc"] + df["entry_man"])
        station_report(d, "entry_traffic", "Entry traffic flow by station",
                       {"Entry traffic": "entry_total"}, "vehicles")
    with tabs[1]:
        station_report(df, "entry_by_type", "Entry traffic flow by system, manual and ETC",
                       by_type("entry"), "vehicles")
    with tabs[2]:
        d = df.assign(exit_total=df["exit_sys"] + df["exit_etc"] + df["exit_man"])
        station_report(d, "exit_traffic", "Exit traffic flow by station",
                       {"Exit traffic": "exit_total"}, "vehicles")
    with tabs[3]:
        station_report(df, "exit_by_type", "Exit traffic flow by system, manual and ETC",
                       by_type("exit"), "vehicles")
    with tabs[4]:
        station_report(df, "generator_fuel", "Generator fuel by station",
                       {"Generator fuel (L)": "gen_fuel"}, "litres", "%.1f")
    with tabs[5]:
        station_report(df, "vehicle_fuel", "Vehicle fuel by station",
                       {"Vehicle fuel (L)": "veh_fuel"}, "litres", "%.1f")
    with tabs[6]:
        station_report(df, "exit_paper", "Exit thermal paper by station",
                       {"Exit paper (rolls)": "thermal_exit"}, "rolls")
    with tabs[7]:
        station_report(df, "entry_paper", "Entry thermal paper by station",
                       {"Entry paper (rolls)": "thermal_entry"}, "rolls")


def make_backup_bytes() -> bytes:
    """Consistent snapshot of the live database (safe while users are working)."""
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src = sqlite3.connect(DB_FILE, timeout=30)
        dst = sqlite3.connect(tmp_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def backup_page():
    user = current_user()
    header("💾 Database Backup", "Download a full copy of the database", manager=True)
    if not is_admin(user):
        st.error("Only a Super Admin can download backups.")
        return

    with db() as conn:
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("users", "reports", "unpaid_vehicles", "audit_log")}
    size_mb = os.path.getsize(DB_FILE) / (1024 * 1024) if os.path.exists(DB_FILE) else 0
    m = st.columns(5)
    m[0].metric("Database size", f"{size_mb:,.2f} MB")
    m[1].metric("Users", f"{counts['users']:,}")
    m[2].metric("Reports", f"{counts['reports']:,}")
    m[3].metric("Unpaid vehicles", f"{counts['unpaid_vehicles']:,}")
    m[4].metric("Audit entries", f"{counts['audit_log']:,}")

    st.warning("A backup contains every user, report and photo, including password hashes. "
               "Store it somewhere safe and do not share it.")

    if st.button("🗄️ Create backup now", type="primary"):
        try:
            data = make_backup_bytes()
            name = f"toll_operations_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
            st.session_state["_backup"] = (name, data, now_str())
            log_action(actor(), "BACKUP_CREATE", "DATABASE", None, name,
                       f"Created database backup ({len(data) / 1024 / 1024:,.2f} MB)")
        except (sqlite3.Error, OSError) as e:
            st.error(f"Backup failed: {e}")

    backup = st.session_state.get("_backup")
    if backup:
        name, data, created = backup
        st.success(f"Backup ready: **{name}** ({len(data) / 1024 / 1024:,.2f} MB), created {created}.")
        st.download_button(
            "📥 Download backup", data=data, file_name=name, mime="application/octet-stream",
            type="primary",
            on_click=lambda: log_action(actor(), "BACKUP_DOWNLOAD", "DATABASE", None, name,
                                        "Downloaded database backup"),
        )
    st.caption("To restore: stop the app, replace toll_operations.db with the backup file, and start the app again.")


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")


def validate_user_fields(fname, lname, username, exclude_id=None):
    errors = []
    f, l, u = fname.strip(), lname.strip(), username.strip()
    if not f:
        errors.append("First name is required")
    if not l:
        errors.append("Last name is required")
    if not USERNAME_RE.match(u):
        errors.append("Username must be 3–30 characters: letters, numbers, dot, dash or underscore")
    if f and l and f.lower() == l.lower():
        errors.append("First name and last name must be different")
    if u.lower() in (f.lower(), l.lower()):
        errors.append("Username must be different from first and last name")
    if USERNAME_RE.match(u) and username_taken(u, exclude_id):
        errors.append(f"Username '{u}' already exists")
    return errors


def users_page():
    me = current_user()
    header("👥 User Management", "Create, edit, activate or deactivate users", manager=True)
    list_tab, add_tab, edit_tab = st.tabs(["📋 All users", "➕ Add user", "✏️ Edit user"])

    with list_tab:
        df = get_all_users()
        active = int((df["is_active"] == 1).sum())
        m = st.columns(4)
        m[0].metric("Total", len(df))
        m[1].metric("🟢 Active", active)
        m[2].metric("🔴 Inactive", len(df) - active)
        m[3].metric("👑 / 🏢 / 🛡️", f"{(df['role'] == ROLE_ADMIN).sum()} / "
                                   f"{(df['role'] == ROLE_STATION).sum()} / {(df['role'] == ROLE_SUPERVISOR).sum()}",
                    help="Super Admins / Station Managers / Supervisors")

        view = df.assign(
            Name=(df["fname"] + " " + df["lname"]).str.strip(),
            Status=df["is_active"].map({1: "🟢 Active", 0: "🔴 Inactive"}),
            Role=df["role"].map(ROLE_LABELS).fillna(df["role"]),
        )[["Name", "username", "station", "Role", "Status", "created_at"]]
        event = st.dataframe(
            view, hide_index=True, use_container_width=True, on_select="rerun",
            selection_mode="single-row", key="users_table",
            column_config={"username": "Username", "station": "Station", "created_at": "Created"},
        )
        rows = event.selection.rows
        if rows:
            sel = df.iloc[rows[0]]
            is_self = int(sel["id"]) == me["id"]
            with st.container(border=True):
                st.write(f"**{sel['fname']} {sel['lname']}** (@{sel['username']})")
                if sel["is_active"]:
                    if st.button("🔴 Deactivate", disabled=is_self,
                                 help="You can't deactivate your own account." if is_self else None):
                        ok, msg = set_user_active(int(sel["id"]), False, actor())
                        flash(msg, "✅" if ok else "❌")
                        st.rerun()
                else:
                    if st.button("🟢 Activate", type="primary"):
                        ok, msg = set_user_active(int(sel["id"]), True, actor())
                        flash(msg, "✅" if ok else "❌")
                        st.rerun()
        else:
            st.caption("Select a user to activate or deactivate them.")
        st.download_button("📥 Download users", df.to_csv(index=False), "users.csv", mime="text/csv")

    with add_tab:
        st.caption("New users must choose their own password at first login.")
        ROLE_HELP = {
            ROLE_SUPERVISOR: "Submits shift reports for their station and adds unpaid vehicles.",
            ROLE_STATION: "Views reports and analytics, settles shifts and manages unpaid vehicles "
                          "for ONE station.",
            ROLE_ADMIN: "Full access to all stations, users and the audit log.",
        }
        # Role is chosen outside the form so the Station field can react to it.
        role = st.radio("Role", list(ROLE_LABELS), format_func=ROLE_LABELS.get, horizontal=True,
                        key="new_user_role")
        st.info(ROLE_HELP[role])

        with st.form("add_user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                fname = st.text_input("First name", placeholder="e.g., Abebe")
                lname = st.text_input("Last name", placeholder="e.g., Kebede")
                username = st.text_input("Username", placeholder="e.g., abebe.k")
            with c2:
                password = st.text_input("Temporary password", type="password",
                                         placeholder=f"Min {MIN_PASSWORD} characters")
                if role == ROLE_ADMIN:
                    station = ALL_STATIONS
                    st.text_input("Station", value=ALL_STATIONS, disabled=True)
                elif role == ROLE_STATION:
                    station = st.selectbox("Station (the one they manage)", STATIONS)
                else:
                    station = st.selectbox("Station", STATIONS + [ALL_STATIONS],
                                           help="Pick 'All Stations' to let the supervisor choose "
                                                "the station on each report.")
            if st.form_submit_button(f"➕ Create {ROLE_LABELS[role].split(' ', 1)[1]}", type="primary",
                                     use_container_width=True):
                errors = validate_user_fields(fname, lname, username)
                if len(password) < MIN_PASSWORD:
                    errors.append(f"Password must be at least {MIN_PASSWORD} characters")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    ok, msg = create_user(fname.strip(), lname.strip(), username.strip(), password,
                                          station, role, actor())
                    if ok:
                        flash(f"{ROLE_LABELS[role]} @{username.strip()} created", "🎉")
                        st.rerun()
                    else:
                        st.error(msg)

    with edit_tab:
        df = get_all_users()
        labels = {f"{r.fname} {r.lname} (@{r.username})": int(r.id) for r in df.itertuples()}
        choice = st.selectbox("Select user", list(labels.keys()))
        uid = labels[choice]
        u = get_user(user_id=uid)
        is_self = uid == me["id"]
        if is_self:
            st.info("This is your own account — username and role can't be changed here.")

        with st.form(f"edit_user_{uid}"):
            c1, c2 = st.columns(2)
            with c1:
                n_f = st.text_input("First name", value=u["fname"])
                n_l = st.text_input("Last name", value=u["lname"])
                n_u = st.text_input("Username", value=u["username"], disabled=is_self)
            with c2:
                stations = STATIONS + [ALL_STATIONS]
                n_s = st.selectbox("Station", stations,
                                   index=stations.index(u["station"]) if u["station"] in stations else 0)
                roles = list(ROLE_LABELS)
                n_r = st.selectbox("Role", roles, index=roles.index(u["role"]) if u["role"] in roles else 0,
                                   format_func=ROLE_LABELS.get, disabled=is_self)
            n_pw = st.text_input("Reset password (optional)", type="password",
                                 placeholder="Leave empty to keep the current password")
            if st.form_submit_button("💾 Save changes", type="primary", use_container_width=True):
                errors = validate_user_fields(n_f, n_l, u["username"] if is_self else n_u, exclude_id=uid)
                if n_pw and len(n_pw) < MIN_PASSWORD:
                    errors.append(f"Password must be at least {MIN_PASSWORD} characters")
                if (u["role"] if is_self else n_r) == ROLE_STATION and n_s == ALL_STATIONS:
                    errors.append("A Station Manager must be assigned to one specific station")
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    ok, msg = update_user(uid, n_f.strip(), n_l.strip(),
                                          u["username"] if is_self else n_u.strip(), n_s,
                                          u["role"] if is_self else n_r, n_pw or None, actor())
                    if ok:
                        flash(msg)
                        st.rerun()
                    else:
                        st.error(msg)


ACTION_ICONS = [
    ("BACKUP", "💾"),
    ("LOGIN_FAILED", "⚠️"), ("LOGIN", "🔑"), ("LOGOUT", "🚪"), ("CHANGE_PASSWORD", "🔐"),
    ("UNSETTLE", "🔓"), ("SETTLE", "🔒"), ("DEACTIVATE", "⛔"), ("ACTIVATE", "✅"),
    ("DELETE", "🗑️"), ("CREATE", "➕"), ("UPDATE", "✏️"),
]
AUDIT_ACTIONS = [
    "LOGIN", "LOGOUT", "LOGIN_FAILED", "CREATE_USER", "UPDATE_USER", "ACTIVATE_USER", "DEACTIVATE_USER",
    "CHANGE_PASSWORD", "CREATE_REPORT", "UPDATE_REPORT", "SETTLE_REPORT", "UNSETTLE_REPORT",
    "CREATE_UNPAID", "UPDATE_UNPAID_STATUS", "DELETE_UNPAID", "BACKUP_CREATE", "BACKUP_DOWNLOAD",
]


def action_label(action: str) -> str:
    for key, icon in ACTION_ICONS:
        if action.startswith(key) or action.endswith(key) or key in action:
            return f"{icon} {action}"
    return f"ℹ️ {action}"


def audit_log_page():
    header("📋 Audit Log", "All system activity", manager=True)
    c1, c2, c3 = st.columns([1, 1, 2])
    username = c1.text_input("Username", placeholder="All users").strip() or None
    action = c2.selectbox("Action", ["All"] + AUDIT_ACTIONS)
    with c3:
        start, end = date_range("log_range", days=7)
    limit = st.slider("Max entries", 50, 2000, 300, step=50)

    df = get_audit_log(limit=limit, username=username, action=None if action == "All" else action,
                       start_date=start, end_date=end)
    if df.empty:
        st.info("No log entries for these filters.")
        return

    m = st.columns(4)
    m[0].metric("Entries", len(df))
    m[1].metric("Unique users", df["username"].nunique())
    m[2].metric("Action types", df["action"].nunique())
    m[3].metric("⚠️ Failed logins", int((df["action"] == "LOGIN_FAILED").sum()))

    view = df.assign(Action=df["action"].map(action_label))[
        ["timestamp", "username", "role", "Action", "target_name", "details", "station"]]
    st.dataframe(
        view, hide_index=True, use_container_width=True, height=520,
        column_config={
            "timestamp": "When", "username": "User", "role": "Role",
            "target_name": "Target", "details": st.column_config.TextColumn("Details", width="large"),
            "station": "Station",
        },
    )
    st.download_button("📥 Download CSV", df.to_csv(index=False),
                       f"audit_log_{datetime.now():%Y%m%d_%H%M%S}.csv", mime="text/csv")


# ===================================================================
# MAIN
# ===================================================================
def build_pages(user):
    P = st.Page
    dash = P(dashboard_page, title="Dashboard", icon="📊", url_path="dashboard", default=True)
    unpaid = P(unpaid_page, title="Unpaid Vehicles", icon="🚫", url_path="unpaid")
    if is_admin(user):
        return {
            "Overview": [
                dash,
                P(analytics_page, title="Analytics", icon="📈", url_path="analytics"),
                P(consolidated_page, title="Consolidated", icon="📋", url_path="consolidated"),
                P(station_reports_page, title="Station Reports", icon="🏢", url_path="station-reports"),
            ],
            "Operations": [
                P(reports_page, title="Reports", icon="🗂️", url_path="reports"),
                P(settle_page, title="Settle Shifts", icon="🔒", url_path="settle"),
                unpaid,
            ],
            "Admin": [
                P(users_page, title="Users", icon="👥", url_path="users"),
                P(audit_log_page, title="Audit Log", icon="🧾", url_path="audit"),
                P(backup_page, title="Database Backup", icon="💾", url_path="backup"),
            ],
        }
    if user["role"] in (ROLE_STATION, ROLE_ADMIN):  # ROLE_ADMIN here = tied to one station
        return {
            "Overview": [
                dash,
                P(analytics_page, title="Analytics", icon="📈", url_path="analytics"),
                P(consolidated_page, title="Consolidated", icon="📋", url_path="consolidated"),
                P(station_reports_page, title="Station Reports", icon="🏢", url_path="station-reports"),
            ],
            "Operations": [
                P(reports_page, title="Reports", icon="🗂️", url_path="reports"),
                P(settle_page, title="Settle Shifts", icon="🔒", url_path="settle"),
                unpaid,
            ],
        }
    return [
        dash,
        P(submit_page, title="Submit Report", icon="📝", url_path="submit"),
        P(my_reports_page, title="My Reports", icon="📋", url_path="my-reports"),
        unpaid,
    ]


def main():
    init_once()
    user = current_user()
    if user is None:
        login_view()
        show_flash()
        return
    if user["must_change_password"]:
        force_password_view(user)
        return

    nav = st.navigation(build_pages(user))
    sidebar_footer(user)
    show_flash()
    nav.run()
    st.caption("© 2026 Toll Operations Manager")


main()