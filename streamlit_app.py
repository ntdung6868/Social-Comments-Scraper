import tempfile
import threading
import re
import io
import json
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from streamlit_autorefresh import st_autorefresh

from tiktok_scraper_core import run_tiktok_scraper
from fb_scraper_core import run_facebook_scraper


st.set_page_config(page_title="Social Comment Scraper", page_icon="💬", layout="wide")

# ========== AUTHENTICATION ==========
def load_config():
    """Load config từ file YAML"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.load(f, Loader=SafeLoader)
    except FileNotFoundError:
        return None


def save_config(config):
    """Lưu config vào file YAML"""
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def has_users(config):
    """Kiểm tra đã có user nào trong config chưa"""
    if not config:
        return False
    creds = config.get('credentials', {}) or {}
    usernames = creds.get('usernames', {}) or {}
    if not usernames:
        return False
    # Lọc bỏ các comment/placeholder
    real_users = {k: v for k, v in usernames.items() if isinstance(v, dict) and 'password' in v}
    return len(real_users) > 0


def setup_first_admin():
    """Form tạo admin đầu tiên"""
    st.title("🔐 Thiết lập tài khoản Admin")
    st.info("Chưa có tài khoản nào. Vui lòng tạo tài khoản Admin đầu tiên.")
    
    with st.form("setup_admin"):
        username = st.text_input("Username", placeholder="admin")
        name = st.text_input("Tên hiển thị", placeholder="Administrator")
        password = st.text_input("Mật khẩu", type="password")
        password_confirm = st.text_input("Xác nhận mật khẩu", type="password")
        
        submitted = st.form_submit_button("🚀 Tạo tài khoản", use_container_width=True)
        
        if submitted:
            if not username or not password:
                st.error("❌ Vui lòng nhập đầy đủ username và mật khẩu!")
            elif password != password_confirm:
                st.error("❌ Mật khẩu xác nhận không khớp!")
            elif len(password) < 4:
                st.error("❌ Mật khẩu phải có ít nhất 4 ký tự!")
            else:
                # Hash password và lưu (hỗ trợ cả phiên bản cũ và mới của streamlit-authenticator)
                try:
                    # Phiên bản mới (>=0.3.0)
                    hashed_password = stauth.Hasher.hash(password)
                except (AttributeError, TypeError):
                    # Phiên bản cũ
                    hashed_password = stauth.Hasher([password]).generate()[0]
                
                config = {
                    'credentials': {
                        'usernames': {
                            username: {
                                'name': name or username,
                                'password': hashed_password
                            }
                        }
                    },
                    'cookie': {
                        'expiry_days': 30,
                        'key': f'social_scraper_{username}_{hash(password) % 10000}',
                        'name': 'social_scraper_auth'
                    }
                }
                
                save_config(config)
                st.success(f"✅ Đã tạo tài khoản **{username}** thành công!")
                st.info("🔄 Đang tải lại trang...")
                st.rerun()
    
    st.stop()


# Load config
config = load_config()

# Kiểm tra nếu chưa có user -> hiển thị form tạo admin
if not has_users(config):
    setup_first_admin()

# Tạo authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

# Hiển thị form đăng nhập
authenticator.login(location='main')

if st.session_state["authentication_status"] is False:
    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.warning("👋 Vui lòng đăng nhập để sử dụng ứng dụng.")
    st.info("💡 Liên hệ admin để được cấp tài khoản.")
    st.stop()

# ========== ĐÃ ĐĂNG NHẬP THÀNH CÔNG ==========

# Custom CSS: giới hạn chiều rộng 80%, căn giữa, và ẩn autorefresh iframe
st.markdown("""
<style>
    .block-container {
        max-width: 80% !important;
        margin: 0 auto;
    }
    /* Ẩn iframe của st_autorefresh */
    .st-key-scraper_refresh {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Header với nút Logout
col_title, col_user = st.columns([4, 1])
with col_title:
    st.title("💬 Social Comment Scraper")
with col_user:
    st.write("")  # Spacer
    st.write(f"👤 **{st.session_state['name']}**")
    authenticator.logout("🚪 Đăng xuất", location='main')


# ========== VALIDATION FUNCTIONS ==========
def is_link_valid(link: str, platform: str) -> bool:
    """Kiểm tra link có đúng nền tảng không"""
    l = (link or "").lower().strip()
    p = (platform or "").lower().strip()
    is_tiktok = "tiktok" in p
    is_facebook = "facebook" in p
    if is_tiktok:
        return "tiktok.com" in l and "facebook.com" not in l and "fb.watch" not in l and "fb.com" not in l
    if is_facebook:
        return ("facebook.com" in l or "fb.watch" in l or "fb.com" in l) and "tiktok.com" not in l
    return False


def is_cookie_valid(cookie_content: bytes, platform: str) -> bool:
    """Kiểm tra cookie có đúng nền tảng không"""
    if not cookie_content:
        return False
    try:
        data = json.loads(cookie_content.decode("utf-8"))
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


# ========== SHARED STATE (persist qua các rerun) ==========
@dataclass
class ScraperState:
    stop_event: threading.Event = field(default_factory=threading.Event)
    data: List = field(default_factory=list)
    log_lines: List[str] = field(default_factory=list)
    status: str = "idle"  # idle, running, stopped, done
    thread: Optional[threading.Thread] = None
    platform: str = "TikTok"
    comment_count: int = 0  # Đếm số bình luận đã cào
    data_saved: bool = False  # Đánh dấu đã lưu vào history chưa
    last_url: str = ""  # URL của lần cào hiện tại


@st.cache_resource
def get_scraper_state():
    return ScraperState()


@st.cache_resource
def get_scraper_history():
    """Lưu trữ 5 lần cào gần nhất"""
    return []


state = get_scraper_state()
history = get_scraper_history()


def save_to_history(data: List, platform: str, url: str):
    """Lưu kết quả vào lịch sử (giữ tối đa 5 lần gần nhất)"""
    if not data:
        return
    
    entry = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "platform": platform,
        "url": url[:50] + "..." if len(url) > 50 else url,
        "count": len(data),
        "data": data.copy()
    }
    
    # Thêm vào đầu danh sách
    history.insert(0, entry)
    
    # Giữ tối đa 5 entries
    while len(history) > 5:
        history.pop()


def get_comment_count_from_logs():
    """Parse số lượng bình luận từ logs (pattern: Tổng: X)"""
    for line in reversed(state.log_lines):
        match = re.search(r"Tổng:\s*(\d+)", line)
        if match:
            return int(match.group(1))
    return 0


def get_current_step():
    """Xác định bước hiện tại từ logs"""
    if not state.log_lines:
        return "Đang chuẩn bị..."
    
    # Duyệt từ cuối lên để lấy bước mới nhất
    for line in reversed(state.log_lines):
        line_lower = line.lower()
        
        # Bước 1: Khởi tạo trình duyệt
        if "đang khởi tạo trình duyệt" in line_lower:
            return "🚀 Đang khởi tạo trình duyệt..."
        if "đã khởi tạo trình duyệt" in line_lower:
            return "✅ Đã khởi tạo trình duyệt"
            
        # Bước 2: Nạp cookie
        if "đang nạp cookie" in line_lower:
            return "🍪 Đang nạp cookie..."
        if "đã nạp" in line_lower and "cookie" in line_lower:
            return "✅ Đã nạp cookie"
        if "chạy không cookie" in line_lower:
            return "⚠️ Chạy không có cookie"
            
        # Bước 3: Truy cập bài viết/video
        if "đang vào" in line_lower or "đang truy cập" in line_lower:
            return "🌍 Đang truy cập link..."
            
        # Bước 4: Chuyển bộ lọc (Facebook)
        if "đang chuyển bộ lọc" in line_lower:
            return "🔄 Đang chuyển bộ lọc bình luận..."
        if "đã chuyển bộ lọc" in line_lower:
            return "✅ Đã chuyển bộ lọc"
            
        # Bước 5: Đang quét comment
        if "bắt đầu quét" in line_lower:
            return "⬇️ Đang quét bình luận..."
        if "tổng:" in line_lower or "lấy thêm" in line_lower:
            return "⬇️ Đang quét bình luận..."
            
        # Đang cuộn
        if "đang thử cuộn" in line_lower:
            return "⏳ Đang thử tải thêm..."
            
        # Hết dữ liệu
        if "đã hết dữ liệu" in line_lower or "đã hết comment" in line_lower:
            return "🏁 Đã quét xong!"
    
    return "⏳ Đang xử lý..."


# ========== SCRAPER FUNCTION (chạy trong thread) ==========
def run_scraper_thread(url, cookie_path, platform_name, headless_mode):
    def log(msg):
        state.log_lines.append(str(msg))

    try:
        if platform_name == "Facebook":
            data = run_facebook_scraper(
                url,
                cookie_path,
                log,
                state.stop_event,
                headless=headless_mode,
            )
        else:
            data = run_tiktok_scraper(
                url,
                cookie_path,
                log,
                state.stop_event,
                headless=headless_mode,
            )

        state.data = data if data else []

        if state.stop_event.is_set():
            state.status = "stopped"
        else:
            state.status = "done"

    except Exception as e:
        state.log_lines.append(f"❌ Lỗi: {e}")
        state.status = "done"


# ========== AUTO REFRESH KHI ĐANG CHẠY ==========
if state.status == "running":
    st_autorefresh(interval=1500, limit=None, key="scraper_refresh")


# ========== LAYOUT 2 CỘT ==========
col_left, col_right = st.columns([6.5, 3.5], gap="large")

# ========== CỘT TRÁI: FORM NHẬP LIỆU ==========
with col_left:
    st.markdown("Chọn nền tảng, nhập link, và upload cookie JSON để bắt đầu.")
    
    is_running = state.status == "running"

    platform = st.selectbox(
        "Nền tảng",
        ["TikTok", "Facebook"],
        disabled=is_running,
        key="platform_select"
    )

    link_label = "Link video" if platform == "TikTok" else "Link bài viết"
    link_placeholder = "https://www.tiktok.com/@user/video/..." if platform == "TikTok" else "https://www.facebook.com/...."
    target_url = st.text_input(link_label, placeholder=link_placeholder, disabled=is_running)

    cookie_file = st.file_uploader("Cookie JSON (bắt buộc)", type=["json"], disabled=is_running)
    headless = st.toggle("Chạy headless (dành cho Cloud)", value=True, disabled=is_running)

    # ========== VALIDATION REALTIME ==========
    validation_errors = []

    if target_url.strip() and not is_link_valid(target_url, platform):
        validation_errors.append(f"❌ Link không đúng nền tảng **{platform}**. Vui lòng kiểm tra lại.")

    if cookie_file is not None and not is_cookie_valid(cookie_file.getvalue(), platform):
        validation_errors.append(f"❌ File cookie không đúng nền tảng **{platform}**. Vui lòng upload cookie của {platform}.")

    for err in validation_errors:
        st.error(err)

    # ========== BUTTONS ==========
    if state.status == "running":
        if st.button("🛑 Dừng lại", type="secondary", use_container_width=True):
            state.stop_event.set()
            st.rerun()
    else:
        if st.button("▶️ Bắt đầu", type="primary", use_container_width=True):
            # Validate bắt buộc
            if not target_url.strip():
                st.warning("⚠️ Vui lòng nhập link.")
            elif cookie_file is None:
                st.warning("⚠️ Vui lòng upload file cookie JSON.")
            elif not is_link_valid(target_url, platform):
                st.error(f"❌ Link không đúng nền tảng **{platform}**.")
            elif not is_cookie_valid(cookie_file.getvalue(), platform):
                st.error(f"❌ File cookie không đúng nền tảng **{platform}**.")
            else:
                # Reset state
                state.stop_event.clear()
                state.data = []
                state.log_lines = []
                state.status = "running"
                state.platform = platform
                state.comment_count = 0
                state.data_saved = False  # Reset flag để cho phép lưu history
                state.last_url = target_url.strip()  # Lưu URL hiện tại

                # Chuẩn bị cookie
                cookie_path = None
                if cookie_file is not None:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
                    temp_file.write(cookie_file.getbuffer())
                    temp_file.flush()
                    temp_file.close()
                    cookie_path = temp_file.name

                # Chạy scraper trong thread riêng
                thread = threading.Thread(
                    target=run_scraper_thread,
                    args=(target_url.strip(), cookie_path, platform, headless),
                    daemon=True
                )
                thread.start()
                state.thread = thread

                st.rerun()

    # ========== HIỂN THỊ TRẠNG THÁI ==========
    if state.status == "running":
        current_count = get_comment_count_from_logs()
        current_step = get_current_step()
        
        st.info(f"""
**{current_step}**

📊 Đã cào được: **{current_count}** bình luận
        """)
        st.caption("🔄 Tự động cập nhật mỗi 1.5s | Bấm **🛑 Dừng lại** để dừng và lưu dữ liệu")

        # Kiểm tra thread còn chạy không
        if state.thread and not state.thread.is_alive():
            st.rerun()

    elif state.status == "stopped":
        platform_name = state.platform.lower()
        if state.data:
            # Lưu vào history và reset về idle
            if not getattr(state, 'data_saved', False):
                save_to_history(state.data, state.platform, getattr(state, 'last_url', ''))
                state.data_saved = True
                
                # Hiển thị thông báo 1 lần rồi reset
                df = pd.DataFrame(state.data)
                st.warning(f"🛑 Đã dừng theo yêu cầu. Lấy được **{len(df)}** bình luận. Đã lưu vào lịch sử.")
                st.dataframe(df, use_container_width=True)
                
                # Export Excel
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                buffer.seek(0)
                st.download_button(
                    "📥 Tải Excel",
                    data=buffer,
                    file_name=f"{platform_name}_comments.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                # Đã lưu rồi, reset về idle
                state.status = "idle"
                state.data = []
                st.rerun()
        else:
            st.warning("🛑 Đã dừng theo yêu cầu. Chưa có dữ liệu.")
            state.status = "idle"

    elif state.status == "done":
        platform_name = state.platform.lower()
        if state.data:
            # Lưu vào history và reset về idle
            if not getattr(state, 'data_saved', False):
                save_to_history(state.data, state.platform, getattr(state, 'last_url', ''))
                state.data_saved = True
                
                # Hiển thị thông báo 1 lần rồi reset
                df = pd.DataFrame(state.data)
                st.success(f"✅ Hoàn thành! Đã lấy **{len(df)}** bình luận. Đã lưu vào lịch sử.")
                st.dataframe(df, use_container_width=True)
                
                # Export Excel
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                buffer.seek(0)
                st.download_button(
                    "📥 Tải Excel",
                    data=buffer,
                    file_name=f"{platform_name}_comments.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            else:
                # Đã lưu rồi, reset về idle
                state.status = "idle"
                state.data = []
                st.rerun()
        else:
            st.error("""
⚠️ **Không lấy được dữ liệu.**

Có thể do cookie đã hết hạn hoặc không hợp lệ. Hãy thử:
1. Đăng xuất khỏi tài khoản trên trình duyệt
2. Đăng nhập lại
3. Xuất cookie mới và thử lại

**Đối với TikTok:**
- Sau khi đăng nhập nếu không hiện capcha thì hãy giữ tab ở đó khoảng **5 - 10 phút** rồi quay lại giải captcha (nếu có)
- Đợi giải captcha xong hãy lấy cookie
- Cookie chỉ có hiệu lực sau khi đã vượt qua captcha
            """)
            state.status = "idle"

# ========== CỘT PHẢI: LỊCH SỬ 5 LẦN CÀO GẦN NHẤT ==========
with col_right:
    st.subheader("📂 Lịch sử 5 lần cào gần nhất")
    
    if history:
        for i, entry in enumerate(history):
            with st.expander(f"**{entry['platform']}** - {entry['count']} bình luận - {entry['timestamp']}"):
                st.caption(f"🔗 {entry['url']}")
                
                # Hiển thị preview data
                df_preview = pd.DataFrame(entry['data'])
                st.dataframe(df_preview.head(5), use_container_width=True)
                
                if len(entry['data']) > 5:
                    st.caption(f"... và {len(entry['data']) - 5} bình luận khác")
                
                # Nút tải về
                buffer = io.BytesIO()
                pd.DataFrame(entry['data']).to_excel(buffer, index=False, engine='openpyxl')
                buffer.seek(0)
                st.download_button(
                    f"📥 Tải Excel ({entry['count']} bình luận)",
                    data=buffer,
                    file_name=f"{entry['platform'].lower()}_comments_{entry['timestamp'].replace('/', '-').replace(':', '-').replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_history_{i}"
                )
    else:
        st.caption("Chưa có lịch sử cào nào.")
