# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Vũ Tiến Dũng
**Nhóm:** F2-LabD305
**Ngày:** 03-08-2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Độ tương tự cosine cao nghĩa là hai vector embedding có hướng gần giống nhau, cho thấy hai đoạn văn bản có nội dung hoặc ý nghĩa ngữ nghĩa gần nhau. Giá trị càng gần 1 thì mức độ tương đồng càng cao.

**Ví dụ có độ tương tự CAO:**

- Câu A: Sinh viên cần đăng ký học phần trước thời hạn quy định.
- Câu B: Người học phải hoàn tất việc đăng ký môn học đúng hạn.
- Tại sao tương đồng: Hai câu cùng đề cập đến yêu cầu sinh viên đăng ký môn học trước thời hạn, dù sử dụng cách diễn đạt khác nhau.

**Ví dụ có độ tương tự THẤP:**

- Câu A: Thư viện cho phép sinh viên gia hạn thời gian mượn sách.
- Câu B: Thời tiết hôm nay có mưa lớn ở khu vực miền Trung.
- Tại sao khác: Hai câu thuộc hai chủ đề không liên quan, một câu nói về dịch vụ thư viện và câu còn lại nói về thời tiết.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine similarity tập trung vào hướng của vector nên ít bị ảnh hưởng bởi độ lớn của embedding, trong khi khoảng cách Euclid thay đổi theo cả hướng lẫn độ lớn. Với văn bản, hướng vector thường phản ánh nội dung ngữ nghĩa tốt hơn độ dài tuyệt đối của vector.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> _Trình bày phép tính:_ `ceil((10,000 - 50) / (500 - 50)) = ceil(9,950 / 450) = ceil(22.11) = 23`.
>
> _Đáp án:_ 23 chunks.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Khi overlap tăng lên 100, số chunk là `ceil((10,000 - 100) / (500 - 100)) = ceil(9,900 / 400) = 25`, tức tăng từ 23 lên 25. Overlap lớn hơn giúp giữ lại ngữ cảnh tại ranh giới giữa hai chunk, nhưng làm tăng số chunk, dung lượng lưu trữ và chi phí xử lý embedding.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

> Tôi dùng regex `(?<=[.!?])[ \t]+|(?<=\.)\r?\n+` để tách tại khoảng trắng sau dấu `.`, `!`, `?` hoặc tại xuống dòng sau dấu chấm, đồng thời giữ lại dấu câu trong câu trước. Các phần rỗng được loại bỏ, mỗi câu được `strip()` và sau đó được nhóm theo `max_sentences_per_chunk`; văn bản rỗng hoặc chỉ có khoảng trắng trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Thuật toán thử lần lượt các separator theo thứ tự ưu tiên `\n\n`, `\n`, `. `, khoảng trắng và cuối cùng là chuỗi rỗng; các phần còn quá dài tiếp tục được xử lý đệ quy bằng separator kế tiếp. Base case là khi đoạn hiện tại không rỗng và có độ dài không vượt `chunk_size`; nếu đã hết separator, thuật toán fallback sang cắt trực tiếp theo số ký tự để bảo đảm luôn dừng và không tạo chunk rỗng.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

> `add_documents` tạo một record in-memory cho từng `Document`, sao chép metadata, bổ sung `doc_id` nếu thiếu, sinh embedding và gán mã nội bộ duy nhất trước khi lưu vào `_store`. Khi tìm kiếm, truy vấn được embed một lần, sau đó tính dot product với embedding của từng record; do mock/local embedder trả vector đã chuẩn hóa, dot product đóng vai trò điểm cosine similarity, rồi kết quả được sắp xếp giảm dần và giới hạn theo `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

> `search_with_filter` lọc candidate theo exact-match của tất cả cặp key/value trong metadata trước khi tính điểm và xếp hạng, sau đó tái sử dụng `_search_records` để tránh lặp logic tìm kiếm. `delete_document` tạo lại danh sách `_store` sau khi loại toàn bộ record có `metadata.doc_id` trùng với ID cần xóa và trả về `True` khi kích thước store thực sự giảm.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

> `answer` truy xuất `top_k` chunk liên quan, đánh số từng context và gắn thông tin nguồn từ `source`, `source_url` hoặc `doc_id` nếu có. Các chunk được ghép vào prompt cùng câu hỏi và chỉ dẫn chỉ trả lời dựa trên context; nếu context không chứa đáp án thì phải nói thông tin chưa có trong knowledge base, sau đó prompt được truyền vào `llm_fn` đúng một lần.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collecting ... collected 42 items

TestProjectStructure:                    2 passed
TestClassBasedInterfaces:                2 passed
TestFixedSizeChunker:                    7 passed
TestSentenceChunker:                     4 passed
TestRecursiveChunker:                    4 passed
TestEmbeddingStore:                      8 passed
TestKnowledgeBaseAgent:                  2 passed
TestComputeSimilarity:                   4 passed
TestCompareChunkingStrategies:           3 passed
TestEmbeddingStoreSearchWithFilter:      3 passed
TestEmbeddingStoreDeleteDocument:        3 passed

============================= 42 passed in 0.11s ==============================
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Tôi chốt dự đoán trước khi chạy mô hình và dùng ngưỡng `0.50`: score từ `0.50` trở lên được xem là cao, dưới `0.50` được xem là thấp. Cả năm cặp được đánh giá bằng cùng mô hình `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.

| Cặp | Câu A | Câu B | Dự đoán    | Điểm thực tế | Đúng? |
| --- | ----- | ----- | ---------- | ------------ | ----- |
| 1 | Sinh viên đại học được mượn tối đa ba tài liệu trong hai tuần. | Mỗi sinh viên bậc đại học có thể vay ba tài liệu với thời hạn mượn hai tuần. | cao | 0.6834 | Có |
| 2 | Người dùng không nên gửi lại thanh toán nếu giao dịch trực tuyến thất bại. | Users should not submit another payment after an online transaction fails. | cao | -0.0914 | Không |
| 3 | Sách Course Reserve chỉ được mượn trong hai giờ. | Mỗi người chỉ được mượn một tài liệu Course Reserve tại một thời điểm. | cao | 0.7985 | Có |
| 4 | Sinh viên được phép gia hạn sách một lần. | Sinh viên không được phép gia hạn sách. | thấp | 0.9705 | Không |
| 5 | Phí trả sách quá hạn là 10.000 đồng mỗi ngày. | Dự báo thời tiết cho biết ngày mai có mưa lớn. | thấp | 0.4292 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

> Bất ngờ nhất là cặp 4 có score `0.9705` dù hai câu đối lập vì từ phủ định “không”; mô hình nhận diện rất mạnh phần từ vựng và cấu trúc chung nhưng chưa phản ánh tốt quan hệ phủ định. Cặp song ngữ ở cặp 2 cũng có score thấp `-0.0914` dù cùng ý nghĩa, cho thấy nhãn “multilingual” không bảo đảm mọi cách diễn đạt xuyên ngôn ngữ đều được căn chỉnh tốt. Vì vậy score embedding cần được kiểm tra bằng dữ liệu thực tế thay vì xem như bằng chứng tuyệt đối về ý nghĩa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Tôi dùng corpus `data/k3_library`, mô hình `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` và `RecursiveChunker` với `chunk_size=500`, ưu tiên separator theo heading: `\n## `, `\n### `, `\n\n`, `\n`, `. `, khoảng trắng và fallback theo ký tự. Cấu hình tạo 50 chunk và được giữ nguyên cho cả năm câu hỏi; Q1 và Q3 dùng thêm filter `audience=student`. Để chạy luồng `KnowledgeBaseAgent` mà không dùng dịch vụ chat bên ngoài, `llm_fn` là hàm extractive cục bộ chọn các dòng trong context có độ phủ từ khóa cao nhất; các nhận xét dưới đây không được trình bày như kết quả của một generative LLM. Có thể tái lập thí nghiệm bằng `python bench.py`; raw top-3 được lưu tại [`results/vu_tien_dung_recursive.json`](../results/vu_tien_dung_recursive.json).

| #   | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
| --- | --------------- | ------------------------------------ | ---------- | ------------------------------ | ------------------------------- |
| 1 | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed? | Chính sách undergraduate: tối đa 3 tài liệu, thời hạn 2 tuần; chunk chưa chứa quy định gia hạn. | 0.6570 | Có, nhưng chỉ bao phủ một phần gold answer. | Trả đúng 3 tài liệu/2 tuần nhưng bỏ sót số lần gia hạn vì section `Renewal` không xuất hiện trong top-3. |
| 2 | How many Course Reserve books may one user borrow at a time? | Bảng Course Reserve: một tài liệu mỗi người tại một thời điểm, sử dụng trong 2 giờ. | 0.6869 | Có, đúng ngay top-1. | Trả đúng một Course Reserve item trong 2 giờ, nhưng kèm thêm một câu không liên quan về graduate borrowing. |
| 3 | What is the overdue fine for normal material, Course Reserve material, and equipment? | Normal: 10.000 VND/ngày; Course Reserve: 10.000 VND/giờ; equipment: 10.000 VND/ngày. | 0.5733 | Có, đúng ngay top-1. | Trả đủ và đúng cả ba mức phạt theo gold answer. |
| 4 | How long is a requested library item held after it is ready for collection? | Top-1 nói về thời hạn mượn thiết bị một ngày làm việc, không trả lời thời gian giữ item được yêu cầu. | 0.6241 | Không ở top-1; chunk đúng nằm ở top-2. | Nhờ context top-3, agent vẫn tìm được thông tin item được giữ trong 2 ngày. |
| 5 | What should a user do when an online library payment fails after accurate card information was entered? | Không gửi lại thanh toán nhiều lần và liên hệ nhân viên tại circulation desk. | 0.7383 | Có, đúng ngay top-1. | Trả đúng hai hành động: không submit lại và liên hệ library staff để được hỗ trợ. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

> Qua bộ benchmark chung do nhóm tổng hợp, tôi học được rằng cần khóa gold answer và evidence section trước khi xem kết quả để tránh đánh giá relevance theo cảm tính. Q4 cho thấy score cao nhất chưa bảo đảm top-1 trả lời đúng câu hỏi, còn Q1 cho thấy một heading bị tách khỏi chunk được truy xuất có thể làm agent bỏ sót điều kiện quan trọng; vì vậy luôn phải kiểm tra nội dung top-3 và metadata chứ không chỉ nhìn score.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí                                        | Điểm tự đánh giá |
| ----------------------------------------------- | ---------------- |
| Khởi động (Warm-up)                             | 5 / 5            |
| Hướng tiếp cận của tôi (My Approach)            | 10 / 10          |
| Hoàn thiện code (Core Implementation — tests)   | 30 / 30          |
| Dự đoán độ tương tự (Similarity Predictions)    | 5 / 5            |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10           |
| **Tổng phần cá nhân**                           | **58 / 60**       |
