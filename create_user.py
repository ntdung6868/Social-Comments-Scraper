"""
Script để tạo user mới hoặc hash password.

Cách sử dụng:
    python create_user.py

Script sẽ hỏi username và password, sau đó in ra đoạn YAML 
để bạn copy vào file config.yaml
"""

import streamlit_authenticator as stauth
import yaml


def create_user():
    print("=" * 50)
    print("TẠO USER MỚI CHO SOCIAL COMMENT SCRAPER")
    print("=" * 50)
    
    username = input("\nNhập username: ").strip()
    if not username:
        print("❌ Username không được để trống!")
        return
    
    name = input("Nhập tên hiển thị: ").strip()
    if not name:
        name = username
    
    password = input("Nhập password: ").strip()
    if not password:
        print("❌ Password không được để trống!")
        return
    
    # Hash password (hỗ trợ cả phiên bản cũ và mới)
    try:
        # Phiên bản mới (>=0.3.0)
        hashed_password = stauth.Hasher.hash(password)
    except (AttributeError, TypeError):
        # Phiên bản cũ
        hashed_password = stauth.Hasher([password]).generate()[0]
    
    print("\n" + "=" * 50)
    print("✅ ĐÃ TẠO USER THÀNH CÔNG!")
    print("=" * 50)
    print("\nCopy đoạn sau vào file config.yaml (trong phần credentials > usernames):\n")
    print(f"    {username}:")
    print(f"      name: {name}")
    print(f"      password: {hashed_password}")
    print("\n" + "=" * 50)
    
    # Hỏi có muốn tự động thêm vào config.yaml không
    auto_add = input("\nBạn có muốn tự động thêm vào config.yaml? (y/n): ").strip().lower()
    
    if auto_add == 'y':
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'credentials' not in config:
                config['credentials'] = {'usernames': {}}
            if 'usernames' not in config['credentials']:
                config['credentials']['usernames'] = {}
            
            config['credentials']['usernames'][username] = {
                'name': name,
                'password': hashed_password
            }
            
            with open('config.yaml', 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            print("✅ Đã thêm user vào config.yaml!")
        except Exception as e:
            print(f"❌ Lỗi: {e}")
            print("Vui lòng copy thủ công đoạn YAML ở trên.")


if __name__ == "__main__":
    create_user()
