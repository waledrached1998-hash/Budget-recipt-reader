import config as c
from datetime import datetime
from dateutil.relativedelta import relativedelta
from db import get_current_tab as db_get_current_tab, set_current_tab,get_current_tab_valid_until


USER_ID = "me"  # placeholder for now

def duplicate_template_tab(request_json,new_sheet_name):
    result = c.sheets_service.spreadsheets().get(spreadsheetId=c.sheet_id).execute()

    for sheet in result['sheets']:
        if sheet['properties']['title'] == 'Budget I':
            prime_tab_id = sheet['properties']['sheetId']

    if does_tab_exist(new_sheet_name):
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
    c.sheets_service.spreadsheets().batchUpdate(spreadsheetId=c.sheet_id, body=body).execute()
    set_current_tab(USER_ID,c.sheet_id,new_sheet_name,request_json['end_date'])


def write_income(request_json, sheet_tab):
    income_result = c.sheets_service.spreadsheets().values().get(
        spreadsheetId=c.sheet_id,
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
        c.sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=c.sheet_id, body=body).execute()


def write_savings(request_json, sheet_tab):
    income_result = c.sheets_service.spreadsheets().values().get(
        spreadsheetId=c.sheet_id,
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
        c.sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=c.sheet_id, body=body).execute()


def write_date(request_json, sheet_tab):
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {"range": f"{sheet_tab}!G9", "values": [[request_json['start_date']]]},
            {"range": f"{sheet_tab}!G10", "values": [[request_json['end_date']]]}
        ]
    }
    c.sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=c.sheet_id, body=body).execute()


def write_expenses(parsed, sheet_tab):
    result = c.sheets_service.spreadsheets().values().get(
        spreadsheetId=c.sheet_id,
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
        c.sheets_service.spreadsheets().values().batchUpdate(spreadsheetId=c.sheet_id, body=body).execute()
        current_row = current_row + 1


def does_tab_exist(tab_name):
    result = c.sheets_service.spreadsheets().get(spreadsheetId=c.sheet_id).execute()
    for sheet in result['sheets']:
        if sheet['properties']['title'] == tab_name:
            return True
    return False


def get_current_tab():
    title = db_get_current_tab(USER_ID,c.sheet_id)

    return title

def get_current_tab_still_valid():
    valid_until_str = get_current_tab_valid_until(USER_ID, c.sheet_id)
    if valid_until_str is None:
        return False

    valid_until = datetime.strptime(valid_until_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    return today <= valid_until


def get_next_tab_name(request_json):
    end_date = datetime.strptime(request_json['end_date'], "%Y-%m-%d")
    return end_date.strftime("%B-%Y")