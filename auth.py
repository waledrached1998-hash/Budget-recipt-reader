from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import requests
import config as c
from db import save_user

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive.file",
]

def build_flow():
    client_config = {
        "web": {
            "client_id": c.GOOGLE_CLIENT_ID,
            "client_secret": c.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [c.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=c.GOOGLE_REDIRECT_URI)
    return flow


def get_login_url():
    flow = build_flow()
    auth_url, _ = flow.authorization_url(access_type="offline", include_granted_scopes="true", prompt="consent")
    return auth_url


def handle_callback(request_url):
    flow = build_flow()
    flow.fetch_token(authorization_response=request_url)
    credentials = flow.credentials

    # Get the user's email and Google ID
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    user_id = userinfo["id"]
    email = userinfo["email"]

    save_user(
        user_id,
        email,
        credentials.token,
        credentials.refresh_token,
        credentials.expiry.isoformat() if credentials.expiry else None
    )

    return user_id, email