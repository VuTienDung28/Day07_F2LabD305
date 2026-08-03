# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Chu Nguyễn Tuấn Anh
**Nhóm:** F2
**Ngày:** 03/08/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

Độ tương tự cosine cao nghĩa là hai vector embedding gần cùng hướng, vì vậy hai đoạn văn thường biểu diễn nội dung hoặc ý nghĩa gần nhau. Giá trị gần 1 thể hiện mức tương đồng cao, gần 0 là ít liên quan và gần -1 là đối lập về hướng vector.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên phải đóng học phí đúng hạn.
- Câu B: Người học cần thanh toán học phí trước thời hạn.
- Tại sao tương đồng: Hai câu dùng từ khác nhau nhưng cùng nói về nghĩa vụ thanh toán học phí đúng hạn.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Hôm nay trời mưa rất lớn.
- Câu B: Sinh viên được phép hủy học phần.
- Tại sao khác: Một câu nói về thời tiết, câu còn lại nói về quy định học vụ nên hầu như không có cùng ngữ nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

Cosine tập trung vào hướng của vector, tức đặc trưng ngữ nghĩa, và ít bị ảnh hưởng bởi độ lớn vector. Khoảng cách Euclid phụ thuộc cả hướng lẫn độ lớn nên hai embedding cùng ý nghĩa vẫn có thể bị xem là xa nhau nếu chuẩn vector khác nhau.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

Bước dịch giữa hai chunk là `500 - 50 = 450` ký tự. Số chunk là `ceil((10,000 - 500) / 450) + 1 = ceil(21.111...) + 1 = 23`.

**Đáp án:** 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

Bước dịch giảm còn `500 - 100 = 400`, nên số chunk là `ceil((10,000 - 500) / 400) + 1 = 25`. Overlap lớn hơn giữ thêm ngữ cảnh ở ranh giới chunk và giảm nguy cơ tách mất một ý quan trọng, đổi lại cần lưu trữ và xử lý nhiều dữ liệu trùng lặp hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` để tách tại khoảng trắng hoặc xuống dòng đứng sau dấu kết câu `.`, `!`, `?`, đồng thời giữ dấu câu trong câu trước. Các câu rỗng được loại bỏ, khoảng trắng được chuẩn hóa và `max_sentences_per_chunk` luôn tối thiểu là 1.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

Thuật toán thử lần lượt các separator từ cấp cấu trúc lớn đến nhỏ, ghép các phần khi chunk kết quả chưa vượt `chunk_size`, rồi đệ quy với separator tiếp theo cho phần quá dài. Base case trả thẳng đoạn đã đủ ngắn; nếu hết separator thì cắt cứng theo `chunk_size`, vì vậy cả danh sách separator rỗng vẫn hoạt động.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

Mỗi `Document` được chuẩn hóa thành record gồm ID duy nhất, nội dung, metadata có thêm `doc_id` và embedding. Khi không có ChromaDB, store giữ record trong bộ nhớ và xếp hạng bằng tích vô hướng giữa các embedding đã chuẩn hóa; nếu ChromaDB có sẵn thì dùng collection cosine và đổi distance thành similarity bằng `1 - distance`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

Metadata được lọc trước khi tính similarity để chỉ xếp hạng các ứng viên hợp lệ. `delete_document` xóa toàn bộ record có `metadata["doc_id"]` trùng ID tài liệu và trả về `True` chỉ khi thực sự có record bị xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

Tác tử lấy top-k chunk từ store, nối nội dung thành khối `Context`, rồi đặt câu hỏi sau phần ngữ cảnh. Prompt yêu cầu LLM chỉ dùng thông tin trong context và trả lời không biết nếu context không chứa đáp án nhằm hạn chế câu trả lời không có căn cứ.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.0.2
collected 42 items

tests/test_solution.py ..........................................        [100%]

============================= 42 passed in 0.26s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

> Môi trường hiện tại chạy Python 3.13.1. Lệnh `py -3.11` chưa chạy được vì máy chưa có Python 3.11 tại đường dẫn đã đăng ký; cần xác minh lại trên Python 3.11 trước khi nộp theo chuẩn của Lab.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Các dự đoán được ghi trước khi chạy `LocalEmbedder` với mô hình `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; điểm thực tế được tính bằng `compute_similarity()`.

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên phải đóng học phí đúng hạn. | Người học cần thanh toán học phí trước thời hạn. | cao | 0.8111 | Có |
| 2 | Thư viện cho phép sinh viên mượn sách. | Sinh viên có thể mượn tài liệu tại thư viện. | cao | 0.9170 | Có |
| 3 | Tôi đăng ký môn học trực tuyến. | Ký túc xá quy định giờ đóng cửa. | thấp | 0.1336 | Có |
| 4 | Điều kiện nhận học bổng dựa trên kết quả học tập. | Thành tích học tập là tiêu chí xét học bổng. | cao | 0.8650 | Có |
| 5 | Hôm nay trời mưa rất lớn. | Sinh viên được phép hủy học phần. | thấp | -0.0046 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

Cặp 2 đạt 0.9170, cao hơn cặp 1 dù hai câu dùng các từ không hoàn toàn giống nhau như “sách” và “tài liệu”. Điều này cho thấy embedding đa ngữ biểu diễn quan hệ ngữ nghĩa và ngữ cảnh tổng thể, thay vì chỉ đếm từ khóa trùng nhau.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Nhóm F2 thống nhất dùng `k3_library.zip` và đúng 5 câu trong `benchmark.csv`. Chiến lược cá nhân của tôi là `RecursiveChunker(chunk_size=500)` với thứ tự separator mặc định `"\n\n"`, `"\n"`, `". "`, `" "`, `""`, kết hợp `LocalEmbedder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")`; corpus tạo ra 41 chunks. Tôi chọn cấu hình này vì nó giữ được cấu trúc đoạn và bảng tốt hơn Fixed Size/Sentence, đồng thời chỉ cần 41 chunks so với 87 chunks của Recursive 250 mà vẫn đạt 5/5 evidence trong top-3.

Trước khi lọc chi tiết, chiến lược đạt 4/5 evidence ở top-1 và 5/5 ở top-3; Q3 về biểu phí đứng top-2 do một chunk hướng dẫn sinh viên có nhiều từ khóa gần nghĩa. Tôi dùng `search_with_filter` theo metadata có căn cứ trong câu hỏi: Q1 lọc `audience=student`, Q2 lọc `category=circulation-policy`, Q3 lọc `audience=student` và `category=library-fees`; Q4–Q5 không lọc. Sau lọc, cả 5 câu đều có đầy đủ evidence ở top-1. Bảng thử nghiệm và failure analysis chi tiết nằm trong `report/STRATEGY_ANALYSIS.md`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Sinh viên đại học được mượn bao nhiêu tài liệu, trong bao lâu và được gia hạn mấy lần? | `undergraduate-borrowing::chunk_0`: tối đa 3 tài liệu, thời hạn 2 tuần, gia hạn 1 lần nếu chưa quá hạn và không có người đặt | 0.6621 | Có | Được mượn 3 tài liệu trong 2 tuần và gia hạn 1 lần. |
| 2 | Mỗi người được mượn bao nhiêu sách Course Reserve cùng lúc? | `circulation-policy::chunk_2`: Course Reserve dùng trong 2 giờ, 1 tài liệu/người/lần | 0.6869 | Có | Mỗi người được mượn 1 tài liệu Course Reserve mỗi lần, tối đa 2 giờ. |
| 3 | Phí quá hạn cho tài liệu thường, Course Reserve và thiết bị là bao nhiêu? | `financial-regulations-library-fees::chunk_0`: liệt kê ba mức phí quá hạn hiện hành | 0.5967 | Có | Tài liệu thường: 10.000 VND/ngày/tài liệu; Course Reserve: 10.000 VND/giờ/tài liệu; thiết bị: 10.000 VND/ngày/thiết bị. |
| 4 | Tài liệu được yêu cầu sẽ được giữ trong bao lâu sau khi sẵn sàng nhận? | `circulation-policy::chunk_10`: giữ 2 ngày rồi hủy yêu cầu nếu không được nhận | 0.7566 | Có | Tài liệu được giữ 2 ngày; quá thời hạn mà không nhận thì yêu cầu bị hủy. |
| 5 | Người dùng nên làm gì khi thanh toán thư viện thất bại dù đã nhập đúng thông tin thẻ? | `fines-and-payment::chunk_4`: không gửi lại thanh toán, liên hệ quầy lưu hành | 0.7556 | Có | Không thử thanh toán lại; liên hệ nhân viên tại quầy lưu hành để được hỗ trợ. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

Qua quá trình nhóm chốt corpus và benchmark, tôi học được rằng metadata về đối tượng và loại chính sách có thể quan trọng ngang với điểm cosine. Với các trang FAQ và dịch vụ có thông tin cũ, ưu tiên tài liệu chính thức có phiên bản rồi lọc theo `audience`/`category` giúp tránh lấy một chunk gần nghĩa nhưng không phải nguồn có thẩm quyền.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 10 / 10 |
| **Tổng phần cá nhân** | **60 / 60** |
