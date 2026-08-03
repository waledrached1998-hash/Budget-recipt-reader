import config as c
from flask import session
from datetime import datetime
from dateutil.relativedelta import relativedelta
from db import get_current_tab as db_get_current_tab, get_sheet_id, get_user, set_current_tab,get_current_tab_valid_until,set_user_sheet
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build




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
        range=f"{sheet_tab}!D27:D37"
    ).execute()
    values = income_result.get('values', [])
    current_income_row = 27 + len(values)
    for entry in request_json['income']:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_income_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!G{current_income_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!J{current_income_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


def write_savings(request_json, sheet_tab,sheets_service,sheet_id):
    income_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{sheet_tab}!D42:D57"
    ).execute()
    values = income_result.get('values', [])
    current_savings_row = 42 + len(values)
    for entry in request_json['savings']:
        body = {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"{sheet_tab}!D{current_savings_row}", "values": [[entry['name']]]},
                {"range": f"{sheet_tab}!G{current_savings_row}", "values": [[entry['amount']]]},
                {"range": f"{sheet_tab}!J{current_savings_row}", "values": [[entry['amount']]]}
            ]
        }
        sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


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
    return user_credentials

def get_user_sheets_service(user_id):
    creds = get_user_credentials(user_id)
    return build('sheets', version='v3', credentials=creds)

def get_user_drive_service(user_id):
    creds = get_user_credentials(user_id)
    return build('drive', version='v3', credentials=creds)

def get_user_sheet_id (user_id) :
    sheet_id = get_sheet_id(user_id)
    return sheet_id

def create_user_sheet(template_file_id, user_email):
    copied_file = c.drive_service.files().copy(
        fileId=template_file_id,
        body={"name": f"Budget - {user_email}"}
    ).execute()
    new_sheet_id = copied_file['id']

    c.drive_service.permissions().create(
        fileId=new_sheet_id,
        body={
            "type": "user",
            "role": "writer",
            "emailAddress": user_email
        }
    ).execute()

    return new_sheet_id

def save_user_sheet(user_id,sheet_id):
    set_user_sheet(user_id,sheet_id)


