import requests
import json
import time
import os # Import the os module to check if the file exists
from dotenv import load_dotenv


load_dotenv()

# --- Configuration ---
# Get sensitive variables from environment
bearer_token = os.getenv('BEARER_TOKEN')


initial_get_url = 'https://lopy-api.komscochak.com/mb/v1/merc/mc-info/member/selectAplyPromot' # REPLACE with the actual URL
search_url = 'https://lopy-api.komscochak.com/mb/v1/merc/mc-find/search'
output_filename = 'all_merchants.json'

# --- Check if bearer token is loaded ---
if not bearer_token:
    print("Error: Bearer token not found. Please set BEARER_TOKEN in your .env file or environment variables.")
    exit()

# Headers for the initial GET request
initial_get_headers = {
    'Host': 'lopy-api.komscochak.com',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Authorization': f'Bearer {bearer_token}', # Use the variable here
    'X-KOMSCO-AREA-SRVC-ID': 'ARC00000000000000003',
    'X-KOMSCO-PAGE-ID': 'SCR_PF_APP_018_001',
    'X-KOMSCO-GBN-CD': '02',
    'X-KOMSCO-APP-ID': 'com.komscochak.m2.client',
    'X-KOMSCO-APP-VERSION': '1.0.0',
    'X-KOMSCO-MEMB-LONGITUDE': 'null',
    'X-KOMSCO-MEMB-LATITUDE': 'null',
    'Origin': 'https://localpay.komscochak.com',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://localpay.komscochak.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site'
}

# Headers for the POST request
post_headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Authorization': f'Bearer {bearer_token}', # Use the variable here
    'Content-Type': 'application/json',
    'DNT': '1',
    'Host': 'lopy-api.komscochak.com',
    'Origin': 'https://localpay.komscochak.com',
    'Referer': 'https://localpay.komscochak.com/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0',
    'X-KOMSCO-APP-ID': 'com.komscochak.m2.client',
    'X-KOMSCO-APP-VERSION': '1.0.0',
    'X-KOMSCO-AREA-SRVC-ID': 'ARC00000000000000003',
    'X-KOMSCO-GBN-CD': '02',
    'X-KOMSCO-MEMB-LATITUDE': 'null',
    'X-KOMSCO-MEMB-LONGITUDE': 'null',
    'X-KOMSCO-PAGE-ID': 'SCR_PF_APP_018_001'
}

# Create a requests Session to handle cookies
session = requests.Session()

# --- Step 1: Attempt to load existing data from the JSON file ---
all_merchants = []
start_pagination_from_last_merchant = False

if os.path.exists(output_filename):
    print(f"Found existing data file: '{output_filename}'. Attempting to resume.")
    try:
        with open(output_filename, 'r', encoding='utf-8') as f:
            all_merchants = json.load(f)
        print(f"Successfully loaded {len(all_merchants)} merchants from the file.")

        if all_merchants:
            # If data was loaded, we need to start pagination from the last entry
            start_pagination_from_last_merchant = True
            print("Will attempt to resume pagination from the last loaded merchant.")
        else:
            print("Loaded file is empty. Starting from the beginning.")

    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading data from '{output_filename}': {e}")
        print("Starting data collection from the beginning.")
        all_merchants = [] # Clear the list if loading failed


# --- Step 2: Make an initial request to get the WMONID cookie ---
# This is always necessary when you restart the script because sessions are not persistent
try:
    print(f"Making initial GET request to get cookie: {initial_get_url}")
    initial_response = session.get(initial_get_url, headers=initial_get_headers)
    initial_response.raise_for_status() # Check for successful status code (200-level)

    print("Initial GET request successful. WMONID cookie should be stored in the session.")

except requests.exceptions.RequestException as e:
    print(f"Error during initial GET request: {e}")
    print("Could not get the WMONID cookie. Please check your internet connection and the initial URL/headers.")
    exit() # Exit if the initial request fails

# --- Step 3: Prepare the initial payload for pagination ---
payload = {
    "lastCcwCd": "",
    "lastMcpCd": "",
    "lastMercId": "",
    "lastMercNm": "",
    "lastMercNmDiv": "",
    "mercNm": "",
    "mercTpbsCd": ""
}

if start_pagination_from_last_merchant and all_merchants:
    # If resuming, get the pagination parameters from the LAST merchant in the loaded data
    last_loaded_merchant = all_merchants[-1]

    # **Map the loaded merchant fields to the payload fields for the next request**
    # Based on your observation of the second POST request's payload.
    # You need to verify this mapping.
    payload["lastCcwCd"] = last_loaded_merchant.get("ccwCd", "")
    payload["lastMcpCd"] = last_loaded_merchant.get("mcpCd", "")
    payload["lastMercId"] = last_loaded_merchant.get("merclId", "")
    payload["lastMercNm"] = last_loaded_merchant.get("mercNm", "")
    payload["lastMercNmDiv"] = last_loaded_merchant.get("mercNmDiv", "")

    print("Prepared payload to resume pagination.")

# --- Step 4: Implement Pagination Logic ---
more_data_available = True
request_count = 0

print("\nStarting pagination to retrieve all merchants...")

# If we are starting from the beginning (no loaded data or empty file),
# we increment request_count to 1 for the first request.
# If resuming, the request_count will represent the page number we are fetching.
if not start_pagination_from_last_merchant or not all_merchants:
     request_count = 1
else:
    # If resuming, we don't count the loaded data as a request
    request_count = 1 # The first *new* request is effectively page 1 after the loaded data


while more_data_available:
    try:
        print(f"\nMaking POST request (Page {request_count}) with payload: {payload}")
        response = session.post(search_url, headers=post_headers, json=payload)
        response.raise_for_status()

        data = response.json()

        if data.get('head', {}).get('resultCode') == '0000':
            merchant_list = data.get('body', {}).get('list', [])

            if merchant_list:
                print(f"Received {len(merchant_list)} merchants in this response.")
                all_merchants.extend(merchant_list) # Add the received merchants to the total list

                # **Update pagination parameters from the LAST merchant of the NEWLY received list**
                last_new_merchant = merchant_list[-1]

                # **Map the response fields to the payload fields for the next request**
                # Ensure this mapping is correct based on your observation.
                payload["lastCcwCd"] = last_new_merchant.get("ccwCd", "")
                payload["lastMcpCd"] = last_new_merchant.get("mcpCd", "")
                payload["lastMercId"] = last_new_merchant.get("merclId", "")
                payload["lastMercNm"] = last_new_merchant.get("mercNm", "")
                payload["lastMercNmDiv"] = last_new_merchant.get("mercNmDiv", "")

                # Keep these the same
                payload["mercNm"] = ""
                payload["mercTpbsCd"] = ""

                # **Save the accumulated data after each successful page fetch**
                try:
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        json.dump(all_merchants, f, indent=4, ensure_ascii=False)
                    print(f"Data saved to '{output_filename}'. Total saved: {len(all_merchants)}")
                except IOError as e:
                    print(f"Error saving data to file during pagination: {e}")

                # Increment request count for the next iteration
                request_count += 1

                # **Optional: Add a small delay between requests**
                time.sleep(1)

            else:
                print("Received an empty list. End of pagination.")
                more_data_available = False

        else:
            print(f"API returned an error: {data.get('head', {}).get('resultMsg', 'Unknown error')}")
            print("Stopping pagination due to API error.")
            print("Full error response:", json.dumps(data, indent=4))
            more_data_available = False


    except requests.exceptions.RequestException as e:
        print(f"Error making the POST request: {e}")
        print("Stopping pagination due to request error.")
        more_data_available = False
    except json.JSONDecodeError:
        print("Error decoding JSON response.")
        print("Stopping pagination due to JSON decode error.")
        print("Response content:", response.text)
        more_data_available = False
    except Exception as e: # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        print("Stopping pagination.")
        more_data_available = False


print(f"\nData collection finished. Total merchants collected: {len(all_merchants)}")

# The data is already saved after each page fetch, so no final save is strictly needed here
# but you could add it if you prefer.
# try:
#     with open(output_filename, 'w', encoding='utf-8') as f:
#         json.dump(all_merchants, f, indent=4, ensure_ascii=False)
#     print(f"Final collected data saved to '{output_filename}'")
# except IOError as e:
#     print(f"Error saving final data to file: {e}")

