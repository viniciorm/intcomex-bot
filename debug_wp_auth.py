import requests
from requests.auth import HTTPBasicAuth
from credentials import WC_URL, WP_USER, WP_APP_PASS

def debug_auth():
    endpoint = f"{WC_URL}/wp-json/wp/v2/users/me"
    print(f"Testing auth for user: {WP_USER}")
    print(f"Endpoint: {endpoint}")
    
    auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
    try:
        response = requests.get(endpoint, auth=auth, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            user_info = response.json()
            print(f"Successfully authenticated as: {user_info.get('name')} (ID: {user_info.get('id')})")
            print(f"Capabilities: {user_info.get('capabilities')}")
        else:
            print(f"Auth failed: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_auth()
