import requests
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def initiate_device_flow(client_id):
    url = "https://oauth2.googleapis.com/device/code"
    data = {
        "client_id": client_id,
        "scope": " ".join(SCOPES)
    }
    resp = requests.post(url, data=data)
    if resp.status_code == 200:
        return resp.json()
    return None

def complete_device_flow(client_id, client_secret, device_code):
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }
    resp = requests.post(url, data=data)
    if resp.status_code == 200:
        return resp.json()
    return None

def get_cached_credentials(client_id, client_secret, token_cache_json):
    if not token_cache_json:
        return None, None
    try:
        token_data = json.loads(token_cache_json)
        creds = Credentials(
            token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data['access_token'] = creds.token
            return creds, json.dumps(token_data)
        return creds, token_cache_json
    except Exception as e:
        print(f"Error loading creds: {e}")
        return None, None

def push_event_to_google(creds, subject, start_dt, end_dt, content, location=""):
    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
          'summary': subject,
          'location': location,
          'description': content,
          'start': {
            'dateTime': start_dt,
            'timeZone': 'Asia/Ho_Chi_Minh',
          },
          'end': {
            'dateTime': end_dt,
            'timeZone': 'Asia/Ho_Chi_Minh',
          },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return True, event
    except Exception as e:
        return False, str(e)
