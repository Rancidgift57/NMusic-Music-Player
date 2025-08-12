import requests
import os
import sys
import time
import random

def ping_api_with_random_delay():
    """
    Waits for a random period and then sends a single GET request.
    """
    api_url = "https://nmusic.onrender.com/"
    
    if not api_url:
        print("ERROR: API_URL environment variable not set. Exiting.")
        sys.exit(1)

    # Wait for a random number of seconds between 0 and 120 (2 minutes)
    random_delay = random.randint(0, 120)
    print(f"Waiting for {random_delay} seconds before pinging...")
    time.sleep(random_delay)

    print(f"Pinging {api_url} to keep it alive...")

    try:
        response = requests.get(api_url, timeout=30)
        if 200 <= response.status_code < 300:
            print(f"  -> SUCCESS! Status Code: {response.status_code}")
        else:
            print(f"  -> WARNING! Received non-success status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  -> FAILED! An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ping_api_with_random_delay()
