import tkinter as tk
from tkinter import scrolledtext, messagebox
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KDTree
import re

# Đọc dữ liệu từ file
with open("knowledge.txt", "r", encoding="utf-8") as file:
    text_data = file.readlines()

# Chuẩn hóa văn bản và xử lý dữ liệu
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)
    return text

# Xử lý câu hỏi
def process_question(question):
    question = preprocess_text(question)
    return question

# Sử dụng TF-IDF để vector hóa dữ liệu
tfidf_vectorizer = TfidfVectorizer(max_df=0.85, min_df=2, max_features=1000)
vectorized_data = tfidf_vectorizer.fit_transform([process_question(sentence) for sentence in text_data])

# Chuyển đổi ma trận thưa sang mảng mật độ
dense_vectorized_data = vectorized_data.toarray()

# Xây dựng KD-Tree với kích thước lá là 10
kdtree = KDTree(dense_vectorized_data, leaf_size=10)

def get_answer(query):
    # Xử lý câu hỏi
    processed_query = process_question(query)

    # Vector hóa câu truy vấn
    query_vector = tfidf_vectorizer.transform([processed_query]).toarray()

    # Tìm câu trả lời gần nhất trong KD-Tree
    _, idx = kdtree.query(query_vector, k=1)

    return text_data[idx.item()]

def on_send(event=None):
    user_input = user_entry.get()

    if not user_input:
        messagebox.showwarning("Warning", "Please enter a question.")
        return

    # Hiển thị câu trả lời
    answer = get_answer(user_input)

    # Xóa nội dung trong phần hiển thị câu trả lời
    chat_display.insert(tk.END, f"User: {user_input}\nChatBot: {answer}\n\n")

    # Xóa ô nhập liệu sau khi gửi
    user_entry.delete(0, tk.END)

# Tạo cửa sổ
window = tk.Tk()
window.title("ChatBot GUI")

# Thiết lập chiều rộng mong muốn
desired_width = 1000

# Tạo phần hiển thị câu trả lời
chat_display = scrolledtext.ScrolledText(window, width=int(desired_width / 10), height=20, wrap=tk.WORD)
chat_display.grid(row=0, column=0, padx=10, pady=10, columnspan=2, sticky="nsew")  # Thêm sticky="nsew"

# Tạo thanh chat để nhập câu hỏi
user_entry = tk.Entry(window, width=int(desired_width / 10))
user_entry.grid(row=1, column=0, padx=10, pady=10, columnspan=2, sticky="nsew")  # Thêm sticky="nsew"

# Tạo nút Gửi
send_button = tk.Button(window, text="Send", command=on_send)
send_button.grid(row=2, column=0, padx=10, pady=10, columnspan=2, sticky="nsew")  # Thêm sticky="nsew"

# Bắt sự kiện khi nhấn phím Enter
user_entry.bind("<Return>", on_send)

# Thiết lập trọng số cột
window.columnconfigure(0, weight=1)  # Cột 0 co giãn khi cửa sổ thay đổi kích thước
window.columnconfigure(1, weight=1)  # Cột 1 cũng co giãn

# Thiết lập trọng số hàng
window.rowconfigure(0, weight=1)  # Hàng 0 co giãn
window.rowconfigure(1, weight=1)  # Hàng 1 co giãn
window.rowconfigure(2, weight=1)  # Hàng 2 co giãn

# Bắt đầu vòng lặp chạy GUI
window.mainloop()