import sqlite3

DB_PATH = 'budget.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_sheet (
            user_id TEXT,
            sheet_id TEXT,
            current_tab_name TEXT,
            valid_until TEXT,
            PRIMARY KEY (user_id, sheet_id)
        )
    ''')
    conn.commit()
    conn.close()


def set_current_tab(user_id, sheet_id, tab_name, valid_until):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO user_sheet (user_id, sheet_id, current_tab_name, valid_until)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, sheet_id) DO UPDATE SET
            current_tab_name = excluded.current_tab_name,
            valid_until = excluded.valid_until
    ''', (user_id, sheet_id, tab_name, valid_until))
    conn.commit()
    conn.close()


def get_current_tab(user_id, sheet_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
        SELECT current_tab_name FROM user_sheet
        WHERE user_id = ? AND sheet_id = ?
    ''', (user_id, sheet_id))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return row[0]


def get_current_tab_valid_until(user_id, sheet_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
        SELECT valid_until FROM user_sheet
        WHERE user_id = ? AND sheet_id = ?
    ''', (user_id, sheet_id))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return row[0]