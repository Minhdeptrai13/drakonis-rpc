# 🎮 Discord RPC Master (Python Flask & discord.py-self)

Ứng dụng web cục bộ hoàn chỉnh cho phép tùy biến trạng thái **Discord Rich Presence (RPC)** cá nhân với giao diện **Dark Mode** hiện đại phong cách lai giữa **Discord** và bảng điều khiển tối giản của **Vercel**.

---

## 🌟 Tính Năng Nổi Bật

- ⚡ **Khởi chạy tức thì**: Chỉ với **1 câu lệnh duy nhất** `python main.py`, hệ thống tự khởi động server và tự động mở trình duyệt web.
- 🎨 **Bố cục màn hình chia đôi (Split Layout)**:
  - **Cột trái**: Bảng điều khiển cấu hình toàn diện (Token, Activity Type, Details, State, Buttons, Timestamps, Upload ảnh).
  - **Cột phải**: Khung xem trước mô phỏng **1:1 Discord Profile Modal Live Preview** cập nhật theo thời gian thực khi gõ phím.
- 🖼️ **Tải ảnh trực tiếp từ máy (PNG, JPG, GIF, WEBP)**:
  - Tích hợp nút tải file từ máy tính lên server cục bộ (`static/uploads/`) với mã băm UUID chống trùng lặp.
  - Tự động liên kết đường dẫn vào khung Live Preview và trạng thái RPC.
- 🔘 **2 Nút bấm tương tác (Interactive Buttons)**:
  - Hỗ trợ cài đặt nhãn (Label) và đường dẫn URL chuyển hướng.
  - Tích hợp ghi chú rõ ràng về cơ chế hiển thị nút bấm trên Discord.
- ⏱️ **Bộ đếm thời gian thực (Elapsed Timestamp)**:
  - Công tắc bật/tắt hiển thị thời gian bắt đầu trôi qua.
- 🚦 **Đèn LED báo trạng thái trực quan**:
  - 🔴 **Đỏ**: Đã dừng (Stopped).
  - 🟡 **Vàng nhấp nháy**: Đang kết nối tới Gateway Discord (Connecting).
  - 🟢 **Xanh lá**: Đang phát trạng thái (Running/Active).
- 💾 **Hệ thống Presets & Status Rotator**:
  - Đi kèm sẵn các mẫu: *VS Code Coding*, *Valorant Radiant*, *Twitch Streamer*, *Lofi Chill Beats*.
  - Lưu và xóa các mẫu cấu hình cá nhân không giới hạn vào SQLite.
  - Tự động xoay vòng trạng thái sau một chu kỳ thời gian định sẵn.
- 🔒 **Bảo mật & CSDL SQLite cục bộ**:
  - Đăng ký / đăng nhập lưu tài khoản SQLite với mật khẩu băm chuẩn `werkzeug.security`.
- 🛡️ **Kiến trúc luồng nền không nghẽn (Non-blocking Threading & Asyncio)**:
  - Chạy `discord.Client` trong luồng riêng với `asyncio.new_event_loop()`, không làm treo Flask.
  - Bắt sạch lỗi `LoginFailure`, timeout mạng mà không làm crash ứng dụng.

---

## 📁 Cấu Trúc Thư Mục Chuẩn

```text
DiscordRPG/
├── main.py              # Logic Flask server, SQLite DB, worker discord.py-self & auto browser
├── requirements.txt     # Danh sách thư viện phụ thuộc
├── database.db          # Cơ sở dữ liệu SQLite cục bộ (tự động tạo)
├── README.md            # Tài liệu hướng dẫn sử dụng chi tiết
├── templates/
│   ├── login.html       # Giao diện đăng nhập / đăng ký Dark Mode
│   └── index.html       # Dashboard điều khiển & Discord Live Preview 1:1
└── static/
    ├── css/
    │   └── style.css    # Bộ stylesheet Vercel Dark & Discord theme
    ├── js/
    │   └── app.js       # Logic cập nhật realtime, AJAX upload, preset & RPC sync
    └── uploads/         # Thư mục lưu trữ hình ảnh tải lên từ máy tính
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### Bước 1: Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy ứng dụng

```bash
python main.py
```

Ứng dụng sẽ tự động mở trình duyệt web tại địa chỉ:  
👉 **`http://127.0.0.1:5000`**

### Bước 3: Đăng ký & Sử dụng

1. Trên màn hình trình duyệt, chuyển sang tab **Đăng Ký Mới** để tạo tài khoản cá nhân cục bộ.
2. Đăng nhập vào hệ thống.
3. Nhập **Discord User Token** của bạn.
4. Tùy chỉnh nội dung hoạt động, chọn ảnh từ máy hoặc dán URL, thiết lập 2 nút bấm.
5. Nhấn **Khởi Chạy RPC (Start)** để bắt đầu hiển thị trạng thái lên tài khoản Discord!

---

## 💡 Mẹo Lấy Discord User Token An Toàn

1. Mở Discord trên trình duyệt web (hoặc ứng dụng Discord Desktop) và nhấn phím `F12` (hoặc `Ctrl + Shift + I`) để mở Developer Tools.
2. Chuyển sang tab **Console**.
3. Dán đoạn mã sau vào Console và nhấn `Enter`:

   ```javascript
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```

4. Copy chuỗi token hiển thị và dán vào ô nhập liệu trên ứng dụng web Discord RPC Master.

> ⚠️ **Lưu ý bảo mật:** Tuyệt đối không chia sẻ Discord User Token cho người khác. Ứng dụng này chỉ chạy trên máy tính cá nhân của bạn (localhost) và lưu trữ cục bộ an toàn.
