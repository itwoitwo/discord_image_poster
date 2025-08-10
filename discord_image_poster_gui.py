import tkinter as tk
from tkinter import filedialog
import threading
import discord_image_poster  # 既存ロジックを利用
import sys
import os
import pystray
from PIL import Image, ImageDraw

def start_monitoring():
    folder = folder_var.get()
    webhook = webhook_var.get()
    if not folder or not webhook:
        tk.messagebox.showerror("エラー", "監視フォルダとWebhook URLを入力してください。")
        return
    discord_image_poster.BASE_WATCH_DIRECTORY = folder
    discord_image_poster.DISCORD_WEBHOOK_URL = webhook
    def monitor_and_minimize():
        result = discord_image_poster.run_monitoring()
        if result:
            minimize_to_tray()
        else:
            tk.messagebox.showerror("監視開始失敗", "監視対象フォルダが存在しないか、監視できませんでした。")
    threading.Thread(target=monitor_and_minimize, daemon=True).start()

def minimize_to_tray():
    root.withdraw()
    icon = create_tray_icon()
    icon.run()

def create_tray_icon():
    # nuitkaビルド対応: 実行ファイルのディレクトリからアイコン画像を取得
    exe_dir = os.path.dirname(sys.argv[0])
    icon_path = os.path.join(exe_dir, "tray_icon.png")
    try:
        image = Image.open(icon_path)
    except Exception:
        # ファイルがない場合はデフォルトアイコン
        image = Image.new('RGB', (64, 64), color=(60, 60, 60))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill=(114, 137, 218))
    icon = pystray.Icon("discord_image_poster", image, "Discord画像自動投稿", menu=pystray.Menu(
        pystray.MenuItem("終了", on_exit)
    ))
    return icon

def on_exit(icon, item):
    icon.stop()
    root.destroy()

root = tk.Tk()
root.title("Discord画像自動投稿")

tk.Label(root, text="VRChatフォルダ:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
folder_var = tk.StringVar()
folder_entry = tk.Entry(root, textvariable=folder_var, width=40)
folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky="we")
def select_folder():
    folder = filedialog.askdirectory()
    if folder:
        folder_var.set(folder)
tk.Button(root, text="選択", command=select_folder, width=10).grid(row=0, column=2, padx=5, pady=5)

tk.Label(root, text="Discord Webhook URL:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
webhook_var = tk.StringVar()
webhook_entry = tk.Entry(root, textvariable=webhook_var, width=40)
webhook_entry.grid(row=1, column=1, padx=5, pady=5, sticky="we")
tk.Label(root, text="").grid(row=1, column=2)

tk.Button(root, text="スタート", command=start_monitoring, width=20).grid(row=2, column=0, columnspan=3, pady=15)

root.grid_columnconfigure(1, weight=1)
root.mainloop()
