import tempfile

import pandas as pd
import streamlit as st

from tiktok_scraper_core import run_tiktok_scraper
from fb_scraper_core import run_facebook_scraper


st.set_page_config(page_title="Social Comment Scraper", page_icon="💬", layout="centered")
st.title("Social Comment Scraper")

st.markdown("Chọn nền tảng, nhập link, và (tuỳ chọn) upload cookie JSON.")

platform = st.selectbox("Nền tảng", ["TikTok", "Facebook"])
link_label = "Link video" if platform == "TikTok" else "Link bài viết"
link_placeholder = "https://www.tiktok.com/@user/video/..." if platform == "TikTok" else "https://www.facebook.com/...."
target_url = st.text_input(link_label, placeholder=link_placeholder)

cookie_file = st.file_uploader("Cookie JSON (tuỳ chọn)", type=["json"])
headless = st.toggle("Chạy headless (dành cho Cloud)", value=True)

log_placeholder = st.empty()
log_lines = []


def log(msg):
    log_lines.append(str(msg))
    log_placeholder.text_area("Logs", "\n".join(log_lines), height=240)


run_clicked = st.button("Bắt đầu", type="primary")

if run_clicked:
    if not target_url.strip():
        st.warning("Vui lòng nhập link.")
        st.stop()

    cookie_path = None
    temp_file = None
    if cookie_file is not None:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_file.write(cookie_file.getbuffer())
        temp_file.flush()
        cookie_path = temp_file.name

    with st.spinner("Đang chạy..."):
        if platform == "Facebook":
            data = run_facebook_scraper(
                target_url.strip(),
                cookie_path,
                log,
                None,
                headless=headless,
            )
        else:
            data = run_tiktok_scraper(
                target_url.strip(),
                cookie_path,
                log,
                None,
                headless=headless,
            )

    if temp_file is not None:
        try:
            temp_file.close()
        except Exception:
            pass

    if data:
        df = pd.DataFrame(data)
        st.success(f"Đã lấy {len(df)} bình luận.")
        st.dataframe(df, use_container_width=True)

        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Tải CSV",
            data=csv_bytes,
            file_name=f"{platform.lower()}_comments.csv",
            mime="text/csv",
        )
    else:
        st.warning("Không lấy được dữ liệu.")
