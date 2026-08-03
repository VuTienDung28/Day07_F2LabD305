# Báo Cáo So Sánh 5 Câu Benchmark Theo Các Phương Pháp Chunking

**Backend Embedder:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

| # | Câu Hỏi (Query) | Metadata Filter | Evidence File | FixedSize (500,50) | SentenceChunker (3) | RecursiveChunker (350) |
|---|---|---|---|---|---|---|
| 1 | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed? | `audience=student` | `undergraduate-borrowing.md` | 0.6547 | 0.6599 | **0.6599** |
| 2 | How many Course Reserve books may one user borrow at a time? | `-` | `circulation-policy.md` | 0.6288 | 0.6017 | **0.8153** |
| 3 | What is the overdue fine for normal material, Course Reserve material, and equipment? | `audience=student` | `financial-regulations-library-fees.md` | 0.5930 | 0.5751 | **0.5751** |
| 4 | How long is a requested library item held after it is ready for collection? | `-` | `circulation-policy.md` | 0.6181 | 0.6543 | **0.6543** |
| 5 | What should a user do when an online library payment fails after accurate card information was entered? | `-` | `fines-and-payment.md` | 0.7576 | 0.7002 | **0.7556** |


### Nhận Xét Kết Quả:
1. **FixedSizeChunker (500, 50)**: Điểm số khá nhưng dễ gặp tình trạng cắt đứt câu giữa chừng hoặc chứa các đoạn thông tin thừa không liên quan trong cùng 1 chunk.
2. **SentenceChunker (3 câu)**: Các chunks ngắn gọn, tuy nhiên với các tài liệu pháp lý/quy định dài, 3 câu thường chưa bao phủ trọn vẹn ngữ cảnh của điều khoản.
3. **RecursiveChunker (350)**: Đạt điểm tương đồng ngữ nghĩa (similarity score) tối ưu nhất do giữ nguyên cấu trúc tiêu đề (heading) và ranh giới đoạn văn trọn vẹn.
