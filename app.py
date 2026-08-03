from flask import Flask, request, send_from_directory, redirect, session
import sheets as s
import claude_client as cc
import config as c
from db import init_db
import auth

app = Flask(__name__, static_folder='public')
app.secret_key = c.FLASK_SECRET_KEY
init_db()

@app.route('/')
def hello():
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
        drive_service = s.get_user_drive_service(user_id)
        new_sheet_id = s.create_user_sheet(c.sheet_id, drive_service, email)
        s.save_user_sheet(user_id,new_sheet_id)
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/month-exists')
def month_exists():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    still_valid = s.get_current_tab_still_valid(user_id,sheet_id)
    return {"exists": still_valid}


@app.route('/new-month', methods=["POST"])
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
def scan_receipt():
    user_id = session['user_id']
    sheet_id = s.get_user_sheet_id(user_id)
    tab_name = s.get_current_tab(user_id,sheet_id)
    sheets_service = s.get_user_sheets_service(user_id)
    if tab_name is None:
        return {"error": "No active month found. Please create a new month first."}, 400
    
    file = request.files['receipt']
    parsed = cc.scan_receipt_image(file)
    s.write_expenses(parsed, tab_name,sheets_service,sheet_id)
    return {"status": "received"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)