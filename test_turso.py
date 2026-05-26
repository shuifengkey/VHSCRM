import urllib.request
import urllib.error
import json

url = "https://vhs-crm-shuifengkey.turso.io/v2/pipeline"
token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3Nzk3MjE1OTIsImlkIjoiMDE5ZTVmYWItYTMwMS03NDI0LWJkMDEtYjQxYWFkMDY3YjJlIiwicmlkIjoiOGUxZDI1YmUtM2VkYy00MGE2LWFiM2QtYjRmYTMzNGNjMGRlIn0.quHMJF0JlPiFzRP3m50uR9YJE5ec3zm-644ZWp3gJfayzUpxCLBwnpqCY6fKr1MN7TCVjcBOOUn_BZRlZpIXBw"

data = json.dumps({"requests": [{"type": "execute", "stmt": {"sql": "SELECT 1"}}]}).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
})

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()}")
except Exception as e:
    print(e)
