from flask import Flask, request, send_from_directory, redirect, session
import sheets as s
import claude_client as cc
from db import init_db
import auth

app = Flask(__name__, static_folder='public')
init_db()

@app.route('/')
def hello():
    return send_from_directory('public', 'index.html')

@app.route('/login')
def login():
    return redirect(auth.get_login_url())

@app.route('/auth/callback')
def auth_callback():
    user_id, email = auth.handle_callback(request.url)
    session['user_id'] = user_id
    session['email'] = email
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/month-exists')
def month_exists():
    still_valid = s.get_current_tab_still_valid()
    return {"exists": still_valid}


@app.route('/new-month', methods=["POST"])
def new_month():
    request_json = request.json
    new_sheet_name = s.get_next_tab_name(request_json)

    if new_sheet_name is None:
        return {"error": "Could not determine next month name"}, 400
    if s.does_tab_exist(new_sheet_name):
        return {"status": "already exists"}, 400

    s.duplicate_template_tab(request_json,new_sheet_name)
    s.write_income(request_json, new_sheet_name)
    s.write_savings(request_json, new_sheet_name)
    s.write_date(request_json, new_sheet_name)
    return {"status": "created"}


@app.route('/scan-receipt', methods=["POST"])
def scan_receipt():
    tab_name = s.get_current_tab()
    if tab_name is None:
        return {"error": "No active month found. Please create a new month first."}, 400
    
    file = request.files['receipt']
    parsed = cc.scan_receipt_image(file)
    s.write_expenses(parsed, tab_name)
    return {"status": "received"}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)