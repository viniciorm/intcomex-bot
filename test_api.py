import requests
from requests.auth import HTTPBasicAuth
from credentials import WC_URL, WC_CONSUMER_KEY, WC_CONSUMER_SECRET

def test_api():
    endpoint = f"{WC_URL}/wp-json/wp/v2/media"
    print(f"Testing connectivity to {endpoint}...")
    try:
        response = requests.get(
            endpoint,
            auth=HTTPBasicAuth(WC_CONSUMER_KEY, WC_CONSUMER_SECRET),
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
