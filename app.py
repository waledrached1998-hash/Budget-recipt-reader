from functools import wraps

from flask import Flask, request, send_from_directory, redirect, session

import auth
import claude_client as cc
import config as c
import sheets as s
from db import (
    init_db,
    get_categories, set_category, delete_category,
    get_bills, set_bill, delete_bill, sync_bills,
    set_current_tab,
    get_current_tab,
    update_cycle,
    get_current_cycle,
    delete_cycle_income,
    delete_cycle_savings
)

app = Flask(__name__, static_folder='public')
app.secret_key = c.FLASK_SECRET_KEY
init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Static assets / PWA
# ---------------------------------------------------------------------------

@app.route('/manifest.json')
def manifest():
    return send_from_directory('public', 'manifest.json', mimetype='application/manifest+json')


@app.route('/sw.js')
def service_worker():
    return send_from_directory('public', 'sw.js', mimetype='application/javascript')


@app.route('/icons/<path:filename>')
def icons(filename):
    return send_from_directory('public/icons', filename)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route('/')
def hello():
    if 'user_id' not in session:
        return send_from_directory('public', 'login.html')
    return send_from_directory('public', 'index.html')


@app.route('/settings')
@login_required
def settings_page():
    return send_from_directory('public', 'settings.html')


@app.route('/cycle')
@login_required
def cycle_page():
    return send_from_directory('public', 'cycle.html')


@app.route('/manage-bills')
@login_required
def manage_bills_page():
    return send_from_directory('public', 'manage-bills.html')


# ---------------------------------------------------------------------------
# Auth (Google Sign-In)
# ---------------------------------------------------------------------------

@app.route('/login')
def login():
    login_url, code_verifier = auth.get_login_url()
    session['code_verifier'] = code_verifier
    return redirect(login_url)


@app.route('/auth/callback')
def auth_callback():
    code_verifier = session.get('code_verifier')
    user_id, email = auth.handle_callback(request.url, code_verifier)
    session['user_id'] = user_id
    session['email'] = email

    existing_sheet_id = s.get_user_sheet_id(user_id)
    if existing_sheet_id is None:
        user_drive_service = s.get_user_drive_service(user_id)
        new_sheet_id = s.create_user_sheet(c.sheet_id, email, user_drive_service)
        s.seed_default_categories(user_id)
        s.save_user_sheet(user_id, new_sheet_id)

    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------------------------------------------------------------------
# Monthly cycle: create / status
# ---------------------------------------------------------------------------

@app.route('/month-exists')
@login_required
def month_exists():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    still_valid = s.get_current_tab_still_valid(user_id, sheet_id)
    return {"exists": still_valid}


@app.route('/cycle-status')
@login_required
def cycle_status():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    if sheet_id is None:
        return {"error": "No active sheet found."}, 400

    is_active = s.get_current_tab_still_valid(user_id, sheet_id)
    return {"active": is_active}


@app.route('/new-month', methods=["POST"])
@login_required
def new_month():
    request_json = request.json
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    sheets_service = s.get_user_sheets_service(user_id)
    new_tab_name = s.get_next_tab_name(request_json)

    if new_tab_name is None:
        return {"error": "Could not determine next month name"}, 400
    if s.does_tab_exist(new_tab_name, sheets_service, sheet_id):
        return {"status": "already exists"}, 400

    cycle_id = s.duplicate_template_tab(request_json, new_tab_name, sheets_service, sheet_id, user_id)
    s.write_income(request_json, new_tab_name, sheets_service, sheet_id,cycle_id)
    s.write_savings(request_json, new_tab_name, sheets_service, sheet_id,cycle_id)
    s.write_date(request_json, new_tab_name, sheets_service, sheet_id)

    if request_json.get('modify_bills'):
        sync_bills(user_id, request_json['bills'])

    bills = get_bills(user_id)
    s.write_bills({"bills": bills}, new_tab_name, sheets_service, sheet_id)

    return {"status": "created"}


# ---------------------------------------------------------------------------
# Current cycle: dates
# ---------------------------------------------------------------------------

@app.route('/current-cycle/dates', methods=["GET"])
@login_required
def get_current_cycle_dates():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = get_current_tab(user_id, sheet_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    cycle = get_current_cycle(user_id,sheet_id)

    return {'start_date':cycle['start_date'],'end_date':cycle['end_date']}


@app.route('/current-cycle/dates', methods=["POST"])
@login_required
def update_current_dates():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    s.write_date(request.json, tab['tab_name'], sheets_service, sheet_id)
    update_cycle(tab['cycle_id'],request.json['start_date'],request.json['end_date'],tab['tab_name'])
    return {"status": "Updated"}


# ---------------------------------------------------------------------------
# Current cycle: income
# ---------------------------------------------------------------------------

@app.route('/current-cycle/income', methods=["GET"])
@login_required
def get_current_cycle_income():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    income = s.get_current_income(tab['cycle_id'])
    return {"income": income}


@app.route('/current-cycle/income/add', methods=["POST"])
@login_required
def add_income():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found."}, 400
    income = request.json['income']
    existing = s.get_current_income(tab['cycle_id'])
    for e in existing :
        if e['name'] == income['name'] :
            return {"error": "You can't add the same income twice"}, 400

    s.write_income({"income": [income]},tab['tab_name'],sheets_service,sheet_id,tab['cycle_id'])
    return {"status": "added"}


@app.route('/current-cycle/income/remove', methods=["POST"])
@login_required
def remove_income():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    entry = request.json['income']
    delete_cycle_income(tab['cycle_id'],entry['name'])
    existing = s.get_current_income(tab['cycle_id'])
    s.replace_income(existing, tab['tab_name'], sheets_service, sheet_id)
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Current cycle: savings
# ---------------------------------------------------------------------------

@app.route('/current-cycle/savings', methods=["GET"])
@login_required
def get_current_cycle_savings():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    savings = s.get_current_savings(tab['cycle_id'])
    return {"savings": savings}


@app.route('/current-cycle/savings/add', methods=["POST"])
@login_required
def add_saving():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    savings = request.json['savings']
    existing = s.get_current_savings(tab['cycle_id'])
    for e in existing :
        if e['name'] == savings['name'] :
            return {"error": "You can't add the same saving twice"}, 400
        
    s.write_savings({"savings": [savings]},tab['tab_name'],sheets_service,sheet_id,tab['cycle_id'])
    return {"status": "added"}


@app.route('/current-cycle/savings/remove', methods=["POST"])
@login_required
def remove_saving():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found."}, 400

    entry = request.json['savings']
    delete_cycle_savings(tab['cycle_id'],entry['name'])
    existing = s.get_current_savings(tab['cycle_id'])
    s.replace_savings(existing,tab['tab_name'], sheets_service, sheet_id)
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Receipts: scan, review, confirm
# ---------------------------------------------------------------------------

@app.route('/scan-receipt', methods=["POST"])
@login_required
def scan_receipt():
    if 'receipt' not in request.files:
        return {"error": "No file was attached"}, 400

    file = request.files['receipt']

    if not file.mimetype.startswith('image/'):
        return {"error": "The attached file is not an image"}, 400

    try:
        parsed = cc.scan_receipt_image(file, session['user_id'])
    except Exception as e:
        print(f"Error scanning receipt: {e}")
        return {"error": "Couldn't read that receipt. Please try again."}, 400

    if not parsed['is_receipt']:
        return {"error": "The photo that you have uploaded is not of a reciept"}, 400

    return {"status": "parsed", "data": parsed}


@app.route('/confirm-receipt', methods=["POST"])
@login_required
def confirm_receipt():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab = s.get_current_tab(user_id, sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab is None:
        return {"error": "No active month found. Please create a new month first."}, 400

    parsed = request.json
    s.write_expenses(parsed, tab['tab_name'], sheets_service, sheet_id,tab['cycle_id'])
    return {"status": "received"}


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.route('/categories', methods=["GET"])
@login_required
def list_categories():
    categories = get_categories(session['user_id'])
    return {"categories": categories}


@app.route('/categories/add', methods=["POST"])
@login_required
def add_category():
    user_id = session['user_id']
    set_category(user_id, request.json['category'])
    sheet_id = s.get_user_sheet_id(user_id)
    sheets_service = s.get_user_sheets_service(user_id)
    s.sync_categories_to_sheet(user_id, sheets_service, sheet_id)
    return {"status": "added"}


@app.route('/categories/remove', methods=["POST"])
@login_required
def remove_category():
    user_id = session['user_id']
    delete_category(user_id, request.json['category'])
    sheet_id = s.get_user_sheet_id(user_id)
    sheets_service = s.get_user_sheets_service(user_id)
    s.sync_categories_to_sheet(user_id, sheets_service, sheet_id)
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Bills
# ---------------------------------------------------------------------------

@app.route('/bills', methods=["GET"])
@login_required
def list_bills():
    bills = get_bills(session['user_id'])
    return {"bills": bills}


@app.route('/bills/add', methods=["POST"])
@login_required
def add_bill():
    user_id = session['user_id']
    data = request.json
    bill = data['bill']

    set_bill(user_id, bill['name'], bill['amount'])

    if data.get('apply_to_current_month'):
        sheet_id = s.get_user_sheet_id(user_id)
        tab = s.get_current_tab(user_id, sheet_id)
        sheets_service = s.get_user_sheets_service(user_id)
        if tab is not None:
            s.write_bills({"bills": [bill]}, tab['tab_name'], sheets_service, sheet_id)

    return {"status": "added"}


@app.route('/bills/remove', methods=["POST"])
@login_required
def remove_bill():
    user_id = session['user_id']
    bill = request.json['bill']
    delete_bill(user_id, bill['name'])
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

@app.route('/my-sheet-url')
@login_required
def my_sheet_url():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)

    if sheet_id is None:
        return {"error": "No active sheet found."}, 400

    return {"url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)