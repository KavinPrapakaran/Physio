import sys
sys.path.insert(0, r'c:/Users/Kavin Prabakaran/Documents/Kavin HTML')
from backend.app import app

client = app.test_client()
health = client.get('/api/health')
print('status', health.status_code)
print('json', health.get_json())
login = client.get('/login')
print('login_status', login.status_code)
print('login_contains', 'REE Forma' in login.get_data(as_text=True))
