import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import discord_image_poster  # 既存ロジックを利用

def start_monitoring():
    folder = folder_var.get()
    webhook = webhook_var.get()
    if not folder or not webhook:
        messagebox.showerror("エラー", "VRChatフォルダとWebhook URLを入力してください。")
        return
    discord_image_poster.BASE_WATCH_DIRECTORY = folder
    discord_image_poster.DISCORD_WEBHOOK_URL = webhook
    threading.Thread(target=discord_image_poster.run_monitoring, daemon=True).start()
    messagebox.showinfo("監視開始", f"監視を開始しました。\nフォルダ: {folder}")

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
# 空のcolumn=2でスペースを揃える
tk.Label(root, text="").grid(row=1, column=2)

tk.Button(root, text="スタート", command=start_monitoring, width=20).grid(row=2, column=0, columnspan=3, pady=15)

root.grid_columnconfigure(1, weight=1)
root.mainloop()
