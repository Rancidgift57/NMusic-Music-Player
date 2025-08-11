import requests
import os
import sys

def ping_api():
    """
    Sends a single GET request to the API URL and exits.
    """
    api_url = "https://nmusic.onrender.com/"
    
    if not api_url:
        print("ERROR: API_URL environment variable not set. Exiting.")
        sys.exit(1) # Exit with an error code

    print(f"Pinging {api_url} to keep it alive...")

    try:
        response = requests.get(api_url, timeout=30)
        # We only care that the request was successful, not the content
        if 200 <= response.status_code < 300:
            print(f"  -> SUCCESS! Status Code: {response.status_code}")
        else:
            print(f"  -> WARNING! Received non-success status code: {response.status_code}")
            print(f"  -> Response Body: {response.text[:200]}")
            # Even with a non-success code, the service is awake, so we don't fail the script
            
    except requests.exceptions.RequestException as e:
        print(f"  -> FAILED! An error occurred: {e}")
        sys.exit(1) # Exit with an error code to fail the workflow run

if __name__ == "__main__":
    ping_api()

