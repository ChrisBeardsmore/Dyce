import sqlite3
from datetime import datetime

def get_connection(db_path="dyce.db"):
    return sqlite3.connect(db_path)

def get_memory(conn, app=None):
    sql = "SELECT * FROM gpt_memory"
    if app:
        sql += " WHERE app = ? ORDER BY timestamp DESC"
        return conn.execute(sql, (app,)).fetchall()
    return conn.execute(sql + " ORDER BY timestamp DESC").fetchall()

def log_gpt_note(app, message):
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gpt_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app TEXT,
            timestamp TEXT,
            user TEXT,
            message TEXT
        )
    """)
    conn.execute(
        "INSERT INTO gpt_memory (app, timestamp, user, message) VALUES (?, ?, ?, ?)",
        (app, datetime.utcnow().isoformat(), "GPT", message)
    )
    conn.commit()
