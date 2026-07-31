import os
from anthropic import Anthropic
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
sheet_id = os.environ["SHEET_ID"]

credentials = Credentials.from_service_account_file(
    "/workspaces/Budget-recipt-reader/scp/budget-recipt-reader-dd91f18db0d1.json",
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
sheets_service = build('sheets', version='v4', credentials=credentials)