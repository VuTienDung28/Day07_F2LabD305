from __future__ import annotations

import math
from src.embeddings import LocalEmbedder

embedder = LocalEmbedder()

def dot(a, b):
    return sum(x * y for x, y in zip(a, b))

def cosine(a, b):
    na = math.sqrt(dot(a, a))
    nb = math.sqrt(dot(b, b))
    return dot(a, b) / (na * nb) if na * nb > 0 else 0.0

pairs = [
    ("Quy định mượn sách thư viện VinUni", "Thủ tục mượn sách cho sinh viên đại học"),
    ("Thời hạn trả sách thư viện là bao lâu?", "Hướng dẫn nộp học phí trực tuyến"),
    ("Giảng viên mượn tối đa 5 tài liệu", "Sinh viên cao học mượn 5 tài liệu"),
    ("Nộp phạt quá hạn trực tuyến", "Thanh toán phí dịch vụ qua cổng ngân hàng"),
    ("Sách Course Reserve đọc tại chỗ 2 giờ", "Thiết bị thư viện mượn 1 ngày làm việc"),
]

print("=== EXACT SECTION 4 SIMILARITY SCORES ===")
for i, (a, b) in enumerate(pairs, 1):
    va = embedder(a)
    vb = embedder(b)
    score = cosine(va, vb)
    print(f"Pair {i}: score = {score:.4f}")
