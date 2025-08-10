import os
import time
import requests
from PIL import Image
import io
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuration ---
# Base directory where year-month folders are located
BASE_WATCH_DIRECTORY = r"YOUR_BASE_DIRECTORY_HERE"  # Replace with your actual base directory path
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

    # 10MB超過判定
    max_size = 10 * 1024 * 1024
    file_size = os.path.getsize(file_path)
    file_obj = None
    send_filename = filename

    if file_size > max_size:
        print(f"{filename} is over 10MB. Compressing to JPEG in memory...")
        try:
            with Image.open(file_path) as img:
                # RGB変換（PNG等の場合）
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                quality = 95
                while True:
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=True)
                    buf.seek(0)
                    if buf.getbuffer().nbytes <= max_size or quality <= 10:
                        break
                    quality -= 10
                file_obj = buf
                send_filename = os.path.splitext(filename)[0] + ".jpg"
                print(f"Compressed {filename} to {buf.getbuffer().nbytes/1024/1024:.2f}MB (quality={quality})")
        except Exception as e:
            print(f"JPEG変換失敗: {e}")
            return
    else:
        file_obj = open(file_path, 'rb')

    print(f"New image detected: {filename}. Posting to Discord...")
    try:
        # Wait a moment for the file to be fully written
        time.sleep(1)
        files = {'file': (send_filename, file_obj)}
        msg = filename
        if file_size > max_size:
            msg += "（Discordのファイルサイズ上限10MBを超えていたためjpgに変換されました。）"
        payload = {'content': msg}
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
    finally:
        if file_obj and not isinstance(file_obj, io.BytesIO):
            file_obj.close()

def check_webhook_url(url):
    """Discord Webhook URLが有効かどうかを判定する（テストメッセージ送信）"""
    try:
        response = requests.post(url, data={"content": "Webhook 設定完了！"})
        if response.status_code == 204 or response.status_code == 200:
            return True
        else:
            print(f"Webhook確認失敗: status={response.status_code}")
            return False
    except Exception as e:
        print(f"Webhook確認エラー: {e}")
        return False

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

def run_observer(observer, watch_dir):
    """Runs the watchdog observer loop."""
    print(f"Monitoring directory: {watch_dir}")
    print(f"Posting new images to Discord webhook...")
    observer.start()
    try:
        observer.join() # Blocks until observer.stop() is called
    finally:
        if observer.is_alive(): # Ensure stop if join returns unexpectedly
            observer.stop()
            observer.join() # Wait for stop to complete
        print("Observer stopped.")

# --- Helper: 最新年月フォルダ取得 ---
def get_latest_year_month_folder():
    folders = [f for f in os.listdir(BASE_WATCH_DIRECTORY)
               if os.path.isdir(os.path.join(BASE_WATCH_DIRECTORY, f)) and
               f.startswith("20") and "-" in f]
    if not folders:
        return None
    # YYYY-MM形式でソート
    folders.sort(reverse=True)
    return os.path.join(BASE_WATCH_DIRECTORY, folders[0])

# --- 画像監視Observer管理 ---
image_observer = None

def start_image_observer(watch_dir):
    global image_observer
    if image_observer:
        image_observer.stop()
        image_observer.join()
    if not os.path.isdir(watch_dir):
        print(f"画像監視対象フォルダが存在しません: {watch_dir}")
        return
    event_handler = NewImageHandler()
    image_observer = Observer()
    image_observer.schedule(event_handler, watch_dir, recursive=False)
    threading.Thread(target=run_observer, args=(image_observer, watch_dir), daemon=True).start()
    print(f"画像監視を開始: {watch_dir}")

# --- 親フォルダ監視イベントハンドラ ---
class FolderCreateHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            print(f"新しいフォルダ検知: {event.src_path}")
            latest_folder = get_latest_year_month_folder()
            if latest_folder:
                start_image_observer(latest_folder)

def run_monitoring():
    # --- 親フォルダ監視Observerセットアップ ---
    if not os.path.isdir(BASE_WATCH_DIRECTORY):
        print(f"親フォルダが存在しません: {BASE_WATCH_DIRECTORY}")
        return False

    # 最初の画像監視
    latest_folder = get_latest_year_month_folder()
    if latest_folder:
        start_image_observer(latest_folder)
    else:
        print("監視対象となる年月フォルダがありません。")
        return False

    # 親フォルダ監視開始
    parent_handler = FolderCreateHandler()
    parent_observer = Observer()
    parent_observer.schedule(parent_handler, BASE_WATCH_DIRECTORY, recursive=False)
    print(f"親フォルダ監視開始: {BASE_WATCH_DIRECTORY}")
    parent_observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("終了処理中...")
        parent_observer.stop()
        parent_observer.join()
        if image_observer:
            image_observer.stop()
            image_observer.join()
        print("全ての監視を終了しました。")
    return True

if __name__ == "__main__":
    run_monitoring()