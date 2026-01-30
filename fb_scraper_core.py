import time
import json
import os
import re
import shutil
import pandas as pd
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 1. KHỞI TẠO DRIVER ---
def _should_run_headless():
    if "HEADLESS" in os.environ:
        return os.environ.get("HEADLESS", "1") != "0"
    if os.name in ("nt", "darwin"):
        return False
    if os.environ.get("DISPLAY"):
        return False
    return True


def init_driver(headless=None, debugger_address=None):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument("--disable-blink-features=AutomationControlled")

    if debugger_address:
        options.add_experimental_option("debuggerAddress", debugger_address)
    
    if headless is None:
        headless = _should_run_headless()
    if headless and not debugger_address:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,720")

    chrome_bin = os.environ.get("CHROME_BIN") or os.environ.get("GOOGLE_CHROME_BIN")
    if not chrome_bin:
        for path in ("/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"):
            if os.path.exists(path):
                chrome_bin = path
                break
    if chrome_bin:
        options.binary_location = chrome_bin

    driver_path = (
        os.environ.get("CHROMEDRIVER_PATH")
        or shutil.which("chromedriver")
        or shutil.which("chromium-driver")
    )
    service = Service(driver_path) if driver_path else Service(ChromeDriverManager().install())
    if os.name == 'nt':
        service.creation_flags = 0x08000000 
    
    driver = webdriver.Chrome(service=service, options=options)
    
    # Mobile View
    try:
        driver.maximize_window()
        time.sleep(0.3)
        h = driver.get_window_size()["height"]
        driver.set_window_rect(x=0, y=0, width=420, height=h)
    except: pass
    return driver

# --- 2. XỬ LÝ DỮ LIỆU ---
def extract_id_from_url(url):
    if not url: return "Unknown"
    try:
        parsed = urlparse(url)
        if "profile.php" in parsed.path:
            query = parse_qs(parsed.query)
            if 'id' in query: return query['id'][0]
        path_parts = parsed.path.strip("/").split("/")
        if path_parts: return path_parts[0]
    except: pass
    return "Unknown"

def is_junk_line(text):
    t = text.strip().lower()
    junk_phrases = [
        "thích", "trả lời", "phản hồi", "chia sẻ", "xem thêm", 
        "viết bình luận", "bình luận", "like", "reply", "share", 
        "phù hợp nhất", "tất cả bình luận", "xem bản dịch", 
        "theo dõi", "follow", "đang theo dõi", "đã chỉnh sửa", "tác giả", "top fan"
    ]
    if t in junk_phrases: return True
    time_patterns = [r"^\d+\s?(giờ|phút|giây|ngày|tuần|năm|h|m|d|y|w)$", r"^vừa xong$", r"^just now$", r"^\d+$"]
    for p in time_patterns:
        if re.match(p, t): return True
    return False

def sleep_with_stop(seconds, stop_event):
    if not stop_event:
        time.sleep(seconds)
        return False
    end_time = time.time() + seconds
    while time.time() < end_time:
        if stop_event.is_set():
            return True
        time.sleep(0.1)
    return False

def get_scroll_target(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"]')
    except Exception:
        pass
    try:
        return driver.execute_script("return document.scrollingElement || document.documentElement;")
    except Exception:
        return None

# --- 3. HÀM CHẠY CHÍNH ---
def run_facebook_scraper(
    post_url,
    cookie_path,
    log_callback,
    stop_event,
    headless=None,
    debugger_address=None,
):
    def log(msg):
        if log_callback: log_callback(msg)
        else: print(msg)

    driver = init_driver(headless=headless, debugger_address=debugger_address)
    scroll_target = None

    def should_stop():
        return stop_event is not None and stop_event.is_set()
    
    # NẠP COOKIE
    if cookie_path and os.path.exists(cookie_path):
        log(f"🍪 Đang nạp cookie...")
        try:
            driver.get("https://www.facebook.com")
            if sleep_with_stop(1, stop_event):
                try: driver.quit()
                except: pass
                log("\n🛑 Đã dừng theo yêu cầu.")
                return []
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                if isinstance(cookies, dict) and "cookies" in cookies: cookies = cookies["cookies"]
            count = 0
            for c in cookies:
                try: 
                    driver.add_cookie({'name': c['name'], 'value': c['value'], 'domain': '.facebook.com', 'path': '/', 'secure': True})
                    count += 1
                except: pass
            driver.refresh()
            if sleep_with_stop(1.5, stop_event):
                try: driver.quit()
                except: pass
                log("\n🛑 Đã dừng theo yêu cầu.")
                return []
            log(f"✅ Đã nạp {count} cookie.")
        except Exception as e:
            log(f"❌ Lỗi nạp cookie: {e}")
    else:
        log("⚠️ Chạy không cookie (Cần đăng nhập tay).")

    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    log(f"🌍 Đang vào bài viết...")
    driver.get(post_url)
    if sleep_with_stop(2, stop_event):
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="article"]')))
    except Exception:
        pass

    # CHUYỂN BỘ LỌC
    log("🔄 Đang chuyển bộ lọc 'Tất cả bình luận'...")
    try:
        filter_xpath = "//span[contains(text(), 'Phù hợp nhất') or contains(text(), 'Most relevant')]"
        trigger = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, filter_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'}); arguments[0].click();", trigger)
        if sleep_with_stop(1, stop_event):
            try: driver.quit()
            except: pass
            log("\n🛑 Đã dừng theo yêu cầu.")
            return []
        
        all_xpath = "//span[contains(text(), 'Tất cả bình luận') or contains(text(), 'All comments')]"
        option = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, all_xpath)))
        driver.execute_script("arguments[0].click();", option)
        log("✅ Đã chuyển bộ lọc!")
        if sleep_with_stop(1.2, stop_event):
            try: driver.quit()
            except: pass
            log("\n🛑 Đã dừng theo yêu cầu.")
            return []
    except:
        log("⚠️ Không tìm thấy bộ lọc (Có thể đã đúng sẵn).")

    data_set = set()
    final_list = []
    no_new_data_count = 0
    
    log("⬇️  Bắt đầu quét...")

    while True:
        # CHECK DỪNG NGAY ĐẦU VÒNG LẶP
        if should_stop():
            break

        try:
            if not scroll_target:
                scroll_target = get_scroll_target(driver)
            else:
                _ = scroll_target.tag_name
        except Exception:
            scroll_target = get_scroll_target(driver)

        try: container = driver.find_element(By.CSS_SELECTOR, 'div[role="dialog"]')
        except: container = driver

        comments = container.find_elements(By.CSS_SELECTOR, 'div[role="article"]')
        if len(comments) < 2:
            comments = container.find_elements(By.CSS_SELECTOR, 'div[aria-label]')

        count_new = 0
        for item in comments:
            try:
                # Lấy ID
                user_id = "Unknown"
                try:
                    link_el = item.find_element(By.TAG_NAME, "a")
                    user_id = extract_id_from_url(link_el.get_attribute("href"))
                except: pass

                # Lấy Nội dung + Icon
                raw_text = item.text.strip()
                emoji_text = ""
                try:
                    content_div = item.find_element(By.CSS_SELECTOR, "div[dir='auto']")
                    imgs = content_div.find_elements(By.TAG_NAME, "img")
                    for img in imgs:
                        alt = img.get_attribute("alt")
                        if alt: emoji_text += alt + " "
                except: pass

                # 3. LẤY TEXT VÀ LỌC TÊN
                raw_text = item.text.strip()
                if not raw_text and not emoji_text: continue
                
                all_lines = raw_text.split('\n')
                # Lọc rác (thời gian, reply, like...)
                clean_lines = [line for line in all_lines if not is_junk_line(line)]
                
                comment_content = ""
                
                # --- LOGIC FIX LỖI LẤY TÊN ---
                # Facebook luôn xếp: [Dòng 1: Tên] [Dòng 2 trở đi: Nội dung]
                # Vì vậy ta LUÔN LUÔN bỏ dòng đầu tiên (clean_lines[0])
                
                if len(clean_lines) >= 2:
                    # Nếu có từ 2 dòng trở lên -> Dòng 1 là tên -> Lấy từ dòng 2
                    comment_content = "\n".join(clean_lines[1:])
                elif len(clean_lines) == 1:
                    # Nếu chỉ còn 1 dòng duy nhất -> 99% đó là Tên hiển thị (vì nội dung rỗng hoặc chỉ có ảnh)
                    # Nên ta bỏ qua dòng này luôn
                    comment_content = "" 
                
                # Ghép text với emoji
                final_content = (comment_content + " " + emoji_text).strip()
                
                # Nếu sau khi lọc mà rỗng thì gán nhãn
                if not final_content: final_content = "[Ảnh/Sticker/GIF]"

                key = (user_id, final_content)
                if key not in data_set:
                    data_set.add(key)
                    final_list.append({"User ID": user_id, "Comment": final_content})
                    count_new += 1
                    # Log gọn (bỏ xuống dòng)
                    log(f"   + {user_id}: {final_content[:30].replace(chr(10), ' ')}...")

            except: continue

        if count_new > 0:
            no_new_data_count = 0
            log(f"✅ Lấy thêm {count_new} (Tổng: {len(final_list)})")
        else:
            no_new_data_count += 1
            log(f"⏳ Đang thử cuộn lại... ({no_new_data_count}/2)")
        
        # JS Scroll
        driver.execute_script("""
        var dialog = document.querySelector('div[role="dialog"]');
        var target = dialog ? dialog : document;
        var divs = target.querySelectorAll('div');
        for (var i = 0; i < divs.length; i++) {
            var d = divs[i];
            if (d.scrollHeight > d.clientHeight && d.clientHeight > 100) {
                if (d.querySelector('div[role="article"]')) {
                    d.scrollTop = d.scrollHeight;
                }
            }
        }
        window.scrollTo(0, document.body.scrollHeight);
        """)
        
        # Ngủ và check dừng liên tục để phản hồi nhanh
        for _ in range(5):
            if should_stop():
                break
            time.sleep(0.5)

        if no_new_data_count >= 2:
            log("🛑 Đã hết dữ liệu.")
            break

    driver.quit()
    return final_list