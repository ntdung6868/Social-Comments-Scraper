import time
import json
import os
import glob
import random
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- 1. KHỞI TẠO DRIVER ---
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    if os.name == 'nt':
        service.creation_flags = 0x08000000 
    
    driver = webdriver.Chrome(service=service, options=options)
    
    # 320px Mobile View
    try:
        driver.maximize_window()
        time.sleep(0.3)
        h = driver.get_window_size()["height"]
        driver.set_window_rect(x=0, y=0, width=320, height=h)
    except: pass

    return driver

# --- 2. CÁC HÀM HỖ TRỢ ---
def load_cookies_from_json(cookie_file_path):
    try:
        with open(cookie_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'cookies' in data: return data['cookies']
        if isinstance(data, list): return data
        return []
    except: return []

def apply_cookies_to_driver(driver, cookies):
    if not cookies: return False
    try:
        driver.get("https://www.tiktok.com")
        time.sleep(2)
        driver.delete_all_cookies()
        for cookie in cookies:
            try:
                selenium_cookie = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.tiktok.com'),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', False)
                }
                driver.add_cookie(selenium_cookie)
            except: continue
        driver.refresh()
        time.sleep(2)
        return True
    except: return False

def extract_userid_from_url(url):
    try:
        if "@" in url:
            part = url.split("@")[1]
            return f"@{part.split('?')[0].split('/')[0]}"
    except: pass
    return "Unknown_ID"

def click_first_comment_button(driver, log_func=print):
    log_func("⏳ Đang tìm nút bình luận...")
    try:
        wait = WebDriverWait(driver, 10)
        selectors = [
            "//div[@id='column-list-container']//button[contains(@aria-label, 'comment')]",
            "//span[@data-e2e='comment-icon']/ancestor::button",
            "//strong[@data-e2e='comment-count']/ancestor::button"
        ]
        
        button = None
        for xpath in selectors:
            try:
                button = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                if button: break
            except: continue
            
        if button:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", button)
            log_func("✅ Đã click mở bình luận.")
            return True
        else:
            log_func("⚠️ Không tìm thấy nút bình luận (Có thể đã mở sẵn).")
            return False
    except Exception as e:
        log_func(f"⚠️ Lỗi tìm nút: {e}")
        return False

def is_captcha_overlay_present(driver):
    try:
        overlay = driver.find_elements(By.CSS_SELECTOR, '.captcha-verify-container, #captcha-verify-container-main-page')
        if len(overlay) > 0 and overlay[0].is_displayed():
            return True
        return False
    except: return False

def wait_captcha_solved_if_any(driver, log_func=print, max_wait_seconds=300):
    if not is_captcha_overlay_present(driver):
        return

    log_func("\n[!] 🛑 PHÁT HIỆN CAPTCHA! Vui lòng giải tay...")
    
    waited = 0
    while waited < max_wait_seconds:
        if not is_captcha_overlay_present(driver):
            log_func("✅ Đã giải xong captcha!")
            time.sleep(2)
            return
        time.sleep(2)
        waited += 2
        if waited % 10 == 0: log_func(f"    ... đang chờ ({waited}s)...")

    log_func("[!] Hết thời gian chờ.")

# Sleep có kiểm tra stop_event để dừng sớm
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

# --- 3. HÀM CHẠY CHÍNH ---
def scrape_level1_window_mode(video_url, cookie_file_path=None, log_callback=None, stop_event=None):
    def log(msg):
        print(msg)
        if log_callback:
            try: log_callback(msg)
            except: pass

    log("🚀 Đang khởi tạo trình duyệt...")
    try:
        driver = init_driver()
        log("✅ Đã khởi tạo trình duyệt.")
    except Exception as e:
        log(f"❌ Lỗi khởi tạo trình duyệt: {e}")
        return []

    def should_stop():
        return stop_event is not None and stop_event.is_set()

    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []
    
    if cookie_file_path:
        log(f"🍪 Đang nạp cookie...")
        try:
            cookies = load_cookies_from_json(cookie_file_path)
            if apply_cookies_to_driver(driver, cookies):
                log("✅ Đã nạp xong cookie.")
            else:
                 log("⚠️ Có thể lỗi nạp cookie (hoặc cookie hết hạn).")
        except Exception as e:
            log(f"❌ Lỗi nạp cookie: {e}")

    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []
    
    log(f"🌍 Đang truy cập: {video_url}")
    driver.get(video_url)
    if sleep_with_stop(2, stop_event):
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    click_first_comment_button(driver, log)
    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    wait_captcha_solved_if_any(driver, log)

    if should_stop():
        try: driver.quit()
        except: pass
        log("\n🛑 Đã dừng theo yêu cầu.")
        return []

    data_set = set() 
    final_list = []
    scroll_attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    captcha_check_counter = 0
    
    log("\n⬇️  Bắt đầu quét comment...")

    while True:
        if should_stop():
            log("\n🛑 Đã dừng theo yêu cầu.")
            break
        
        captcha_check_counter += 1
        if captcha_check_counter >= 5:
            wait_captcha_solved_if_any(driver, log)
            captcha_check_counter = 0
        
        try:
            comment_text_elements = driver.find_elements(By.CSS_SELECTOR, '[data-e2e="comment-level-1"]')
        except: comment_text_elements = []

        count_new_in_loop = 0
        
        for text_el in comment_text_elements:
            try:
                comment_text = text_el.text.strip()
                if not comment_text: continue

                user_id = "Unknown"
                try:
                    user_link_el = text_el.find_element(By.XPATH, "./ancestor::div[1]//a[contains(@href, '@')][1]")
                    user_link = user_link_el.get_attribute('href')
                    user_id = extract_userid_from_url(user_link)
                except:
                    try:
                        user_id = extract_userid_from_url(text_el.find_element(By.XPATH, "./preceding::a[contains(@href, '@')][1]").get_attribute('href'))
                    except: pass


                unique_key = (user_id, comment_text)
                
                if unique_key not in data_set:
                    data_set.add(unique_key)
                    final_list.append({
                        "User ID": user_id, 
                        "Comment": comment_text
                    })
                    count_new_in_loop += 1
                    log(f"   + {user_id}: {comment_text[:40].replace(chr(10), ' ')}...")
            
            except Exception: continue

        if count_new_in_loop > 0:
            scroll_attempts = 0
            log(f"✅ Lấy thêm {count_new_in_loop} (Tổng: {len(final_list)})")
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        if sleep_with_stop(random.uniform(1.0, 2.0), stop_event):
            log("\n🛑 Đã dừng theo yêu cầu.")
            break

        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            scroll_attempts += 1
            log(f"⏳ Đang thử cuộn lại... ({scroll_attempts}/2)")
            driver.execute_script("window.scrollBy(0, -400);")
            if sleep_with_stop(0.5, stop_event):
                log("\n🛑 Đã dừng theo yêu cầu.")
                break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            if sleep_with_stop(1.5, stop_event):
                log("\n🛑 Đã dừng theo yêu cầu.")
                break
            if scroll_attempts >= 2:
                log("🛑 Đã hết comment.")
                break
        else:
            last_height = new_height

    try: driver.quit()
    except: pass

    return final_list

# Alias
run_tiktok_scraper = scrape_level1_window_mode

if __name__ == "__main__":
    link = input("👉 Nhập link TikTok: ")
    data = scrape_level1_window_mode(link)
    if data:
        # Thử lưu CSV nếu Excel vẫn lỗi (Backup plan)
        df = pd.DataFrame(data)
        file_name = f"tiktok_fixed.xlsx"
        try:
            df.to_excel(file_name, index=False)
            print(f"✅ Đã lưu Excel: {file_name}")
        except Exception as e:
            print(f"❌ Lỗi lưu Excel: {e}")
            csv_name = "tiktok_backup.csv"
            df.to_csv(csv_name, index=False, encoding='utf-8-sig')
            print(f"✅ Đã lưu CSV thay thế: {csv_name}")