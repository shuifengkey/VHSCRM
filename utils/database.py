# utils/database.py — VHS CRM v4
import sqlite3, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vhs_crm.db")

try:
    import streamlit as st
except ImportError:
    st = None

class RowProxy:
    def __init__(self, columns, row):
        self._columns = columns
        self._row = row
        self._dict = dict(zip(columns, row))
    def __getitem__(self, key):
        if isinstance(key, int): return self._row[key]
        return self._dict[key]
    def keys(self):
        return self._dict.keys()
    def get(self, key, default=None):
        return self._dict.get(key, default)

class LibSQLCursorWrapper:
    def __init__(self, rs):
        self.rs = rs
        self._idx = 0
    def fetchone(self):
        if self._idx < len(self.rs.rows):
            row = self.rs.rows[self._idx]
            self._idx += 1
            return RowProxy(self.rs.columns, row)
        return None
    def fetchall(self):
        return [RowProxy(self.rs.columns, row) for row in self.rs.rows]

def _get_turso_client(url, token):
    import libsql_client
    return libsql_client.create_client_sync(url=url, auth_token=token)

if st:
    _get_turso_client = st.cache_resource(_get_turso_client)

class LibSQLConnectionWrapper:
    def __init__(self, url, token):
        self.client = _get_turso_client(url, token)
    def cursor(self):
        return self
    def execute(self, sql, parameters=()):
        rs = self.client.execute(sql, parameters)
        return LibSQLCursorWrapper(rs)
    def executemany(self, sql, parameters_list):
        for params in parameters_list:
            self.client.execute(sql, params)
    def commit(self):
        pass
    def close(self):
        # Bỏ qua close để tái sử dụng client (tăng tốc độ)
        pass

def get_connection():
    db_url = None
    auth_token = None
    
    if st:
        try:
            db_url = st.secrets.get("TURSO_DATABASE_URL")
            auth_token = st.secrets.get("TURSO_AUTH_TOKEN")
        except Exception:
            pass
            
    if not db_url:
        db_url = os.environ.get("TURSO_DATABASE_URL", "https://vhs-crm-shuifengkey.aws-ap-northeast-1.turso.io")
    if not auth_token:
        auth_token = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3Nzk3MjE1OTIsImlkIjoiMDE5ZTVmYWItYTMwMS03NDI0LWJkMDEtYjQxYWFkMDY3YjJlIiwicmlkIjoiOGUxZDI1YmUtM2VkYy00MGE2LWFiM2QtYjRmYTMzNGNjMGRlIn0.quHMJF0JlPiFzRP3m50uR9YJE5ec3zm-644ZWp3gJfayzUpxCLBwnpqCY6fKr1MN7TCVjcBOOUn_BZRlZpIXBw")
        
    if db_url:
        try:
            return LibSQLConnectionWrapper(db_url, auth_token)
        except ImportError:
            pass # Fallback
            
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _do_init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS technicians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_ktv TEXT UNIQUE NOT NULL,
        ten TEXT NOT NULL,
        sdt TEXT,
        active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_kh      TEXT UNIQUE NOT NULL,
        ten_cty    TEXT NOT NULL,
        dai_dien   TEXT,
        sdt        TEXT,
        dia_chi    TEXT,
        phan_khuc  TEXT DEFAULT 'Nhà hàng',
        ghi_chu    TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # HỢP ĐỒNG — các trường lịch lặp:
    # ngay_thi_cong_dau : ngày thi công ĐẦU TIÊN (do user setup, khác ngày ký)
    # gio_bat_dau / gio_ket_thuc : giờ cố định cho HĐ này (HH:MM)
    # tan_suat   : 1/2/3/4 lần/tháng
    # kieu_lap   : 'ngay_co_dinh' | 'thu_co_dinh'
    #   - ngay_co_dinh: lặp lại vào đúng ngày đó tháng sau (VD: ngày 5 mỗi tháng)
    #   - thu_co_dinh : lặp lại vào thứ X tuần Y (VD: thứ Hai đầu tiên mỗi tháng)
    # lap_thu    : 0=CN,1=T2,...,6=T7 (chỉ dùng khi thu_co_dinh)
    c.execute("""CREATE TABLE IF NOT EXISTS contracts (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_hd               TEXT UNIQUE NOT NULL,
        ma_kh               TEXT NOT NULL,
        ngay_ky             TEXT NOT NULL,
        ngay_het_han        TEXT,
        ngay_thi_cong_dau   TEXT NOT NULL,
        gio_bat_dau         TEXT NOT NULL,
        gio_ket_thuc        TEXT NOT NULL,
        tan_suat            INTEGER DEFAULT 1,
        kieu_lap            TEXT DEFAULT 'ngay_co_dinh',
        lap_thu             INTEGER,
        gia_tri_thang       REAL DEFAULT 0,
        don_vi_tinh         TEXT DEFAULT '/tháng',
        loai_khach          TEXT DEFAULT 'Định kỳ',
        chu_ky_lap          TEXT,
        tuan_lap_lai        TEXT,
        khu_vuc_xu_ly       TEXT,
        loai_con_trung      TEXT,
        phuong_phap_xu_ly   TEXT,
        ky_thuat_vien       TEXT,
        trang_thai          TEXT DEFAULT 'active',
        ghi_chu             TEXT,
        nguon               TEXT DEFAULT 'auto',
        FOREIGN KEY (ma_kh) REFERENCES customers(ma_kh)
    )""")

    # LỊCH THI CÔNG — mỗi row = 1 buổi thi công cụ thể
    c.execute("""CREATE TABLE IF NOT EXISTS schedules (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_hd         TEXT NOT NULL,
        ma_kh         TEXT NOT NULL,
        ky_thang      TEXT NOT NULL,    -- YYYY-MM
        lan_thu       INTEGER NOT NULL, -- 1,2,3,4
        ngay_du_kien  TEXT NOT NULL,    -- YYYY-MM-DD
        gio_bat_dau   TEXT NOT NULL,    -- HH:MM
        gio_ket_thuc  TEXT NOT NULL,    -- HH:MM
        trang_thai    TEXT DEFAULT 'scheduled',
        nguon         TEXT DEFAULT 'auto',
        ky_thuat_vien TEXT,
        ghi_chu       TEXT,
        loai_con_trung TEXT,
        phuong_phap_xu_ly TEXT,
        google_event_id TEXT,
        UNIQUE(ma_hd, ky_thang, lan_thu),
        FOREIGN KEY (ma_hd) REFERENCES contracts(ma_hd)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logbook (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        schedule_id    INTEGER NOT NULL UNIQUE,
        ma_kh          TEXT NOT NULL,
        ky_thuat_vien  TEXT,
        checkin_time   TEXT,
        checkout_time  TEXT,
        hoa_chat       TEXT,
        ket_qua        TEXT,
        canh_bao_gio   INTEGER DEFAULT 0,
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS debts (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_hd         TEXT NOT NULL,
        ma_kh         TEXT NOT NULL,
        ky_thanh_toan TEXT NOT NULL,
        can_thu       REAL DEFAULT 0,
        da_thu        REAL DEFAULT 0,
        ngay_thu      TEXT,
        ghi_chu       TEXT,
        UNIQUE(ma_hd, ky_thanh_toan),
        FOREIGN KEY (ma_hd) REFERENCES contracts(ma_hd)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS uploads (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_kh         TEXT,
        file_name     TEXT,
        file_path     TEXT,
        uploaded_at   TEXT DEFAULT (datetime('now','localtime'))
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_name TEXT UNIQUE NOT NULL,
        value_data TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_hd TEXT,
        ma_kh TEXT NOT NULL,
        ky_thang TEXT NOT NULL,
        so_hoa_don TEXT,
        ngay_xuat TEXT,
        gia_truoc_vat REAL DEFAULT 0,
        vat_pct REAL DEFAULT 0,
        tien_vat REAL DEFAULT 0,
        tong_tien REAL DEFAULT 0,
        trang_thai TEXT DEFAULT 'Chưa xuất'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ngay_chi TEXT NOT NULL,
        loai_chi_phi TEXT NOT NULL,
        so_tien REAL DEFAULT 0,
        nguoi_chi TEXT,
        ghi_chu TEXT,
        ma_hd TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    # --- Auto Migration for existing databases ---
    try: c.execute("ALTER TABLE customers ADD COLUMN nguoi_lien_he TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE customers ADD COLUMN ten_phap_ly TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE customers ADD COLUMN ma_so_thue TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE customers ADD COLUMN dia_chi_phap_ly TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE customers ADD COLUMN lat REAL")
    except Exception: pass
    try: c.execute("ALTER TABLE customers ADD COLUMN lng REAL")
    except Exception: pass
    
    try: c.execute("ALTER TABLE contracts ADD COLUMN vat_pct REAL DEFAULT 0")
    except Exception: pass
    try: c.execute("ALTER TABLE debts ADD COLUMN tien_vat REAL DEFAULT 0")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN don_vi_tinh TEXT DEFAULT '/tháng'")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN loai_khach TEXT DEFAULT 'Định kỳ'")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN khu_vuc_xu_ly TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN loai_con_trung TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE schedules ADD COLUMN ky_thuat_vien TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN tuan_lap_lai TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE schedules ADD COLUMN loai_con_trung TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE schedules ADD COLUMN google_event_id TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE schedules ADD COLUMN phuong_phap_xu_ly TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE logbook ADD COLUMN attachments TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE logbook ADD COLUMN ket_qua TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE logbook ADD COLUMN hoa_chat TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE contracts ADD COLUMN ky_thuat_vien TEXT")
    except Exception: pass
    try: c.execute("ALTER TABLE technicians ADD COLUMN pin TEXT")
    except Exception: pass
    
    # --- Database Indexes for Performance Optimization ---
    try: c.execute("CREATE INDEX IF NOT EXISTS idx_schedules_ngay ON schedules(ngay_du_kien)")
    except Exception: pass
    try: c.execute("CREATE INDEX IF NOT EXISTS idx_schedules_ktv ON schedules(ky_thuat_vien)")
    except Exception: pass
    try: c.execute("CREATE INDEX IF NOT EXISTS idx_schedules_makh ON schedules(ma_kh)")
    except Exception: pass
    try: c.execute("CREATE INDEX IF NOT EXISTS idx_contracts_makh ON contracts(ma_kh)")
    except Exception: pass
    try: c.execute("CREATE INDEX IF NOT EXISTS idx_logbook_schedule ON logbook(schedule_id)")
    except Exception: pass
    
    conn.commit()
    conn.close()

if st:
    @st.cache_data
    def _run_init_db_once():
        _do_init_db()
else:
    def _run_init_db_once():
        _do_init_db()

def init_db():
    _run_init_db_once()

def seed_demo_data():
    conn = get_connection()
    if conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] > 0:
        conn.close(); return
    # Removed mock data auto-generation as per user request
    conn.commit()
    conn.close()
