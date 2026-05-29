import requests
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.file'
]

def initiate_device_flow(client_id):
    url = "https://oauth2.googleapis.com/device/code"
    data = {
        "client_id": client_id,
        "scope": " ".join(SCOPES)
    }
    resp = requests.post(url, data=data)
    if resp.status_code == 200:
        return resp.json(), None
    return None, resp.text

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
        return resp.json(), None
    return None, resp.text

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
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'popup', 'minutes': 12 * 60},
            ],
          },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return True, event.get('id')
    except Exception as e:
        return False, str(e)

def update_event_on_google(creds, event_id, subject, start_dt, end_dt, content, location=""):
    try:
        if not event_id: return False, "No event ID"
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
          'reminders': {
            'useDefault': False,
            'overrides': [
              {'method': 'popup', 'minutes': 12 * 60},
            ],
          },
        }
        event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return True, event.get('id')
    except Exception as e:
        return False, str(e)

def delete_event_on_google(creds, event_id):
    try:
        if not event_id: return False, "No event ID"
        service = build('calendar', 'v3', credentials=creds)
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True, "Deleted"
    except Exception as e:
        return False, str(e)

def auto_sync_schedule_to_google(conn, schedule_id, action="upsert"):
    """
    Tự động đồng bộ 1 schedule lên Google Calendar.
    action: "upsert" (tạo mới hoặc cập nhật), "delete" (xóa)
    Lưu ý: HAm này sử dụng object conn từ utils.database.get_connection()
    """
    # 1. Get credentials
    settings = dict(conn.execute("SELECT key_name, value_data FROM settings").fetchall())
    client_id = settings.get("google_client_id")
    client_secret = settings.get("google_client_secret")
    cache_str = settings.get("google_token_cache")
    if not client_id or not client_secret or not cache_str:
        return False, "Chưa cấu hình Google Calendar."
    
    creds, new_cache = get_cached_credentials(client_id, client_secret, cache_str)
    if not creds or not creds.valid:
        return False, "Token không hợp lệ hoặc hết hạn."
    
    # 2. Update cache if refreshed
    if new_cache and new_cache != cache_str:
        conn.execute("INSERT OR REPLACE INTO settings (id, key_name, value_data) VALUES ((SELECT id FROM settings WHERE key_name='google_token_cache'), 'google_token_cache', ?)", (new_cache,))
        conn.commit()
        
    # 3. Get schedule info
    if action == "delete":
        # Với delete, cần biết google_event_id. Thường truyền google_event_id vào schedule_id nếu bản ghi đã bị xóa khỏi DB.
        # Nhưng để an toàn, ta coi schedule_id là google_event_id luôn.
        ok, msg = delete_event_on_google(creds, schedule_id)
        return ok, msg
        
    # Upsert: Lấy thông tin từ DB
    row = conn.execute("""
        SELECT s.id, s.ngay_du_kien, s.gio_bat_dau, s.gio_ket_thuc, s.ghi_chu, s.ky_thuat_vien, s.google_event_id, c.ten_cty, c.dia_chi
        FROM schedules s
        JOIN customers c ON s.ma_kh=c.ma_kh
        WHERE s.id=?
    """, (schedule_id,)).fetchone()
    
    if not row: return False, "Không tìm thấy lịch."
    
    start_dt = f"{row['ngay_du_kien']}T{row['gio_bat_dau']}:00"
    end_dt   = f"{row['ngay_du_kien']}T{row['gio_ket_thuc']}:00"
    subject  = f"[VHS] Thi công: {row['ten_cty']}"
    content  = f"Khách hàng: {row['ten_cty']}\n"
    if row['ky_thuat_vien']: content += f"KTV: {row['ky_thuat_vien']}\n"
    if row['ghi_chu']:       content += f"Ghi chú: {row['ghi_chu']}\n"
    location = row['dia_chi'] or ""
    
    event_id = row['google_event_id']
    if event_id:
        ok, eid = update_event_on_google(creds, event_id, subject, start_dt, end_dt, content, location)
    else:
        ok, eid = push_event_to_google(creds, subject, start_dt, end_dt, content, location)
        
    if ok and eid and eid != event_id:
        conn.execute("UPDATE schedules SET google_event_id=? WHERE id=?", (eid, schedule_id))
        conn.commit()
        
    return ok, eid

from googleapiclient.http import MediaIoBaseUpload
import io

def upload_to_google_drive(creds, file_bytes, filename):
    try:
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': filename}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/octet-stream', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e:
        return False, str(e)
