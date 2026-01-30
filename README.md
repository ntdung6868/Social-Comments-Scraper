# Social Comment Scraper

Công cụ thu thập bình luận từ **TikTok** và **Facebook** bằng giao diện trực quan. Tự mở Chrome, cào comment và lưu file Excel vào Desktop.

## Tải phần mềm

Vào trang **Releases** của repo và tải bản mới nhất:

- **Windows:** `Social-Comment-Scraper.exe`
- **macOS (Apple Silicon):** `Social-Comment-Scraper-arm64.dmg`
- **macOS (Intel):** `Social-Comment-Scraper-x86_64.dmg`

Giao diện và cách dùng giống nhau trên mọi nền tảng.

---

## Cài đặt trên macOS (sau khi tải .dmg)

1. **Mở file .dmg**  
   Double-click file `Social-Comment-Scraper-*.dmg` → cửa sổ Finder hiện ra với biểu tượng **Social Comment Scraper**.

2. **Kéo vào Applications**  
   Kéo biểu tượng app vào thư mục **Applications**.  
   Sau khi copy xong, có thể **Eject** ổ đĩa ảo .dmg và xóa file .dmg nếu muốn.

3. **Mở app**  
   Vào **Applications** → double-click **Social Comment Scraper** để chạy.

### Nếu không mở được / báo "Nhà phát triển không xác định"

**Cách 1 – Cho phép mở (nên dùng):**
- **Chuột phải** (hoặc Control + click) vào app → chọn **Open** → bấm **Open** lần nữa.

**Cách 2 – Dùng Cài đặt hệ thống:**
- Mở **System Settings** → **Privacy & Security**.  
- Kéo xuống **Security** → bấm **Open Anyway** nếu có cảnh báo.

**Cách 3 – Tạm tắt Gatekeeper (chỉ khi hai cách trên vẫn không được):**
- Terminal: `sudo spctl --master-disable`  
- Mở app → xong thì bật lại: `sudo spctl --master-enable`

⚠️ Tắt Gatekeeper làm giảm bảo mật của Mac. Chỉ dùng tạm.

**Cách 4 – Ký lại ứng dụng (codesign):**
- `sudo codesign --force --deep --sign - ` *(kéo file .app vào sau dấu cách)*
- `sudo xattr -r -c ` *(kéo file .app vào sau dấu cách)*

## Yêu cầu

- **Hệ điều hành:** Windows hoặc macOS (M1/Intel)
- **Google Chrome** đã cài sẵn

Không cần cài Python hay thư viện khi dùng bản Releases.

## Cách dùng nhanh

1. Mở **Social Comment Scraper**.
2. Chọn **Nền tảng**: TikTok hoặc Facebook.
3. Dán **link video/post**.
4. (Tùy chọn) **Kéo-thả** hoặc **Browse** file cookie `.json`.
5. Bấm **BẮT ĐẦU** để chạy.
6. Có thể bấm **DỪNG LẠI** để dừng sớm.

### Lưu file

File Excel được lưu theo nền tảng:

- TikTok: `~/Desktop/tiktok-scratched-data/tiktok_comments_YYYYMMDD_HHMMSS.xlsx`
- Facebook: `~/Desktop/facebook-scratched-data/facebook_comments_YYYYMMDD_HHMMSS.xlsx`

## Cookie (tùy chọn)

Cookie giúp giảm captcha và hạn chế bị chặn.

**Cách lấy cookie:**
1. Cài extension **Cookie Editor** hoặc **EditThisCookie** trên Chrome.
2. Đăng nhập TikTok/Facebook trên Chrome.
3. Export cookie ra file **JSON**.
4. Trong app, **Browse** hoặc **kéo-thả** file `.json`.

**Định dạng cookie**:
- Object có key `"cookies"` chứa mảng cookie, hoặc  
- Mảng cookie trực tiếp.

## Windows SmartScreen cảnh báo

Nếu gặp **"Windows protected your PC"**:
1. Bấm **More info**
2. Bấm **Run anyway**

Đây là cảnh báo thường gặp với app chưa ký số.

## Gặp lỗi

- **Không thấy bình luận:** Giao diện thay đổi hoặc bài viết không có comment.
- **Captcha:** Giải captcha trên Chrome rồi chờ tool chạy tiếp.
- **Không cào được:** Kiểm tra link, cookie và mạng.

## Streamlit Cloud

App web dùng file `streamlit_app.py`. Repo đã có sẵn `requirements.txt` và `packages.txt`.

Các bước triển khai:

1. Đẩy code lên GitHub.
2. Vào https://streamlit.io/cloud → **New app**.
3. Chọn repo + branch, đặt **Main file path** = `streamlit_app.py`.
4. Deploy và chờ build xong.

Lưu ý: Cloud chạy headless nên nếu gặp captcha sẽ không thể giải tay.

## Lưu ý

- Chỉ dùng cho mục đích học tập/nghiên cứu.
- Scraping có thể vi phạm điều khoản của nền tảng; sử dụng có trách nhiệm.

## License

MIT – xem [LICENSE](LICENSE).
