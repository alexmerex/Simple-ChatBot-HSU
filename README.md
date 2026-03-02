# ChatBot Đại Học Hoa Sen

ChatBot hỏi đáp thông tin Đại học Hoa Sen, xây dựng bằng Python với kiến trúc modular theo `src/`, hỗ trợ cả GUI và CLI, có giải thích kết quả truy hồi, tự động nạp lại dữ liệu tri thức khi thay đổi, và lưu lịch sử hội thoại.

## Mục tiêu dự án

- Trả lời nhanh các câu hỏi dựa trên tập tri thức cục bộ (`knowledge.txt`)
- Dễ mở rộng và bảo trì nhờ tách module rõ ràng
- Cho phép theo dõi chất lượng câu trả lời qua phần giải thích top-k

## Tính năng chính

- Chuẩn hóa văn bản tiếng Việt (bao gồm xử lý bỏ dấu)
- Truy hồi bằng `TF-IDF + KDTree`
- Reranking kết quả bằng điểm lai:
  - semantic similarity
  - lexical overlap
- Ngưỡng tin cậy (`similarity_threshold`) + fallback khi ngoài miền tri thức
- Hot-reload `knowledge.txt` không cần khởi động lại app
- Chạy được ở 2 chế độ:
  - GUI (`tkinter`)
  - CLI (terminal)
- Explanations:
  - GUI: panel riêng bên phải
  - CLI: in top-k candidate + score
- Lịch sử hội thoại:
  - export `.json` / `.txt`
  - auto-save khi thoát ứng dụng
  - tự động rotate/prune file export cũ
- Session ID theo timestamp hiển thị trong GUI/CLI

## Cấu trúc dự án

```text
.
├── main.py
├── knowledge.txt
├── requirements.txt
├── pyproject.toml
├── .env.example
├── src/
│   └── chatbot_hsu/
│       ├── __init__.py
│       ├── config.py
│       ├── engine.py
│       ├── gui.py
│       ├── history.py
│       ├── logging_utils.py
│       └── text_utils.py
└── tests/
    ├── test_engine.py
    └── test_text_utils.py
```

## Cài đặt

Yêu cầu: Python 3.10+

```bash
pip install -r requirements.txt
```

## Cấu hình `.env`

Tạo file `.env` từ mẫu:

```bash
copy .env.example .env
```

### Các biến cấu hình quan trọng

#### Chế độ chạy
- `CHATBOT_MODE=gui|cli`
- `CHATBOT_APP_TITLE=ChatBot Đại Học Hoa Sen`

#### Dữ liệu tri thức
- `CHATBOT_KNOWLEDGE_FILE=knowledge.txt`
- `CHATBOT_HOT_RELOAD=true`

#### Truy hồi và giải thích
- `CHATBOT_RETRIEVAL_K=5`
- `CHATBOT_EXPLANATION_TOP_K=3`
- `CHATBOT_SIMILARITY_THRESHOLD=0.18`
- `CHATBOT_FALLBACK_MESSAGE=...`
- `CHATBOT_SHOW_EXPLANATIONS=true`

#### Lịch sử hội thoại
- `CHATBOT_HISTORY_EXPORT_DIR=exports`
- `CHATBOT_HISTORY_KEEP_LAST_EXPORTS=20`

#### Logging / debug
- `CHATBOT_DEBUG=false`
- `CHATBOT_LOG_LEVEL=INFO`

## Chạy ứng dụng

### GUI mode

```bash
python main.py --mode gui
```

### CLI mode

```bash
python main.py --mode cli
```

Hoặc bỏ `--mode` để dùng mode từ `.env`.

## CLI commands

- `/help`: hiển thị hướng dẫn nhanh
- `/clear`: xóa lịch sử hội thoại của phiên hiện tại
- `/reload`: reload chỉ mục tri thức ngay lập tức
- `/config`: in cấu hình runtime hiện tại
- `/topk [n]`: xem/chỉnh số lượng kết quả giải thích hiển thị
- `/export json`: export lịch sử sang JSON
- `/export txt`: export lịch sử sang TXT
- `exit` / `quit`: thoát (kèm auto-save lịch sử)

## GUI controls

- `Send`: gửi câu hỏi
- `Clear Chat`: xóa chat + explanations + history phiên hiện tại
- `Reload Knowledge`: nạp lại dữ liệu tri thức thủ công
- `Export JSON`: xuất lịch sử thủ công dạng `.json`
- `Export TXT`: xuất lịch sử thủ công dạng `.txt`

## Cơ chế lưu lịch sử

- Mỗi phiên có `session_id` theo timestamp
- Auto-save khi thoát app (GUI/CLI) mà không cần thao tác tay
- File lưu trong `CHATBOT_HISTORY_EXPORT_DIR`
- Tự động giữ lại N file mới nhất theo `CHATBOT_HISTORY_KEEP_LAST_EXPORTS`

## Chạy test

```bash
pytest
```

## Gợi ý cải thiện tiếp

- Bổ sung bộ dữ liệu tri thức theo chủ đề (học phí, tuyển sinh, lịch học)
- Thêm command `/stats` cho CLI để xem tỉ lệ fallback
- Thêm chế độ export CSV cho báo cáo nhanh
