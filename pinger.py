import requests
import time
import os

def ping_api(api_url):
    """
    Sends a GET request to the specified API URL and prints the result.

    Args:
        api_url (str): The URL of the API to ping.
    """
    try:
        # Record the start time
        start_time = time.time()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Pinging {api_url}...")

        # Send the GET request
        response = requests.get(api_url, timeout=20) # 20-second timeout

        # Record the end time
        end_time = time.time()
        
        # Calculate the duration
        duration = end_time - start_time

        # Check if the request was successful (status code 2xx)
        if response.ok:
            print(f"  -> SUCCESS! Status Code: {response.status_code}. Response time: {duration:.2f}s")
        else:
            # Handle non-successful status codes
            print(f"  -> FAILED! Status Code: {response.status_code}. Response time: {duration:.2f}s")
            print(f"  -> Response Body: {response.text[:200]}") # Print first 200 chars of response

    except requests.exceptions.RequestException as e:
        # Handle network errors (e.g., DNS failure, refused connection)
        print(f"  -> ERROR! An error occurred: {e}")
    except Exception as e:
        # Handle other unexpected errors
        print(f"  -> UNEXPECTED ERROR! An unexpected error occurred: {e}")


def main():
    """
    Main function to run the pinging loop for a limited duration.
    """
    # Get the API URL from an environment variable. This is crucial for GitHub Actions.
    api_url = "https://nmusic.onrender.com/"
    
    if not api_url:
        print("ERROR: API_URL environment variable not set. Exiting.")
        return

    # The interval in seconds to wait between pings
    ping_interval = 50
    # How long the entire script should run, in seconds (e.g., 4.5 minutes)
    run_duration = 270 

    print("--- GitHub Actions API Pinger Started ---")
    print(f"Target URL: {api_url}")
    print(f"Ping Interval: {ping_interval} seconds")
    print(f"Total Run Duration: {run_duration} seconds")
    print("-----------------------------------------")

    script_start_time = time.time()

    # Loop for a set duration instead of infinitely
    while (time.time() - script_start_time) < run_duration:
        ping_api(api_url)
        print(f"Waiting for {ping_interval} seconds...")
        time.sleep(ping_interval)
    
    print("--- Script finished its run. ---")


if __name__ == "__main__":
    main()
