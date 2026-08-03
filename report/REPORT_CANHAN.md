# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Đức Chung
**Nhóm:** F2
**Ngày:** 03/08/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai vector embedding có hướng gần nhau, vì vậy hai đoạn văn bản thường biểu diễn nội dung hoặc ý nghĩa tương tự. Giá trị càng gần 1 thì mức độ tương đồng về ngữ nghĩa càng cao.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên có thể gia hạn sách qua cổng thông tin thư viện.
- Câu B: Người học được phép kéo dài thời gian mượn tài liệu trực tuyến.
- Tại sao tương đồng: Hai câu sử dụng từ khác nhau nhưng cùng nói về việc sinh viên gia hạn tài liệu thư viện qua hệ thống trực tuyến.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Sinh viên đăng ký học phần trên cổng học vụ.
- Câu B: Thời tiết hôm nay có mưa lớn.
- Tại sao khác: Hai câu thuộc hai chủ đề không liên quan, một câu nói về hoạt động học vụ và câu còn lại nói về thời tiết.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine similarity tập trung vào hướng của vector nên ít bị ảnh hưởng bởi độ lớn của vector, phù hợp khi cần so sánh ý nghĩa văn bản. Khi embedding đã được chuẩn hóa về độ dài 1, tích vô hướng cũng chính là cosine similarity và có thể được dùng để xếp hạng nhanh.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Bước nhảy giữa hai chunk là `500 - 50 = 450` ký tự. Áp dụng công thức: `ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.111...) = 23`.
>
> **Đáp án: 23 chunks.**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100, bước nhảy còn `500 - 100 = 400`, nên số chunk là `ceil((10000 - 100) / 400) = ceil(24.75) = 25`. Overlap lớn hơn giúp bảo toàn thông tin nằm ở ranh giới giữa hai chunk, nhưng làm tăng dữ liệu lặp, số embedding và chi phí lưu trữ/tìm kiếm.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng biểu thức chính quy `(?<=[.!?])(?:[ \t]+|\r?\n+)` để tách tại khoảng trắng hoặc xuống dòng đứng sau dấu kết thúc câu, đồng thời giữ dấu câu ở câu phía trước. Các câu rỗng và khoảng trắng thừa được loại bỏ; văn bản rỗng trả về danh sách rỗng. Sau đó, các câu được gom tuần tự theo `max_sentences_per_chunk`, với giá trị tối thiểu là một câu mỗi chunk.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử các separator theo thứ tự ưu tiên: đoạn văn, dòng, câu, từ và cuối cùng là ký tự. Base case là văn bản rỗng hoặc văn bản đã ngắn hơn `chunk_size`; nếu không còn separator phù hợp, văn bản được cắt cứng theo số ký tự. Các phần nhỏ liền nhau được ghép lại khi tổng độ dài chưa vượt `chunk_size`, giúp tránh tạo quá nhiều chunk rất ngắn.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Mỗi `Document` được chuyển thành một record gồm ID lưu trữ duy nhất, nội dung, bản sao metadata và embedding. Nếu metadata chưa có `doc_id`, ID tài liệu gốc được bổ sung để hỗ trợ truy vết và xóa theo tài liệu. Khi tìm kiếm, query chỉ được embedding một lần; hệ thống tính dot product với từng embedding đã lưu, sắp xếp score giảm dần và trả tối đa `top_k` kết quả.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc record theo tất cả cặp khóa–giá trị metadata trước, sau đó mới tính điểm trên tập ứng viên còn lại. Cách lọc trước giúp tránh các tài liệu sai đối tượng tham gia xếp hạng. `delete_document` tìm và xóa toàn bộ chunk có cùng `metadata['doc_id']`, trả về `True` nếu có dữ liệu bị xóa và `False` nếu không tìm thấy.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Agent truy xuất top-k chunk liên quan, rồi ghép từng chunk vào prompt cùng `doc_id` và nguồn để có thể truy vết. Prompt yêu cầu LLM chỉ sử dụng phần `RETRIEVED CONTEXT`, không tự bịa và phải thừa nhận khi ngữ cảnh không đủ. Câu hỏi được đặt sau context trước khi gọi hàm `llm_fn` để sinh câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
Môi trường: Python 3.11.15, pytest 9.1.1
Lệnh: python -m pytest tests -v -p no:cacheprovider
Kết quả: collected 42 items — 42 passed in 0.13s
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Mô hình dùng để thực nghiệm: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (embedding 384 chiều, chuẩn hóa vector).

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên có thể gia hạn sách trực tuyến. | Người học được phép kéo dài thời gian mượn tài liệu qua website. | Cao | 0.685151 | Đúng |
| 2 | Undergraduate students may borrow three library items. | The borrowing limit for undergraduate students is three items. | Cao | 0.736967 | Đúng |
| 3 | The library explains how to renew a book. | Renewable energy reduces fossil-fuel consumption. | Thấp | 0.115043 | Đúng |
| 4 | Sinh viên đại học được mượn sách trong hai tuần. | Undergraduate students may borrow books for two weeks. | Cao | 0.886312 | Đúng |
| 5 | Course Reserve materials may be used for two hours. | The weather forecast predicts heavy rain tomorrow. | Thấp | 0.022651 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Kết quả nổi bật nhất là cặp 4 đạt `0.886312`, cao nhất trong năm cặp dù hai câu dùng hai ngôn ngữ khác nhau. Điều này cho thấy mô hình multilingual ánh xạ câu tiếng Việt và tiếng Anh có cùng ý nghĩa vào các vùng rất gần nhau trong không gian vector. Cặp 3 chỉ đạt `0.115043` dù có các từ bề mặt gần nhau như *renew* và *renewable*, cho thấy embedding ưu tiên ngữ nghĩa toàn câu hơn sự giống nhau của một từ đơn lẻ.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

**Thiết lập thực nghiệm:** Tôi dùng cùng corpus `data/k3_library` và đúng năm câu hỏi trong `benchmark.csv`. Mô hình embedding là `paraphrase-multilingual-MiniLM-L12-v2`. Tôi so sánh ba cấu hình: FixedSize 500/50 (34 chunks, top-3 hit 5/5, MRR 0.866667), Sentence 3 câu/chunk (51 chunks, top-3 hit 4/5, MRR 0.800000), và Recursive 500 (41 chunks, top-3 hit 5/5, MRR 0.800000). Tôi chọn **FixedSizeChunker (`chunk_size=500`, `overlap=50`)** làm chiến lược cá nhân vì đạt đủ 5/5 evidence hits và có thứ hạng trung bình tốt nhất.

> Repo chỉ cung cấp `demo_llm` trả về bản xem trước prompt, không phải mô hình sinh câu trả lời thật. Vì vậy cột cuối ghi **câu trả lời grounded dạng tóm tắt**, được rút trực tiếp từ evidence trong top-3 và đối chiếu với gold answer; không được trình bày như kết quả của một API LLM bên ngoài.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed? | `undergraduate-borrowing`: quyền mượn của sinh viên đại học; filter `audience=student`. | 0.654704 | Có — evidence ở rank 1 | Sinh viên đại học được mượn 3 tài liệu trong 2 tuần và được gia hạn một lần. |
| 2 | How many Course Reserve books may one user borrow at a time? | `course-reserve`: mô tả Course Reserve và thời gian sử dụng; evidence đầy đủ trong `circulation-policy` ở rank 3. | 0.628819 | Liên quan một phần — evidence chuẩn ở rank 3 | Mỗi người được mượn một Course Reserve item tại một thời điểm và chỉ sử dụng tối đa 2 giờ. |
| 3 | What is the overdue fine for normal material, Course Reserve material, and equipment? | `financial-regulations-library-fees`: bảng phí quá hạn; filter `audience=student`. | 0.592976 | Có — evidence ở rank 1 | Phí là 10.000 VND/tài liệu/ngày với tài liệu thường, 10.000 VND/tài liệu/giờ với Course Reserve và 10.000 VND/thiết bị/ngày. |
| 4 | How long is a requested library item held after it is ready for collection? | `circulation-policy`: quy trình yêu cầu và giữ tài liệu. | 0.618119 | Có — evidence ở rank 1 | Tài liệu được giữ 2 ngày; nếu không đến nhận trong thời hạn này thì yêu cầu bị hủy. |
| 5 | What should a user do when an online library payment fails after accurate card information was entered? | `fines-and-payment`: hướng dẫn xử lý giao dịch không thành công. | 0.757613 | Có — evidence ở rank 1 | Không gửi lại thanh toán nhiều lần; liên hệ nhân viên tại quầy lưu hành để được hỗ trợ. |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Kết quả chuẩn bị cho phần so sánh nhóm cho thấy không có một chunker luôn đứng đầu ở mọi câu hỏi. SentenceChunker tạo chunk dễ đọc nhưng bỏ lỡ evidence chuẩn của câu Course Reserve trong top-3; RecursiveChunker đưa evidence đó lên rank 1 nhưng làm evidence của hai câu khác xuống rank 2. FixedSize với overlap giữ được evidence của cả năm câu và đạt MRR cao nhất, cho thấy cần đánh giá bằng cùng benchmark thay vì chỉ nhìn độ mạch lạc của chunk.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 9 / 10 |
| **Tổng phần cá nhân** | **59 / 60** |
