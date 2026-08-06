from flask import Flask, request, send_from_directory, redirect, session
from functools import wraps
import sheets as s
import claude_client as cc
import config as c
from db import init_db
import auth

app = Flask(__name__, static_folder='public')
app.secret_key = c.FLASK_SECRET_KEY
init_db()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper

@app.route('/')
def hello():
    if 'user_id' not in session:
        return send_from_directory('public', 'login.html')
    return send_from_directory('public', 'index.html')

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
        s.save_user_sheet(user_id, new_sheet_id)
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/month-exists')
@login_required
def month_exists():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    still_valid = s.get_current_tab_still_valid(user_id,sheet_id)
    return {"exists": still_valid}


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
    if s.does_tab_exist(new_tab_name,sheets_service,sheet_id):
        return {"status": "already exists"}, 400

    s.duplicate_template_tab(request_json,new_tab_name,sheets_service,sheet_id,user_id)
    s.write_income(request_json, new_tab_name,sheets_service,sheet_id)
    s.write_savings(request_json, new_tab_name,sheets_service,sheet_id)
    s.write_date(request_json, new_tab_name,sheets_service,sheet_id)
    return {"status": "created"}


@app.route('/scan-receipt', methods=["POST"])
@login_required
def scan_receipt():

    if 'receipt' not in request.files :
        return {"error": "No file was attached"}, 400
    
    file = request.files['receipt']

    if not file.mimetype.startswith('image/'):
        return {"error": "The attached file is not an image"}, 400

    try :
        parsed = cc.scan_receipt_image(file)
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
    tab_name = s.get_current_tab(user_id,sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab_name is None:
        return {"error": "No active month found. Please create a new month first."}, 400
    
    parsed = request.json

    s.write_expenses(parsed, tab_name,sheets_service,sheet_id)
    return {"status": "received"}

@app.route('/my-sheet-url')
@login_required
def my_sheet_url():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)

    if sheet_id is None :
        return {"error": "No active sheet found."}, 400

    return {"url": f"https://docs.google.com/spreadsheets/d/{sheet_id}"}


@app.route('/cycle-status')
@login_required
def cycle_status():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    if sheet_id is None :
            return {"error": "No active sheet found."}, 400
    
    is_active = s.get_current_tab_still_valid(user_id,sheet_id)
    
    return {"active": is_active}
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)