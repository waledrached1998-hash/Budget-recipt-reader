from datetime import datetime, timedelta

import sheets as s
from db import (
    get_all_user_sheets, add_cycle, set_current_tab,
    set_cycle_income, set_cycle_savings, set_cycle_expense,
)


def to_iso(raw):
    if isinstance(raw, (int, float)):
        return (datetime(1899, 12, 30) + timedelta(days=raw)).strftime('%Y-%m-%d')
    return raw


def find_active_tab(sheets_service, sheet_id):
    result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    today = datetime.now().date()

    for sheet in result['sheets']:
        props = sheet['properties']
        if props.get('hidden', False):
            continue

        title = props['title']
        date_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{title}!G9:G10",
            valueRenderOption='UNFORMATTED_VALUE'
        ).execute()
        values = date_result.get('values', [])
        if len(values) < 2:
            continue

        try:
            start_date = to_iso(values[0][0])
            end_date = to_iso(values[1][0])
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except (ValueError, IndexError, TypeError):
            continue

        if start <= today <= end:
            return title, start_date, end_date

    return None, None, None


def read_pairs(sheets_service, sheet_id, tab_name, name_range, amount_range):
    name_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{tab_name}!{name_range}",
        valueRenderOption='UNFORMATTED_VALUE'
    ).execute()
    amount_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"{tab_name}!{amount_range}",
        valueRenderOption='UNFORMATTED_VALUE'
    ).execute()

    names = name_result.get('values', [])
    amounts = amount_result.get('values', [])
    return list(zip(names, amounts))


def migrate_user(user_id, sheet_id):
    sheets_service = s.get_user_sheets_service(user_id)
    tab_name, start_date, end_date = find_active_tab(sheets_service, sheet_id)

    if tab_name is None:
        print(f"  No active tab found for user {user_id} — skipped")
        return

    cycle_id = add_cycle(user_id, sheet_id, start_date, end_date, tab_name)
    set_current_tab(user_id, sheet_id, cycle_id)

    for name_row, amount_row in read_pairs(sheets_service, sheet_id, tab_name, "D27:E36", "J27:J36"):
        set_cycle_income(cycle_id, name_row[0], amount_row[0])

    for name_row, amount_row in read_pairs(sheets_service, sheet_id, tab_name, "D42:E56", "J42:J56"):
        set_cycle_savings(cycle_id, name_row[0], amount_row[0])

    for category_row, amount_row in read_pairs(sheets_service, sheet_id, tab_name, "I62:I322", "G62:G322"):
        set_cycle_expense(cycle_id, category_row[0], amount_row[0])

    print(f"  Migrated user {user_id}: cycle_id={cycle_id}, tab='{tab_name}'")


if __name__ == '__main__':
    entries = get_all_user_sheets()
    print(f"Found {len(entries)} user/sheet pairs to migrate.")
    for entry in entries:
        migrate_user(entry['user_id'], entry['sheet_id'])
    print("Done.")