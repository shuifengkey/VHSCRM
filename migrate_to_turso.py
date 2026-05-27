import os
import sys
import sqlite3

# Thêm đường dẫn hiện tại vào sys.path


from utils.database import init_db, get_connection

def main():
    print("Initializing Turso DB structure...")
    # Vì đã có .streamlit/secrets.toml, get_connection() sẽ tự động dùng Turso
    init_db()
    print("Turso DB structure created successfully!")

    # Lấy dữ liệu từ file local
    print("Migrating data from local vhs_crm.db to Turso...")
    local_conn = sqlite3.connect("vhs_crm.db")
    local_conn.row_factory = sqlite3.Row
    turso_conn = get_connection()

    tables = ["technicians", "customers", "contracts", "schedules", "logbook", "debts"]
    for table in tables:
        rows = local_conn.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            continue
        print(f"Migrating {len(rows)} rows for table {table}...")
        columns = rows[0].keys()
        placeholders = ",".join(["?"] * len(columns))
        col_names = ",".join(columns)
        
        insert_sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        for r in rows:
            try:
                turso_conn.execute(insert_sql, tuple(r))
            except Exception as e:
                print(f"Error inserting into {table}: {e}")
                
    turso_conn.commit()
    print("Migration complete!")

if __name__ == "__main__":
    main()
