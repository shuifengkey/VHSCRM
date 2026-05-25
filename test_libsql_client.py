import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("TURSO_DATABASE_URL")
auth_token = os.environ.get("TURSO_AUTH_TOKEN")

print("URL", db_url)

import libsql_client

class LibSQLCursorWrapper:
    def __init__(self, rs):
        self.rs = rs
        self._idx = 0
    def fetchone(self):
        if self._idx < len(self.rs.rows):
            row = self.rs.rows[self._idx]
            self._idx += 1
            return dict(zip(self.rs.columns, row))
        return None
    def fetchall(self):
        return [dict(zip(self.rs.columns, row)) for row in self.rs.rows]

class LibSQLConnectionWrapper:
    def __init__(self, url, token):
        self.client = libsql_client.create_client_sync(url=url, auth_token=token)
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
        self.client.close()

conn = LibSQLConnectionWrapper(db_url, auth_token)
print(conn.execute("SELECT * FROM users LIMIT 1").fetchone())
