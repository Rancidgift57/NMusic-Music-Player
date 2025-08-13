import requests
import os
import sys
import time
import random
from datetime import datetime, time as dt_time

def is_time_in_range(start, end, current):
    """Checks if a time is within a given range."""
    return start <= current <= end

def ping_api_with_schedule():
    """
    Checks if the current time is within the scheduled windows,
    then waits for a random period and sends a single GET request.
    """
    # Define scheduled windows in UTC
    # Morning Window (IST 6:30-9:30 AM): 01:00 UTC to 04:00 UTC
    # Afternoon Window (IST 2:30-6:00 PM): 09:00 UTC to 12:30 UTC
    utc_now = datetime.utcnow().time()
    
    # Define the time ranges
    morning_start = dt_time(1, 0)
    morning_end = dt_time(4, 0)
    afternoon_start = dt_time(9, 0)
    afternoon_end = dt_time(12, 30)

    in_morning_window = is_time_in_range(morning_start, morning_end, utc_now)
    in_afternoon_window = is_time_in_range(afternoon_start, afternoon_end, utc_now)

    if not (in_morning_window or in_afternoon_window):
        print(f"Current UTC time {utc_now.strftime('%H:%M:%S')} is outside the scheduled pinging windows. Exiting.")
        sys.exit(0) # Exit successfully without pinging

    print(f"Current UTC time {utc_now.strftime('%H:%M:%S')} is within a scheduled window. Proceeding with ping.")
    
    api_url = "https://nmusic.onrender.com/"
    if not api_url:
        print("ERROR: API_URL environment variable not set. Exiting.")
        sys.exit(1)

    # Wait for a random number of seconds between 0 and 120 (2 minutes)
    # This adds randomness to the exact ping time within the window
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
    ping_api_with_schedule()

