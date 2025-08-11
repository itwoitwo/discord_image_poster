import tkinter as tk
from tkinter import filedialog
import threading
import discord_image_poster  # 既存ロジックを利用
import sys
import os
import json
import pystray
from PIL import Image, ImageDraw


# 設定ファイルのパス（%APPDATA%\Roaming\vrc_picture_to_discord\config.json）
def get_config_path():
    appdata = os.getenv("APPDATA")
    config_dir = os.path.join(appdata, "vrc_picture_to_discord")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "config.json")

def save_config(folder, webhook):
    config = {"folder": folder, "webhook": webhook}
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f)

def load_config():
    try:
        with open(get_config_path(), "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("folder", ""), config.get("webhook", "")
    except Exception:
        return "", ""

def start_monitoring():
    folder = folder_var.get()
    webhook = webhook_var.get()
    if not folder or not webhook:
        tk.messagebox.showerror("エラー", "監視フォルダとWebhook URLを入力してください。")
        return
    discord_image_poster.BASE_WATCH_DIRECTORY = folder
    discord_image_poster.DISCORD_WEBHOOK_URL = webhook

    def run_monitor():
        result = discord_image_poster.run_monitoring()
        if not result:
            tk.messagebox.showerror("監視開始失敗", "監視対象フォルダが存在しないか、監視できませんでした。")

    def monitor_and_minimize():
        # Webhook URLの正当性チェック
        if not discord_image_poster.check_webhook_url(webhook):
            tk.messagebox.showerror("Webhookエラー", "Webhook URLが正しくありません。")
            return
        # 設定保存
        save_config(folder, webhook)
        # 監視開始（非同期）
        threading.Thread(target=run_monitor, daemon=True).start()
        minimize_to_tray()

    threading.Thread(target=monitor_and_minimize, daemon=True).start()

def minimize_to_tray():
    root.withdraw()
    icon = create_tray_icon()
    icon.run()

def create_tray_icon():
    exe_dir = os.path.dirname(sys.argv[0])
    icon_path = os.path.join(exe_dir, "tray_icon.png")
    try:
        image = Image.open(icon_path)
    except Exception:
        image = Image.new('RGB', (64, 64), color=(60, 60, 60))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill=(114, 137, 218))
    def on_show_window(icon, item):
        root.deiconify()
        icon.stop()
    icon = pystray.Icon("vrc_picture_to_discord", image, "Discord画像自動投稿", menu=pystray.Menu(
        pystray.MenuItem("設定を表示", on_show_window),
        pystray.MenuItem("終了", on_exit)
    ))
    return icon

def on_exit(icon, item):
    icon.stop()
    root.destroy()

root = tk.Tk()
root.title("Discord画像自動投稿")

# 設定ファイル読込＆自動監視
config_folder, config_webhook = load_config()
folder_var = tk.StringVar(value=config_folder)
webhook_var = tk.StringVar(value=config_webhook)

def auto_start_monitoring():
    if config_folder and config_webhook:
        discord_image_poster.BASE_WATCH_DIRECTORY = config_folder
        discord_image_poster.DISCORD_WEBHOOK_URL = config_webhook
        # 監視開始（非同期）
        threading.Thread(target=discord_image_poster.run_monitoring, daemon=True).start()
        # 最小化
        minimize_to_tray()

tk.Label(root, text="VRChatフォルダ:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
folder_entry = tk.Entry(root, textvariable=folder_var, width=40)
folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)
tk.Button(root, text="選択", command=select_folder, width=10).grid(row=0, column=2, padx=5, pady=5)

tk.Label(root, text="Discord Webhook URL:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
webhook_entry = tk.Entry(root, textvariable=webhook_var, width=40)
webhook_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
tk.Label(root, text="").grid(row=1, column=2)

tk.Button(root, text="スタート", command=start_monitoring, width=20).grid(row=2, column=0, columnspan=3, pady=15)

root.grid_columnconfigure(1, weight=1)

# 起動時に自動監視
root.after(100, auto_start_monitoring)

root.mainloop()
