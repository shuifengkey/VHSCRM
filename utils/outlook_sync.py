import msal
import requests
import json
import streamlit as st

SCOPES = ["Calendars.ReadWrite", "User.Read"]

def get_msal_app(client_id, tenant_id, cache_dict=None):
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    cache = msal.SerializableTokenCache()
    if cache_dict:
        cache.deserialize(cache_dict)
    
    app = msal.PublicClientApplication(
        client_id, 
        authority=authority,
        token_cache=cache
    )
    return app, cache

def get_cached_token(client_id, tenant_id, cache_string):
    if not cache_string: return None, None
    app, cache = get_msal_app(client_id, tenant_id, cache_string)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"], cache.serialize()
    return None, cache.serialize()

def initiate_device_flow(client_id, tenant_id):
    app, _ = get_msal_app(client_id, tenant_id)
    flow = app.initiate_device_flow(scopes=SCOPES)
    return flow

def complete_device_flow(client_id, tenant_id, flow):
    app, cache = get_msal_app(client_id, tenant_id)
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" in result:
        return result["access_token"], cache.serialize()
    return None, None

def push_event_to_outlook(access_token, subject, start_dt, end_dt, content, location=""):
    """
    start_dt and end_dt should be ISO 8601 strings in UTC or with timezone.
    For Microsoft Graph, it expects naive datetime + timezone string, e.g.:
    {
      "dateTime": "2023-10-10T12:00:00",
      "timeZone": "SE Asia Standard Time"
    }
    """
    url = "https://graph.microsoft.com/v1.0/me/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "subject": subject,
        "body": {
            "contentType": "HTML",
            "content": content
        },
        "start": {
            "dateTime": start_dt,
            "timeZone": "SE Asia Standard Time"
        },
        "end": {
            "dateTime": end_dt,
            "timeZone": "SE Asia Standard Time"
        },
        "location": {
            "displayName": location
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code == 201:
        return True, resp.json()
    else:
        return False, resp.text
