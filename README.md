# Bộ giải Quy hoạch Tuyến tính

Giải các bài toán quy hoạch tuyến tính có từ 1–8 biến quyết định và tối đa 12 ràng buộc.
Chương trình giải từng bước, liệt kê các điểm góc, báo cáo giá bóng, phát hiện các trường hợp
đặc biệt (không khả thi, không bị chặn, nhiều nghiệm tối ưu, suy biến) và vẽ kết quả.

Cùng một bộ máy giải được sử dụng theo hai cách:

| Giao diện | Tệp | Cách chạy |
|---|---|---|
| Ứng dụng web (Streamlit) | `streamlit_app.py` | `streamlit run streamlit_app.py` |
| Chương trình Terminal | `lp_app.py` | `python lp_app.py` |

## Cấu trúc thư mục

```text
├── streamlit_app.py        # giao diện web, tệp khởi động cho Streamlit Cloud
├── lp_app.py               # giao diện Terminal
├── lp_engine.py            # phân tích biểu thức, giải, điểm góc, giá bóng
├── lp_input_guide.py       # ví dụ, hướng dẫn nhập/ký hiệu, trường hợp đặc biệt
├── lp_plotting.py          # miền khả thi / miền 3D / biểu đồ nghiệm
├── lp_utils.py             # các hàm hỗ trợ dùng chung
├── requirements.txt        # các gói cần cài trên Streamlit Cloud
└── README.md
```

Tất cả các tệp `lp_*.py` phải nằm cùng thư mục với `streamlit_app.py`.

## Chạy trên máy tính

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Ứng dụng mở tại `http://localhost:8501`.

## Đưa lên GitHub

1. Tạo một repository mới trên GitHub (có thể public hoặc private).
2. Trong thư mục dự án, chạy:

```bash
git init
git add .
git commit -m "Bo giai quy hoach tuyen tinh bang Streamlit"
git branch -M main
git remote add origin https://github.com/<ten-cua-ban>/<repository>.git
git push -u origin main
```

Hãy bảo đảm thư mục ẩn `.streamlit` cũng được đưa lên GitHub (`git add .` sẽ bao gồm thư mục này).

## Triển khai trên Streamlit Community Cloud

1. Mở `https://share.streamlit.io` và đăng nhập bằng tài khoản GitHub.
2. Chọn **Create app** và triển khai từ GitHub repository.
3. Điền:
   - **Repository:** `<ten-cua-ban>/<repository>`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
4. Trong **Advanced settings**, có thể chọn Python 3.10 hoặc mới hơn.
5. Chọn **Deploy**. Streamlit sẽ cài các gói trong `requirements.txt` và tạo đường dẫn công khai để chia sẻ với học viên.

Mỗi lần `git push` lên nhánh `main`, ứng dụng trực tuyến sẽ tự cập nhật.

## Cách dùng ứng dụng web

- **Bài toán ví dụ** – chọn một trong 13 ví dụ có sẵn rồi nhấn **Giải**.
- **Tự xây dựng** – chọn số biến, tên biến, max/min, hàm mục tiêu và nhập mỗi ràng buộc trên một dòng, ví dụ:

```text
2x + y <= 100 # Máy 1
x + 2y <= 80  # Máy 2
```

Điều kiện không âm được thêm tự động. Hàm mục tiêu có thể nhập dạng `40x + 30y` hoặc `40, 30`.

- **Hướng dẫn** – xem hướng dẫn nhập dữ liệu, ký hiệu và các trường hợp đặc biệt.

Kết quả được chia thành bốn tab: **Hình minh họa**, **Từng bước**, **Điểm góc** và **Độ nhạy**
(độ dư, ràng buộc chặt, giá bóng).

## Xử lý lỗi thường gặp

| Vấn đề | Cách khắc phục |
|---|---|
| `ModuleNotFoundError: lp_engine` | Đặt tất cả tệp `lp_*.py` ở thư mục gốc của repository, cạnh `streamlit_app.py`. |
| `ModuleNotFoundError: scipy` | Kiểm tra `requirements.txt` nằm ở thư mục gốc và đúng tên. |
| Chạy được trên máy nhưng không chạy trên Cloud | Mở **Manage app → Logs** trên Streamlit Cloud để xem thông báo lỗi. |
| Mô hình lớn chạy chậm | 8 biến × 12 ràng buộc có thể kiểm tra tới 125.970 tổ hợp điểm góc; kết quả được cache nên cùng một mô hình chỉ giải một lần. |
