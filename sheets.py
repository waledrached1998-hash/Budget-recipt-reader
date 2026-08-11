import config as c
from flask import session
from datetime import datetime
from dateutil.relativedelta import relativedelta
from db import get_current_tab as db_get_current_tab, get_sheet_id, get_user, set_current_tab,get_current_tab_valid_until,set_user_sheet,save_user,set_category,get_categories
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


DEFAULT_CATEGORIES = ["Groceries","Take out & restaurants","Going out","Clothing","Electronics","Home essentials","Medicine","Gifts","Transportation","Other"]


def duplicate_template_tab(request_json,new_sheet_name,sheets_service,sheet_id,user_id):
    result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()

    for sheet in result['sheets']:
        if sheet['properties']['title'] == 'Budget I':
            prime_tab_id = sheet['properties']['sheetId']

    if does_tab_exist(new_sheet_name,sheets_service,sheet_id):
        return {"status": "already exists"}, 400

    body = {
        "requests": [
            {
                "duplicateSheet": {
                    "sourceSheetId": prime_tab_id,
                    "insertSheetIndex": 0,
                    "newSheetName": new_sheet_name
                }
            }
        ]
    }
    sheets_service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
    set_current_tab(user_id,sheet_id,new_sheet_name,request_json['end_date'])


def write_income(request_json, sheet_tab,sheets_service,sheet_id):
    income_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_tab}!E27:E37"
    ).execute()
    values = income_result.get('values', [])
    current_income_row = 27 + len(values)
    for entry in request_json['income']:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_income_row}:E{current_income_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!G{current_income_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!J{current_income_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        current_income_row = current_income_row+1

def write_savings(request_json, sheet_tab,sheets_service,sheet_id):
    income_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_tab}!E42:E57"
    ).execute()
    values = income_result.get('values', [])
    current_savings_row = 42 + len(values)
    for entry in request_json['savings']:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_savings_row}:E{current_savings_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!G{current_savings_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!J{current_savings_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        current_savings_row = current_savings_row+1

def write_date(request_json, sheet_tab,sheets_service,sheet_id):
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"{sheet_tab}!G9", "values": [[request_json['start_date']]]},
            {"range": f"{sheet_tab}!G10", "values": [[request_json['end_date']]]}
        ]
    }
    sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


def write_expenses(parsed, sheet_tab,sheets_service,sheet_id):
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_tab}!G62:G322"
    ).execute()
    values = result.get('values', [])
    current_row = 62 + len(values)

    for category, total in parsed['items'].items():
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_row}", "values": [[parsed['date']]]},
                {"range": f"{sheet_tab}!G{current_row}", "values": [[total]]},
                {"range": f"{sheet_tab}!I{current_row}", "values": [[category]]},
                {"range": f"{sheet_tab}!K{current_row}", "values": [[parsed['store_name']]]},
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        current_row = current_row + 1


def write_bills(request_json, sheet_tab,sheets_service,sheet_id):
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_tab}!M17:M56"
    ).execute()
    values = result.get('values', [])
    current_row = 17 + len(values)

    for entry in request_json['bills']:
        due_date = entry.get('due_date', '')

        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!M{current_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!N{current_row}", "values": [[due_date]]},
                {"range": f"{sheet_tab}!P{current_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!R{current_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
        current_row = current_row+1
    
    

    

def does_tab_exist(tab_name,sheets_service,sheet_id):
    result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    for sheet in result['sheets']:
        if sheet['properties']['title'] == tab_name:
            return True
    return False


def get_current_tab(user_id,sheet_id):
    title = db_get_current_tab(user_id,sheet_id)

    return title

def get_current_tab_still_valid(user_id,sheet_id):
    valid_until_str = get_current_tab_valid_until(user_id, sheet_id)
    if valid_until_str is None:
        return False

    valid_until = datetime.strptime(valid_until_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    return today <= valid_until


def get_next_tab_name(request_json):
    end_date = datetime.strptime(request_json['end_date'], "%Y-%m-%d")
    return end_date.strftime("%B-%Y")

def get_user_credentials(user_id) :
    user = get_user(user_id)

    user_credentials = Credentials(
        token=user['access_token'],
        refresh_token=user['refresh_token'],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=c.GOOGLE_CLIENT_ID ,
        client_secret=c.GOOGLE_CLIENT_SECRET,
    )
    if user_credentials.expired and user_credentials.refresh_token:
        user_credentials.refresh(Request())
        save_user(user_id, user['email'], user_credentials.token, user_credentials.refresh_token, user_credentials.expiry.isoformat())

    return user_credentials



def get_user_sheets_service(user_id):
    creds = get_user_credentials(user_id)
    return build('sheets', version='v4', credentials=creds)

def get_user_drive_service(user_id):
    creds = get_user_credentials(user_id)
    return build('drive', version='v3', credentials=creds)

def get_user_sheet_id (user_id) :
    sheet_id = get_sheet_id(user_id)
    return sheet_id

def create_user_sheet(template_file_id, user_email, user_drive_service):
    c.drive_service.permissions().create(
        fileId=template_file_id,
        body={"type": "user", "role": "reader", "emailAddress": user_email}
    ).execute()

    copied_file = user_drive_service.files().copy(
        fileId=template_file_id,
        body={"name": f"Budget - {user_email}"}
    ).execute()
    return copied_file['id']

def seed_default_categories(user_id):
    for category in DEFAULT_CATEGORIES:
        set_category(user_id, category)
    
    

def save_user_sheet(user_id,sheet_id):
    set_user_sheet(user_id,sheet_id)

def write_categories_to_tab (tab_name,sheets_service,categories,sheet_id):
    
    clear_values = [[""] for _ in range(17, 57)]  # 40 rows, T17 to T56
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!T17:T56",
        valueInputOption="USER_ENTERED",
        body={"values": clear_values}
    ).execute()

    rows = [[cat] for cat in categories]
    if rows:
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{tab_name}!T17:T{17 + len(rows) - 1}",
            valueInputOption="USER_ENTERED",
            body={"values": rows}
        ).execute()


def sync_categories_to_sheet(user_id, sheets_service, sheet_id):
    categories = get_categories(user_id)
    write_categories_to_tab('Budget I',sheets_service,categories,sheet_id)
    current_tab = get_current_tab(user_id, sheet_id)
    if current_tab is not None :
        write_categories_to_tab(current_tab,sheets_service,categories,sheet_id)

def get_current_income(sheet_tab, sheets_service, sheet_id):
    income_result_name = sheets_service.spreadsheets().values().get(
        spreadsheetId = sheet_id,
        range = f"{sheet_tab}!D27:E36"
    ).execute()
    income_result_value = sheets_service.spreadsheets().values().get(
            spreadsheetId = sheet_id,
            range =f"{sheet_tab}!J27:J36",
            valueRenderOption='UNFORMATTED_VALUE'
    ).execute()
    
    income_name = income_result_name.get('values', [])
    income_value = income_result_value.get('values', [])
    entries = []
    for name_row, amount_row in zip(income_name, income_value):
        entries.append({"name": name_row[0], "amount": amount_row[0]})

    return entries  

def replace_income(entries, sheet_tab, sheets_service, sheet_id):
    clear_values = [[""] for _ in range(27, 37)]

    body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                    {"range": f"{sheet_tab}!D27:E36", "values": clear_values},
                    {"range": f"{sheet_tab}!G27:G36", "values": clear_values},
                    {"range": f"{sheet_tab}!J27:J36", "values": clear_values}
                ]
    }
    sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId = sheet_id, body = body
    ).execute()


    current_row = 27
    for entry in entries:
        write_body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_row}:E{current_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!G{current_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!J{current_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=sheet_id, body=write_body
        ).execute()
        current_row += 1

    # write the given entries starting at row 27

def get_current_savings(sheet_tab, sheets_service, sheet_id):
    savings_result_name = sheets_service.spreadsheets().values().get(
        spreadsheetId = sheet_id,
        range =f"{sheet_tab}!D42:E56"
    ).execute()
    savings_result_value = sheets_service.spreadsheets().values().get(
        spreadsheetId = sheet_id,
        range =f"{sheet_tab}!J42:J56",
        valueRenderOption='UNFORMATTED_VALUE'
    ).execute()
    savings_name = savings_result_name.get('values',[])
    savings_value = savings_result_value.get('values',[])

    entries = []
    for name,value in zip(savings_name,savings_value):
        entries.append({'name':name[0],'amount':value[0]})

    return entries

def replace_savings(entries, sheet_tab, sheets_service, sheet_id):
    clear_values = [[""] for _ in range(42, 57)]

    body = {
        "valueInputOption": "USER_ENTERED",
        "data" : [
            {"range":f"{sheet_tab}!D42:E56","values" : clear_values},
            {"range":f"{sheet_tab}!G42:G56","values":clear_values},
            {"range":f"{sheet_tab}!J42:J56","values":clear_values}
        ] 
    }
    sheets_service.spreadsheets().values().batchUpdate(
        spreadsheetId = sheet_id,
        body = body
        ).execute()
    current_row = 42
    for entry in entries : 
        write_body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range":f"{sheet_tab}!D{current_row}:E{current_row}","values":[[entry['name']]]},
                {"range":f"{sheet_tab}!G{current_row}","values":[[entry['amount']]]},
                {"range":f"{sheet_tab}!J{current_row}","values":[[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(
                    spreadsheetId = sheet_id,
                    body = write_body
            ).execute()
        current_row = current_row +1

    

   


