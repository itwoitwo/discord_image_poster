import os
import time
import requests
import datetime
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
# Base directory where year-month folders are located
BASE_WATCH_DIRECTORY = r"YOUR_BASE_DIRECTORY_HERE"  # Replace with your actual base directory path
# Get current year and month in YYYY-MM format
current_year_month = datetime.datetime.now().strftime("%Y-%m")
# Construct the full path to watch
WATCH_DIRECTORY = os.path.join(BASE_WATCH_DIRECTORY, current_year_month)
DISCORD_WEBHOOK_URL = "WEBHOOK_URL_HERE"  # Replace with your actual Discord webhook URL
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'} # Add other image extensions if needed
# --- End Configuration ---

# Keep track of processed files to avoid duplicates if the script restarts quickly
processed_files = set()

def post_to_discord(file_path):
    """Posts an image file to the Discord webhook."""
    filename = os.path.basename(file_path)
    if filename in processed_files:
        print(f"Skipping already processed file: {filename}")
        return
    if not os.path.exists(file_path):
        print(f"File not found (possibly deleted quickly): {filename}")
        return

    print(f"New image detected: {filename}. Posting to Discord...")
    try:
        # Wait a moment for the file to be fully written
        time.sleep(1)
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f)}
            payload = {'content': f'New VRChat picture added: {filename}'}
            response = requests.post(DISCORD_WEBHOOK_URL, files=files, data=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully posted {filename} to Discord.")
        processed_files.add(filename)
    except requests.exceptions.RequestException as e:
        print(f"Error posting {filename} to Discord: {e}")
    except FileNotFoundError:
        print(f"Error: File disappeared before posting: {filename}")
    except Exception as e:
        print(f"An unexpected error occurred while processing {filename}: {e}")


class NewImageHandler(FileSystemEventHandler):
    """Handles file system events."""
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            _, ext = os.path.splitext(file_path)
            if ext.lower() in ALLOWED_EXTENSIONS:
                # Use a small delay to ensure the file is fully written before processing
                # This helps prevent issues with large files or slow writes.
                time.sleep(0.5)
                # Check again if file exists before posting, might be deleted between check and post
                if os.path.exists(file_path):
                    post_to_discord(file_path)
                else:
                    print(f"Skipping file as it disappeared quickly: {file_path}")

def run_observer(observer):
    """Runs the watchdog observer loop."""
    print(f"Monitoring directory: {WATCH_DIRECTORY}")
    print(f"Posting new images to Discord webhook...")
    observer.start()
    try:
        observer.join() # Blocks until observer.stop() is called
    finally:
        if observer.is_alive(): # Ensure stop if join returns unexpectedly
             observer.stop()
             observer.join() # Wait for stop to complete
        print("Observer stopped.")


# --- Main Execution ---

if __name__ == "__main__":
    # 1. Check if watch directory exists
    if not os.path.isdir(WATCH_DIRECTORY):
        # Maybe try to create it? Or just error out.
        try:
            print(f"Warning: Directory not found - {WATCH_DIRECTORY}. Attempting to create it.")
            os.makedirs(WATCH_DIRECTORY)
            print(f"Successfully created directory: {WATCH_DIRECTORY}")
        except OSError as e:
            print(f"Error: Could not create directory {WATCH_DIRECTORY}: {e}")
            print("Please ensure the base directory exists and you have permissions.")
            # Use pystray to show error if possible, or just exit
            # For simplicity, we'll just exit here. A GUI popup would be better.
            exit(1)
    elif not os.access(WATCH_DIRECTORY, os.W_OK):
         print(f"Error: No write permissions for directory: {WATCH_DIRECTORY}")
         exit(1)


    # 2. Set up watchdog observer
    event_handler = NewImageHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIRECTORY, recursive=False)

    # 3. Run the observer directly
    # This will block the main thread until interrupted (e.g., Ctrl+C)
    run_observer(observer)

    print("Script finished.") # This line will likely only be reached on interruption