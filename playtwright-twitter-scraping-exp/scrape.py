from playwright.sync_api import sync_playwright, Playwright, Error, Response
import json
import time
import urllib.parse
from typing import List

def format_output_json(data: List[dict]) -> List[dict]:
    out = {"threaded_conversation_with_injections_v2": {
        "instructions": [{"type": "TimelineAddEntries", "entries": []}]
    }}
    for item in data:
        out["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"].extend(item["data"]["threaded_conversation_with_injections_v2"]["instructions"][0]["entries"])
    return out


        

# Store captured data
captured_data = []
# Flags for pagination control
initial_load_complete = False  # Flag for first TweetDetail response
next_response_received = False # Flag for subsequent responses after scrolling

def format_url(url):
    """Format a URL to make it more readable by parsing and formatting its components."""
    parsed_url = urllib.parse.urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    
    # Parse query parameters
    query_params = urllib.parse.parse_qs(parsed_url.query)
    formatted_params = {}
    
    # Decode JSON-encoded parameters
    for key, value in query_params.items():
        try:
            # Handle cases where the value might be JSON encoded
            if key in ["variables", "features", "fieldToggles"] and value[0]:
                formatted_params[key] = json.loads(urllib.parse.unquote(value[0]))
            else:
                formatted_params[key] = value[0]
        except (json.JSONDecodeError, IndexError):
            formatted_params[key] = value
    
    return {
        "base_url": base_url,
        "params": formatted_params
    }

def handle_response(response: Response):
    """Callback function to handle network responses, capturing raw TweetDetail JSON."""
    global captured_data, initial_load_complete, next_response_received

    # Print request headers

    # Check if the URL matches the pattern for TweetDetail GraphQL API
    if "/i/api/graphql/" in response.url and "/TweetDetail" in response.url:
        # print(f"\n--- Intercepted TweetDetail Response ---")
        # print("Request Headers:")
        # for name, value in response.request.headers.items():
        #     print(f"  {name}: {value}")

        # print(f"URL: {response.url}")
        
        # # Format and print URL in a readable format
        # formatted_url = format_url(response.url)
        # print("\nFormatted URL:")
        # print(f"Base URL: {formatted_url['base_url']}")
        # print("Query Parameters:")
        # for param_name, param_value in formatted_url['params'].items():
        #     if isinstance(param_value, dict):
        #         print(f"  {param_name}:")
        #         for sub_key, sub_value in param_value.items():
        #             print(f"    {sub_key}: {sub_value}")
        #     else:
        #         print(f"  {param_name}: {param_value}")
        
        # print(f"Status: {response.status}")
        # print(f"Headers: {response.headers}") # Print headers

        try:
            data = response.json()
            print("Response JSON successfully parsed.")
            captured_data.append(data)  # Store the raw JSON data

            # Signal that a response was received for pagination control
            if not initial_load_complete:
                print("--- Initial TweetDetail load complete ---")
                initial_load_complete = True
                # Set next_response_received too, in case the wait loop started early
                next_response_received = True
            else:
                print("--- Subsequent TweetDetail response received ---")
                next_response_received = True

        except Exception as e:
            print(f"Error processing TweetDetail response: {e}")
            try:
                # Print text if JSON parsing fails
                print("Response Text (first 500 chars):")
                print(response.text()[:500] + "...")
            except Exception as text_e:
                print(f"Error getting response text: {text_e}")

        print(f"--- End Intercepted Response ---")


def run(playwright: Playwright):
    """Main function to connect to Chrome, navigate to a tweet, and implement pagination."""
    global captured_data, initial_load_complete, next_response_received

    # Reset data collections and flags for this run
    captured_data = []
    initial_load_complete = False
    next_response_received = False

    try:
        # Connect to the existing Chrome instance via the debugging port
        browser = playwright.chromium.connect_over_cdp("http://localhost:9223")
        print("Successfully connected to Chrome over CDP.")

        # Get the default context or create a new one if needed
        if not browser.contexts:
            print("Warning: No browser contexts found. Creating a new context.")
            try:
                context = browser.new_context()
                print("Created a new browser context.")
            except Error as new_context_error:
                print(f"Could not create a new context: {new_context_error}")
                browser.close()
                return
        else:
            # Use the first context found
            context = browser.contexts[0]
            print(f"Using existing browser context.")

        # Create a new page within this context
        page = context.new_page()
        print("Created a new page in the browser context.")

        # Set the color scheme to no-preference to respect the browser's theme
        page.emulate_media(color_scheme="no-preference")

        # Set up response handler BEFORE navigation
        print("Setting up network response listener...")
        page.on("response", handle_response)

        # Navigate to the Tweet
        tweet_url = "https://x.com/aiDotEngineer/status/1930825193062277238"
        print(f"Navigating to {tweet_url}...")
        
        try:
            # Navigate without waiting for network idle initially
            page.goto(tweet_url, timeout=30000)
            print(f"Initial navigation to {page.title()} complete.")
            # page.wait_for_timeout(3000) # REMOVED - Wait for signal instead
            # page.wait_for_load_state('load', timeout=30000) # This doesnt make any difference
        except Exception as nav_error:
            print(f"Navigation failed: {nav_error}")
            # Consider cleanup if navigation fails critically
            page.close()
            browser.close() # Assuming CDP connection owns the browser lifecycle here might be wrong, adjust if needed
            return

        # --- Wait for the initial TweetDetail response ---
        print("Waiting for the initial TweetDetail response...")
        wait_start_time = time.time()
        initial_wait_timeout = 45 # Increased timeout for initial load
        while not initial_load_complete:
            page.wait_for_timeout(100) # Check every 100ms, allows Playwright events to process
            if time.time() - wait_start_time > initial_wait_timeout:
                 print(f"Timeout ({initial_wait_timeout}s) waiting for initial TweetDetail response.")
                 # Decide how to handle timeout
                 page.close()
                 # browser.close() # Consider if closing the browser is appropriate here
                 return # Exit the function if initial data doesn't load

        print("Initial TweetDetail response received. Starting pagination.")

        # --- Implement Pagination through Scrolling ---
        max_scrolls = 5 # Allow more scrolls
        scroll_count = 0
        stalled_scrolls = 0 # Count scrolls with no new entries

        print("\n--- Starting pagination via scrolling ---")

        while scroll_count < max_scrolls:
            scroll_count += 1
            print(f"\nPerforming scroll {scroll_count}/{max_scrolls}...")

            # Reset flag before scrolling and waiting for the *next* response
            next_response_received = False
            # Track data count before scroll to see if new responses are captured
            data_count_before_scroll = len(captured_data)

            # Scroll to the bottom of the page
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            print("Scrolled down.")

            # Wait for the next TweetDetail response after scrolling
            print("Waiting for next TweetDetail response...")
            wait_start_time = time.time()
            scroll_wait_timeout = 5 # Timeout for waiting for response after scroll
            while not next_response_received:
                page.wait_for_timeout(100) # Check frequently
                if time.time() - wait_start_time > scroll_wait_timeout:
                    print(f"Timeout ({scroll_wait_timeout}s) waiting for TweetDetail response after scroll {scroll_count}.")
                    break # Assume no more data is coming for this scroll

            # Add a small delay for rendering after response is received (optional, but can help)
            if next_response_received:
                 print(f"TweetDetail response received after scroll {scroll_count}. Giving 1s for render.")
                 page.wait_for_timeout(1000)
            else:
                print("Proceeding after wait timeout.")

            # Check if new data was captured since the last scroll
            new_data_count = len(captured_data) - data_count_before_scroll
            if new_data_count > 0:
                print(f"Scroll {scroll_count} successful: Captured {new_data_count} new TweetDetail response(s).")
                stalled_scrolls = 0 # Reset stall counter
            else:
                print(f"No new TweetDetail responses captured after scroll {scroll_count} and waiting.")
                stalled_scrolls += 1
                if stalled_scrolls >= 2: # If 2 consecutive scrolls yield nothing, assume end
                    print("Reached end of content (2 consecutive empty scrolls).")
                    break

        print(f"\n--- Pagination complete after {scroll_count} scrolls ---")

        # Report final results
        print("\n--- Scraping Results ---")
        print(f"Total raw TweetDetail responses captured: {len(captured_data)}")

        # Save captured data to file
        with open("captured_tweet_data.json", "w") as f:
            json.dump(format_output_json(captured_data), f, indent=2) # Save the raw list
        print("Raw data saved to captured_tweet_data.json")

        # Keep the script alive to observe or debug
        input("\nPress Enter to close the page and disconnect...")

        # Clean up
        page.remove_listener("response", handle_response)
        page.close()
        print("Page closed and disconnected.")

    except Error as playwright_error:
        print(f"A Playwright error occurred: {playwright_error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Chrome was launched with the command:")
        print('   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9223')
        print("2. Verify that port 9223 is accessible and not used by another process.")
        print("3. Make sure the Chrome browser window is actually open and running.")


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
    
    print("Playwright script finished.")
