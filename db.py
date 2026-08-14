import sqlite3

DB_PATH = 'budget.db'


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()

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
        CREATE TABLE IF NOT EXISTS user_sheet (
            user_id TEXT,
            sheet_id TEXT,
            cycle_id INTEGER,
            PRIMARY KEY (user_id, sheet_id)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS cycles (
            cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            sheet_id TEXT,
            tab_name TEXT,
            start_date TEXT,
            end_date TEXT
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS cycle_income (
            cycle_id INTEGER,
            name TEXT,
            amount REAL,
            PRIMARY KEY (cycle_id, name)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS cycle_savings (
            cycle_id INTEGER,
            name TEXT,
            amount REAL,
            PRIMARY KEY (cycle_id, name)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS cycle_debt (
            cycle_id INTEGER,
            debt_id INTEGER,
            debt_name TEXT,
            amount REAL,
            PRIMARY KEY (cycle_id, debt_name)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS cycle_expense (
            cycle_id INTEGER,
            category TEXT,
            amount REAL,
            PRIMARY KEY (cycle_id, category)
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS debt (
            debt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            debt_name TEXT,
            amount REAL,
            amount_left_to_pay REAL
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


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def save_user(user_id, email, access_token, refresh_token, token_expiry):
    conn = get_connection()
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
    conn = get_connection()
    cursor = conn.execute(
        'SELECT id, email, access_token, refresh_token, token_expiry FROM users WHERE id = ?',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return {"id": row[0], "email": row[1], "access_token": row[2], "refresh_token": row[3], "token_expiry": row[4]}


# ---------------------------------------------------------------------------
# User <-> Sheet, and Cycles
# ---------------------------------------------------------------------------

def set_user_sheet(user_id, sheet_id):
    conn = get_connection()
    conn.execute('''
        INSERT INTO user_sheet (user_id, sheet_id, cycle_id)
        VALUES (?, ?, NULL)
        ON CONFLICT(user_id, sheet_id) DO NOTHING
    ''', (user_id, sheet_id))
    conn.commit()
    conn.close()


def get_sheet_id(user_id):
    conn = get_connection()
    cursor = conn.execute('SELECT sheet_id FROM user_sheet WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return row[0]


def set_current_tab(user_id, sheet_id, cycle_id):
    conn = get_connection()
    conn.execute('''
        INSERT INTO user_sheet (user_id, sheet_id, cycle_id)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, sheet_id) DO UPDATE SET
            cycle_id = excluded.cycle_id
    ''', (user_id, sheet_id, cycle_id))
    conn.commit()
    conn.close()


def get_current_tab(user_id, sheet_id):
    conn = get_connection()
    cursor = conn.execute('''
        SELECT cycles.tab_name,cycles.cycle_id
        FROM user_sheet
        JOIN cycles ON cycles.cycle_id = user_sheet.cycle_id
        WHERE user_sheet.user_id = ? AND user_sheet.sheet_id = ?
    ''', (user_id, sheet_id))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return {'tab_name':row[0],'cycle_id':row[1]}


def get_current_tab_valid_until(user_id, sheet_id):
    conn = get_connection()
    cursor = conn.execute('''
        SELECT cycles.end_date
        FROM user_sheet
        JOIN cycles ON cycles.cycle_id = user_sheet.cycle_id
        WHERE user_sheet.user_id = ? AND user_sheet.sheet_id = ?
    ''', (user_id, sheet_id))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return row[0]


def get_current_cycle(user_id, sheet_id):
    """Convenience helper: one query for cycle_id, tab_name, start_date, and end_date together."""
    conn = get_connection()
    cursor = conn.execute('''
        SELECT cycles.cycle_id, cycles.tab_name, cycles.start_date, cycles.end_date
        FROM user_sheet
        JOIN cycles ON cycles.cycle_id = user_sheet.cycle_id
        WHERE user_sheet.user_id = ? AND user_sheet.sheet_id = ?
    ''', (user_id, sheet_id))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None
    return {"cycle_id": row[0], "tab_name": row[1], "start_date": row[2], "end_date": row[3]}


def add_cycle(user_id, sheet_id, start_date, end_date, tab_name):
    conn = get_connection()
    cursor = conn.execute('''
        INSERT INTO cycles (user_id, sheet_id, start_date, end_date, tab_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, sheet_id, start_date, end_date, tab_name))
    cycle_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cycle_id


def update_cycle(cycle_id, start_date, end_date, tab_name):
    conn = get_connection()
    conn.execute('''
        UPDATE cycles SET
            start_date = ?,
            end_date = ?,
            tab_name = ?
        WHERE cycle_id = ?
    ''', (start_date, end_date, tab_name, cycle_id))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Cycle income / savings / debt / expense (all keyed by cycle_id)
# ---------------------------------------------------------------------------

def set_cycle_income(cycle_id, name, amount):
    conn = get_connection()
    conn.execute('''
        INSERT INTO cycle_income (cycle_id, name, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(cycle_id, name) DO UPDATE SET
            amount = excluded.amount
    ''', (cycle_id, name, amount))
    conn.commit()
    conn.close()


def get_cycle_income(cycle_id):
    conn = get_connection()
    cursor = conn.execute('SELECT name, amount FROM cycle_income WHERE cycle_id = ?', (cycle_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"name": row[0], "amount": row[1]} for row in rows]


def delete_cycle_income(cycle_id, name) :
    conn = get_connection()
    conn.execute('''
        DELETE FROM cycle_income 
        WHERE cycle_id = ? AND name = ?
    ''', (cycle_id, name))
    conn.commit()
    conn.close()


def set_cycle_savings(cycle_id, name, amount):
    conn = get_connection()
    conn.execute('''
        INSERT INTO cycle_savings (cycle_id, name, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(cycle_id, name) DO UPDATE SET
            amount = excluded.amount
    ''', (cycle_id, name, amount))
    conn.commit()
    conn.close()


def get_cycle_savings(cycle_id):
    conn = get_connection()
    cursor = conn.execute('SELECT name, amount FROM cycle_savings WHERE cycle_id = ?', (cycle_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"name": row[0], "amount": row[1]} for row in rows]


def delete_cycle_savings(cycle_id, name) :
    conn = get_connection()
    conn.execute('''
        DELETE FROM cycle_savings 
        WHERE cycle_id = ? AND name = ?
    ''', (cycle_id, name))
    conn.commit()
    conn.close()


def set_cycle_debt(cycle_id, debt_id, debt_name, amount):
    conn = get_connection()
    conn.execute('''
        INSERT INTO cycle_debt (cycle_id, debt_id, debt_name, amount)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(cycle_id, debt_name) DO UPDATE SET
            amount = excluded.amount
    ''', (cycle_id, debt_id, debt_name, amount))
    conn.commit()
    conn.close()


def get_cycle_debt(cycle_id):
    conn = get_connection()
    cursor = conn.execute(
        'SELECT debt_id, debt_name, amount FROM cycle_debt WHERE cycle_id = ?',
        (cycle_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"debt_id": row[0], "name": row[1], "amount": row[2]} for row in rows]


def set_cycle_expense(cycle_id, category, amount):
    conn = get_connection()
    conn.execute('''
        INSERT INTO cycle_expense (cycle_id, category, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(cycle_id, category) DO UPDATE SET
            amount = amount + excluded.amount
    ''', (cycle_id, category, amount))
    conn.commit()
    conn.close()


def get_cycle_expense(cycle_id):
    conn = get_connection()
    cursor = conn.execute('SELECT category, amount FROM cycle_expense WHERE cycle_id = ?', (cycle_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"category": row[0], "amount": row[1]} for row in rows]


# ---------------------------------------------------------------------------
# Debt (persistent, across cycles)
# ---------------------------------------------------------------------------

def add_debt(user_id, debt_name, amount, amount_left_to_pay):
    conn = get_connection()
    cursor = conn.execute('''
        INSERT INTO debt (user_id, debt_name, amount, amount_left_to_pay)
        VALUES (?, ?, ?, ?)
    ''', (user_id, debt_name, amount, amount_left_to_pay))
    debt_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return debt_id


def update_debt(user_id, debt_id, amount, amount_left_to_pay):
    conn = get_connection()
    conn.execute('''
        UPDATE debt SET
            amount = ?,
            amount_left_to_pay = ?
        WHERE user_id = ? AND debt_id = ?
    ''', (amount, amount_left_to_pay, user_id, debt_id))
    conn.commit()
    conn.close()


def delete_debt(user_id, debt_id):
    conn = get_connection()
    conn.execute('DELETE FROM debt WHERE user_id = ? AND debt_id = ?', (user_id, debt_id))
    conn.commit()
    conn.close()


def get_debts(user_id):
    conn = get_connection()
    cursor = conn.execute(
        'SELECT debt_id, debt_name, amount, amount_left_to_pay FROM debt WHERE user_id = ?',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"debt_id": row[0], "debt_name": row[1], "amount": row[2], "amount_left_to_pay": row[3]}
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def set_category(user_id, category):
    conn = get_connection()
    conn.execute('''
        INSERT INTO user_categories (user_id, category)
        VALUES (?, ?)
        ON CONFLICT(user_id, category) DO NOTHING
    ''', (user_id, category))
    conn.commit()
    conn.close()


def delete_category(user_id, category):
    conn = get_connection()
    conn.execute('DELETE FROM user_categories WHERE user_id = ? AND category = ?', (user_id, category))
    conn.commit()
    conn.close()


def get_categories(user_id):
    conn = get_connection()
    cursor = conn.execute('SELECT category FROM user_categories WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# Bills
# ---------------------------------------------------------------------------

def set_bill(user_id, bill_name, amount):
    conn = get_connection()
    conn.execute('''
        INSERT INTO user_bills (user_id, bill_name, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, bill_name) DO UPDATE SET
            amount = excluded.amount
    ''', (user_id, bill_name, amount))
    conn.commit()
    conn.close()


def delete_bill(user_id, bill_name):
    conn = get_connection()
    conn.execute('DELETE FROM user_bills WHERE user_id = ? AND bill_name = ?', (user_id, bill_name))
    conn.commit()
    conn.close()


def get_bills(user_id):
    conn = get_connection()
    cursor = conn.execute('SELECT bill_name, amount FROM user_bills WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"bill_name": row[0], "amount": row[1]} for row in rows]


def sync_bills(user_id, bills):
    submitted_names = [b['name'] for b in bills]

    # upsert each submitted bill
    for bill in bills:
        set_bill(user_id, bill['name'], bill['amount'])

    # delete any saved bill NOT in the submitted list
    existing = get_bills(user_id)
    for existing_bill in existing:
        if existing_bill['bill_name'] not in submitted_names:
            delete_bill(user_id, existing_bill['bill_name'])



# ---------------------------------------------------------------------------
# Help functions
# ---------------------------------------------------------------------------


def get_all_user_sheets():
    conn = get_connection()
    cursor = conn.execute('SELECT user_id, sheet_id FROM user_sheet')
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": row[0], "sheet_id": row[1]} for row in rows]