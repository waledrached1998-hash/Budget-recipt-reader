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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry TEXT
        )
    ''')
    conn.execute(''' 
        CREATE TABLE IF NOT EXISTS user_categories (
            user_id TEXT,
            category TEXT,
            PRIMARY KEY (user_id, category)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS user_bills (
            user_id TEXT,
            bill_name TEXT,
            amount REAL,
            PRIMARY KEY (user_id, bill_name)
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


def set_user_sheet(user_id, sheet_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO user_sheet (user_id, sheet_id)
        VALUES (?, ?)
        ON CONFLICT(user_id, sheet_id) DO UPDATE SET
            current_tab_name = excluded.current_tab_name,
            valid_until = excluded.valid_until
    ''', (user_id, sheet_id,))
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

def save_user(user_id, email, access_token, refresh_token, token_expiry):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO users (id, email, access_token, refresh_token, token_expiry)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            email = excluded.email,
            access_token = excluded.access_token,
            refresh_token = excluded.refresh_token,
            token_expiry = excluded.token_expiry
    ''', (user_id, email, access_token, refresh_token, token_expiry))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('SELECT id, email, access_token, refresh_token, token_expiry FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "access_token": row[2], "refresh_token": row[3], "token_expiry": row[4]}

def get_sheet_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
            SELECT sheet_id FROM user_sheet
            WHERE user_id = ? 
        ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return row[0]

def get_categories(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
            SELECT category FROM user_categories
            WHERE user_id = ? 
        ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def get_bills(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('''
            SELECT 
                bill_name,
                amount
            FROM user_bills
            WHERE user_id = ? 
        ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"bill_name": row[0], "amount": row[1]} for row in rows]



def set_category(user_id,category):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO user_categories (user_id,category)
        VALUES (?, ?)
    ''', (user_id, category))
    conn.commit()
    conn.close()

def delete_category(user_id, category):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        DELETE FROM user_categories WHERE user_id = ? AND category = ?
    ''', (user_id, category))
    conn.commit()
    conn.close()

def set_bill(user_id, bill_name, amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO user_bills (user_id, bill_name, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, bill_name) DO UPDATE SET
            amount = excluded.amount
    ''', (user_id, bill_name, amount))
    conn.commit()
    conn.close()


def delete_bill(user_id, bill_name):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        DELETE FROM user_bills
        WHERE user_id = ? AND bill_name = ?
    ''', (user_id, bill_name))
    conn.commit()
    conn.close()

def sync_bills(user_id, bills):
    submitted_names = [b['name'] for b in bills]

    # step 1: upsert each submitted bill
    for bill in bills:
        set_bill(user_id, bill['name'], bill['amount'])

    # step 2: delete any saved bill NOT in the submitted list
    existing = get_bills(user_id)
    for existing_bill in existing:
        if existing_bill['bill_name'] not in submitted_names:
            delete_bill(user_id, existing_bill['bill_name'])