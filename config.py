

import os
from anthropic import Anthropic
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from db import get_user
from flask import  session

load_dotenv()

anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
sheet_id = os.environ["SHEET_ID"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI = os.environ["GOOGLE_OAUTH_REDIRECT_URI"]
FLASK_SECRET_KEY = os.environ["FLASK_SECRET_KEY"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "scp", "budget-recipt-reader-dd91f18db0d1.json")


credentials = Credentials.from_service_account_file(
    KEY_PATH,
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
sheets_service = build('sheets', version='v4', credentials=credentials)
drive_service = build('drive', version='v3', credentials=credentials)



