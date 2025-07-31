import sqlite3

def get_connection(db_path="dyce.db"):
    return sqlite3.connect(db_path)

def create_table(conn, create_sql):
    cursor = conn.cursor()
    cursor.execute(create_sql)
    conn.commit()

def insert_row(conn, table, data_dict):
    columns = ', '.join(data_dict.keys())
    placeholders = ', '.join('?' * len(data_dict))
    values = tuple(data_dict.values())
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    conn.execute(sql, values)
    conn.commit()
