# ChatBot Đại Học Hoa Sen

## Giới Thiệu

ChatBot Đại Học Hoa Sen là một ứng dụng sử dụng Trí tuệ nhân tạo để trả lời các câu hỏi liên quan đến Đại học Hoa Sen. Ứng dụng được xây dựng bằng Python và sử dụng thư viện `tkinter` để tạo giao diện người dùng đồ họa.

## Dữ Liệu

Dữ liệu đầu vào của ChatBot được lưu trữ trong file `knowledge.txt`. Đây là một tập hợp chứa hơn 300 câu văn bản về Đại học Hoa Sen. Các câu hỏi đã được chuẩn hóa, tách từ, loại bỏ từ dừng và vector hóa bằng phương pháp TF-IDF.

Nếu bạn muốn cập nhật hoặc mở rộng dữ liệu, chỉ cần thêm hoặc sửa đổi nội dung trong file `knowledge.txt`.

## Cách Sử Dụng

1. Chạy file `chatbot.py` để khởi động ứng dụng.
2. Giao diện người dùng sẽ hiển thị, cho phép bạn nhập câu hỏi vào ô nhập liệu hoặc nhấn Enter để gửi câu hỏi.
3. ChatBot sẽ xử lý câu hỏi, tìm kiếm trong dữ liệu và hiển thị câu trả lời tương ứng.

## Cài Đặt

Để chạy ChatBot, bạn cần cài đặt các thư viện sau đây:

```bash
pip install nltk scikit-learn
```

Sau đó, tải các nguồn từ tiếng Anh từ thư viện NLTK bằng lệnh sau:

```bash
python -m nltk.downloader punkt
python -m nltk.downloader stopwords
```

## Cập Nhật Dữ Liệu

Để cập nhật dữ liệu hoặc thêm câu hỏi mới, chỉ cần mở file `knowledge.txt` và thực hiện các thay đổi mong muốn.

---

Chú ý: Hãy đảm bảo rằng bạn đang chạy mã nguồn trong môi trường hỗ trợ Python và có kết nối internet để tải xuống dữ liệu cần thiết từ thư viện NLTK khi chạy lần đầu tiên.