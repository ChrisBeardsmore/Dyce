import sqlite3

def get_connection(db_path="dyce.db"):
    return sqlite3.connect(db_path)

def create_table(conn, create_sql):
    with conn:
        conn.execute(create_sql)

def insert_row(conn, table, data_dict):
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join(['?'] * len(data_dict))
    values = tuple(data_dict.values())
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    with conn:
        conn.execute(sql, values)
        
def select_all(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table}")
    return cursor.fetchall()   

from sqlite_utils import get_connection, create_memory_table, log_gpt_memory, get_memory

conn = get_connection()
create_memory_table(conn)  # Set up the table if it doesn't exist

# Log a message
log_gpt_memory(conn, app="gas", message="Updated margin logic in gpricebook.py")

# View recent logs
logs = get_memory(conn, app="gas")
for row in logs:
    print(row)
