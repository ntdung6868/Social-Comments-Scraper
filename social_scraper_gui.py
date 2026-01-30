import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import json
import pandas as pd
import os
import time
from pathlib import Path
import re
import importlib
import sys

try:
    _tkdnd = importlib.import_module("tkinterdnd2")
    DND_FILES = _tkdnd.DND_FILES
    TkinterDnD = _tkdnd.TkinterDnD
except Exception:
    print("❌ LỖI: Chưa cài tkinterdnd2. Hãy cài bằng: pip install tkinterdnd2")
    sys.exit(1)

# Import logic (Bắt buộc để chung thư mục)
try:
    from tiktok_scraper_core import run_tiktok_scraper
except ImportError:
    print("❌ LỖI: Không tìm thấy file tiktok_scraper_core.py")
    exit()

try:
    from fb_scraper_core import run_facebook_scraper
except ImportError:
    print("❌ LỖI: Không tìm thấy file fb_scraper_core.py")
    exit()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class TikTokApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Social Comment Scraper")
        self.geometry("840x840")
        self.resizable(False, False)
        self.center_window()

        self.colors = {
            "bg": "#0f1115",
            "panel": "#151a22",
            "panel_alt": "#1b2230",
            "border": "#2a3342",
            "text": "#e6e9ef",
            "muted": "#9aa4b2",
            "accent": "#4f8cff",
            "accent_hover": "#3b82f6",
            "success": "#22c55e",
            "success_hover": "#16a34a",
            "danger": "#ef4444",
            "danger_hover": "#dc2626",
            "input": "#111827"
        }

        try:
            self.configure(bg=self.colors["bg"])
        except Exception:
            pass

        self.root = ctk.CTkFrame(self, fg_color=self.colors["bg"])
        self.root.pack(fill="both", expand=True)

        self.stop_event = threading.Event()
        self.cookie_path = ctk.StringVar()
        self.cookie_display = ctk.StringVar(value="Chưa chọn file.")
        self.platform = ctk.StringVar(value="TikTok")

        # UI Header
        ctk.CTkLabel(
            self.root,
            text="SOCIAL COMMENT SCRAPER",
            font=("Arial", 22, "bold"),
            text_color=self.colors["text"]
        ).pack(pady=(20, 10))

        # Platform Selector
        self.frame_platform = ctk.CTkFrame(
            self.root,
            fg_color=self.colors["panel"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=14
        )
        self.frame_platform.pack(pady=8, padx=20, fill="x")
        ctk.CTkLabel(
            self.frame_platform,
            text="Nền tảng",
            text_color=self.colors["muted"]
        ).pack(anchor="w", padx=12, pady=(8, 4))
        self.platform_menu = ctk.CTkSegmentedButton(
            self.frame_platform,
            values=["TikTok", "Facebook"],
            variable=self.platform,
            command=self.on_platform_change,
            fg_color=self.colors["panel_alt"],
            selected_color=self.colors["accent"],
            selected_hover_color=self.colors["accent_hover"],
            unselected_color=self.colors["panel_alt"],
            unselected_hover_color=self.colors["panel"],
            text_color=self.colors["text"]
        )
        self.platform_menu.pack(fill="x", padx=12, pady=(0, 10))
        
        # Link Input
        self.frame_input = ctk.CTkFrame(
            self.root,
            fg_color=self.colors["panel"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=14
        )
        self.frame_input.pack(pady=8, padx=20, fill="x")
        self.label_link = ctk.CTkLabel(
            self.frame_input,
            text="Link Video",
            text_color=self.colors["muted"]
        )
        self.label_link.pack(anchor="w", padx=12, pady=(8, 4))
        self.entry_link = ctk.CTkEntry(
            self.frame_input,
            placeholder_text="https://www.tiktok.com/@user/video/...",
            fg_color=self.colors["input"],
            border_color=self.colors["border"],
            text_color=self.colors["text"],
            placeholder_text_color=self.colors["muted"]
        )
        self.entry_link.pack(fill="x", padx=12, pady=(0, 12))

        # Cookie Input
        self.frame_cookie = ctk.CTkFrame(
            self.root,
            fg_color=self.colors["panel"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=14
        )
        self.frame_cookie.pack(pady=8, padx=20, fill="x")
        ctk.CTkLabel(
            self.frame_cookie,
            text="File Cookie (JSON)",
            text_color=self.colors["muted"]
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.cookie_drop = ctk.CTkFrame(
            self.frame_cookie,
            fg_color=self.colors["panel_alt"],
            border_width=1,
            border_color=self.colors["border"],
            corner_radius=12
        )
        self.cookie_drop.pack(fill="x", padx=12, pady=(0, 12))

        self.cookie_hint = ctk.CTkLabel(
            self.cookie_drop,
            text="Kéo-thả tệp JSON vào đây\nhoặc bấm Chọn File",
            justify="center",
            text_color=self.colors["muted"]
        )
        self.cookie_hint.pack(pady=(12, 6))

        self.cookie_value = ctk.CTkLabel(
            self.cookie_drop,
            textvariable=self.cookie_display,
            justify="center",
            wraplength=320,
            text_color=self.colors["text"]
        )
        self.cookie_value.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(
            self.cookie_drop,
            text="Chọn File",
            width=120,
            command=self.browse_file,
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"]
        ).pack(pady=(0, 12))

        self.cookie_drop.drop_target_register(DND_FILES)
        self.cookie_drop.dnd_bind("<<Drop>>", self.on_drop_cookie)
        self.cookie_hint.drop_target_register(DND_FILES)
        self.cookie_hint.dnd_bind("<<Drop>>", self.on_drop_cookie)

        # --- NÚT BẤM (NGANG HÀNG) ---
        self.frame_actions = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_actions.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.frame_actions, text="BẮT ĐẦU", command=self.on_start, 
                                       fg_color=self.colors["success"], hover_color=self.colors["success_hover"], 
                                       width=170, height=48, font=("Arial", 14, "bold"),
                                       corner_radius=22)
        self.btn_start.pack(side="left", padx=12)
        
        self.btn_stop = ctk.CTkButton(self.frame_actions, text="DỪNG LẠI", command=self.on_stop, 
                                      fg_color=self.colors["danger"], hover_color=self.colors["danger_hover"], 
                                      width=170, height=48, font=("Arial", 14, "bold"),
                                      corner_radius=22,
                                      state="disabled")
        self.btn_stop.pack(side="left", padx=12)
        # ----------------------------

        # Real-Time Analytics
        self.frame_analytics = ctk.CTkFrame(self.root, fg_color="transparent")
        self.frame_analytics.pack(pady=(6, 8), padx=20, fill="x")

        self.analytics_card = ctk.CTkFrame(
            self.frame_analytics,
            fg_color=self.colors["panel_alt"],
            corner_radius=18,
            border_width=1,
            border_color=self.colors["border"]
        )
        self.analytics_card.pack(fill="x", pady=(8, 0))

        self.analytics_title = ctk.CTkLabel(
            self.analytics_card,
            text="Real-Time Analytics",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"]
        )
        self.analytics_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(10, 6))

        self.comments_label = ctk.CTkLabel(
            self.analytics_card,
            text="Comments Scraped",
            text_color=self.colors["muted"]
        )
        self.comments_label.grid(row=1, column=0, sticky="w", padx=14)
        self.comments_value = ctk.CTkLabel(
            self.analytics_card,
            text="0",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        )
        self.comments_value.grid(row=2, column=0, sticky="w", padx=14, pady=(2, 12))

        self.time_label = ctk.CTkLabel(
            self.analytics_card,
            text="Time Elapsed",
            text_color=self.colors["muted"]
        )
        self.time_label.grid(row=1, column=1, sticky="w", padx=14)
        self.time_value = ctk.CTkLabel(
            self.analytics_card,
            text="00:00:00",
            font=("Arial", 18, "bold"),
            text_color=self.colors["text"]
        )
        self.time_value.grid(row=2, column=1, sticky="w", padx=14, pady=(2, 12))

        self.analytics_card.grid_columnconfigure(0, weight=1)
        self.analytics_card.grid_columnconfigure(1, weight=1)

        self.comments_count = 0
        self.start_time = None
        self.timer_job = None

        # Log Box
        self.log_box = ctk.CTkTextbox(
            self.root,
            height=170,
            fg_color=self.colors["panel"],
            border_color=self.colors["border"],
            text_color=self.colors["text"]
        )
        self.log_box.pack(pady=8, padx=20, fill="both")
        self.log("👋 Sẵn sàng. Chọn nền tảng, nhập link và cookie để bắt đầu.")

    def browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if f:
            self.set_cookie_path(f)

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def on_drop_cookie(self, event):
        try:
            paths = list(self.tk.splitlist(event.data))
        except Exception:
            paths = [event.data]
        if not paths:
            return

        json_paths = [p for p in paths if p.lower().endswith(".json")]
        selected = json_paths[0] if json_paths else paths[0]

        if not selected.lower().endswith(".json"):
            messagebox.showwarning("Sai định dạng", "Vui lòng thả file JSON.")
            return

        self.set_cookie_path(selected)

    def set_cookie_path(self, path):
        self.cookie_path.set(path)
        if path:
            self.cookie_display.set(path)
        else:
            self.cookie_display.set("Chưa chọn file.")

    def on_platform_change(self, value):
        self.set_cookie_path("")
        self.entry_link.delete(0, "end")
        if value == "Facebook":
            self.label_link.configure(text="Link Bài viết")
            self.entry_link.configure(placeholder_text="https://www.facebook.com/....")
        else:
            self.label_link.configure(text="Link Video")
            self.entry_link.configure(placeholder_text="https://www.tiktok.com/@user/video/...")
        self.root.focus_set()
        self.log(f"🔁 Đã chuyển nền tảng: {value}")

    def _is_link_valid(self, link, platform):
        l = (link or "").lower().strip()
        p = (platform or "").lower().strip()
        is_tiktok = "tiktok" in p
        is_facebook = "facebook" in p
        if is_tiktok:
            return "tiktok.com" in l and "facebook.com" not in l and "fb.watch" not in l and "fb.com" not in l
        if is_facebook:
            return ("facebook.com" in l or "fb.watch" in l or "fb.com" in l) and "tiktok.com" not in l
        return False

    def _is_cookie_valid(self, cookie_path, platform):
        if not cookie_path:
            return True
        if not os.path.exists(cookie_path):
            return False
        try:
            with open(cookie_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cookies = data.get("cookies") if isinstance(data, dict) else data
            if not isinstance(cookies, list):
                return False
            domains = []
            for c in cookies:
                if isinstance(c, dict):
                    d = c.get("domain") or c.get("host") or c.get("url") or ""
                    domains.append(str(d).lower())
            if not domains:
                return False
            p = (platform or "").lower().strip()
            is_tiktok = "tiktok" in p
            is_facebook = "facebook" in p
            if is_tiktok:
                return any("tiktok.com" in d or "tiktokv.com" in d for d in domains)
            if is_facebook:
                return any("facebook.com" in d or "fb.com" in d or "messenger.com" in d for d in domains)
            return False
        except Exception:
            return False

    def _warn_async(self, title, msg):
        self.after(0, lambda: messagebox.showwarning(title, msg))

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", str(msg) + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self._sync_analytics_from_log(msg)

    def _sync_analytics_from_log(self, msg):
        try:
            text = str(msg)
        except Exception:
            return
        match = re.search(r"Tổng:\s*(\d+)", text)
        if not match:
            match = re.search(r"Đã lưu\s+(\d+)\s+dòng", text)
        if match:
            self._set_comments_count(int(match.group(1)))

    def _set_comments_count(self, count):
        self.comments_count = count
        self.after(0, lambda: self.comments_value.configure(text=f"{count:,}"))

    def _format_elapsed(self, seconds):
        seconds = max(0, int(seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _start_timer(self):
        self._stop_timer()
        self.start_time = time.time()
        self.time_value.configure(text="00:00:00")
        self._update_timer()

    def _update_timer(self):
        if not self.start_time:
            return
        elapsed = time.time() - self.start_time
        self.time_value.configure(text=self._format_elapsed(elapsed))
        self.timer_job = self.after(1000, self._update_timer)

    def _stop_timer(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
        self.timer_job = None
        self.start_time = None

    def on_start(self):
        link = self.entry_link.get().strip()
        cookie = self.cookie_path.get().strip()
        platform = self.platform.get()
        
        if not link:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Link Video!")
            return

        if not self._is_link_valid(link, platform):
            messagebox.showwarning("Sai nền tảng", "Link không đúng với nền tảng đã chọn.")
            return

        if cookie and not self._is_cookie_valid(cookie, platform):
            messagebox.showwarning("Sai cookie", "File cookie không đúng nền tảng hoặc bị lỗi.")
            return
            
        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self._set_comments_count(0)
        self._start_timer()
        
        threading.Thread(target=self.run_process, args=(link, cookie)).start()

    def on_stop(self):
        self.stop_event.set()
        self.log("🛑 Đang gửi lệnh dừng...")
        self.btn_stop.configure(state="disabled")

    def run_process(self, link, cookie):
        data = []
        # LOGIC BẤT TỬ: Dù chạy lỗi cũng không sập app
        try:
            platform = self.platform.get()
            if not self._is_link_valid(link, platform):
                self.log("❌ Link không đúng nền tảng đã chọn.")
                self._warn_async("Sai nền tảng", "Link không đúng với nền tảng đã chọn.")
                return
            if cookie and not self._is_cookie_valid(cookie, platform):
                self.log("❌ Cookie không đúng nền tảng.")
                self._warn_async("Sai cookie", "File cookie không đúng nền tảng hoặc bị lỗi.")
                return
            if self.platform.get() == "Facebook":
                data = run_facebook_scraper(link, cookie if cookie else None, self.log, self.stop_event)
            else:
                data = run_tiktok_scraper(link, cookie if cookie else None, self.log, self.stop_event)
        except Exception as e:
            self.log(f"\n⚠️ Có lỗi kỹ thuật: {e}")

        # --- LƯU FILE ---
        if data:
            try:
                # Lưu ra Desktop/<platform>-scratched-data
                platform_name = self.platform.get().lower()
                desktop = Path.home() / "Desktop" / f"{platform_name}-scratched-data"
                os.makedirs(desktop, exist_ok=True)
                
                ts = time.strftime("%Y%m%d_%H%M%S")
                filename = desktop / f"{platform_name}_comments_{ts}.xlsx"
                
                pd.DataFrame(data).to_excel(filename, index=False)
                
                self.log(f"\n🎉 HOÀN THÀNH! Đã lưu {len(data)} dòng.")
                self.log(f"📂 File: {filename}")
                
                # Thông báo
                if self.stop_event.is_set():
                    messagebox.showinfo("Thông báo", "Đã dừng theo yêu cầu.")
                else:
                    messagebox.showinfo("Thành công", f"Đã lấy xong {len(data)} bình luận!\nLưu tại: {filename}")
                self._set_comments_count(len(data))
                    
            except Exception as e:
                self.log(f"\n❌ LỖI LƯU FILE: {e}")
                messagebox.showerror("Lỗi", "Không lưu được file (Có thể đang mở).")
        else:
            if self.stop_event.is_set():
                self.log("\n⚠️ Đã dừng (Chưa có dữ liệu).")
                messagebox.showinfo("Thông báo", "Đã dừng theo yêu cầu.")
            else:
                self.log("\n❌ Không lấy được dữ liệu.")
                messagebox.showwarning("Thất bại", "Không tìm thấy bình luận.")

        self._stop_timer()
        if not data and not self.stop_event.is_set():
            self._set_comments_count(0)
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = TikTokApp()
    app.mainloop()