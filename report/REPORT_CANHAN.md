# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Lê Minh Ngọc
**Nhóm:** F2- D305
**Ngày:** 03/08/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là hai vector embedding hướng gần giống nhau, nên hai đoạn văn bản thường diễn đạt nội dung hoặc ý nghĩa gần nhau. Điểm càng gần 1 thì hướng của hai vector càng tương đồng.

**Ví dụ có độ tương tự CAO:**
- Câu A: Sinh viên có thể gia hạn sách thư viện trực tuyến.
- Câu B: Người học được phép kéo dài thời gian mượn sách qua hệ thống online.
- Tại sao tương đồng: Hai câu dùng từ khác nhau nhưng cùng nói về việc sinh viên gia hạn sách bằng hệ thống trực tuyến.

**Ví dụ có độ tương tự THẤP:**
- Câu A: Sinh viên có thể gia hạn sách thư viện trực tuyến.
- Câu B: Hôm nay trời có mưa lớn ở Hà Nội.
- Tại sao khác: Một câu nói về dịch vụ thư viện, câu còn lại nói về thời tiết nên gần như không có quan hệ ngữ nghĩa.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Cosine tập trung vào góc, tức hướng ngữ nghĩa của vector, thay vì độ lớn tuyệt đối. Khoảng cách Euclid nhạy với độ lớn vector, nên hai vector cùng hướng nhưng có độ lớn khác nhau vẫn có thể bị xem là xa; điều này thường không phù hợp bằng cosine khi so sánh text embedding.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: `ceil((10,000 - 50) / (500 - 50)) = ceil(9,950 / 450) = ceil(22.111...)`.
> Đáp án: **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap bằng 100: `ceil((10,000 - 100) / (500 - 100)) = ceil(9,900 / 400) = 25`, nên số chunk tăng từ 23 lên **25**. Tăng overlap giúp giữ ngữ cảnh nằm sát ranh giới giữa hai chunk, đổi lại phải lưu nhiều dữ liệu lặp hơn và tìm kiếm tốn chi phí hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Tôi dùng regex `(?<=[.!?])(?:[ \t]+|\n+)` để tách sau dấu kết thúc câu nhưng vẫn giữ lại dấu câu trong nội dung. Các câu được loại khoảng trắng thừa rồi gom tối đa `max_sentences_per_chunk` câu; văn bản rỗng hoặc chỉ chứa khoảng trắng trả về danh sách rỗng.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán thử lần lượt các separator theo độ ưu tiên: đoạn văn, dòng, câu, từ rồi ký tự. Base case là đoạn đã ngắn hơn hoặc bằng `chunk_size`; nếu một mảnh vẫn quá dài thì `_split` gọi đệ quy với separator tiếp theo, còn khi hết separator thì cắt cứng theo số ký tự để bảo đảm thuật toán dừng và chunk không vượt kích thước.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> `add_documents` tạo embedding cho nội dung, sao chép metadata, bổ sung `doc_id` nếu thiếu rồi lưu một record chuẩn hóa; bộ nhớ là nguồn dữ liệu chính và ChromaDB được dùng như backend tùy chọn nếu có. `search` embed câu hỏi, tính dot product với từng embedding và sắp xếp điểm giảm dần; do các backend của lab chuẩn hóa vector, dot product tương đương cosine similarity.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> `search_with_filter` lọc record theo tất cả cặp khóa–giá trị metadata trước rồi mới tính điểm, nhờ vậy top-k chỉ cạnh tranh trong đúng nhóm cần tìm. `delete_document` tìm và xóa tất cả record có `metadata["doc_id"]` tương ứng, vì một tài liệu nguồn có thể đã được tách thành nhiều chunk; hàm trả về `True` chỉ khi thực sự có record bị xóa.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> `answer` truy xuất top-k chunk, đánh số từng chunk rồi đưa chúng vào phần `NGỮ CẢNH`, sau đó thêm `CÂU HỎI` và vị trí `TRẢ LỜI`. Prompt yêu cầu LLM chỉ dùng ngữ cảnh đã truy xuất và nói rõ khi thiếu thông tin nhằm giảm câu trả lời bịa đặt.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
> py -3.11 -m pytest tests/ -v -p no:cacheprovider
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 42 items

tests/test_solution.py ..........................................       [100%]
============================= 42 passed in 0.07s ==============================
```

**Số lượng bài test vượt qua (pass):** **42 / 42**

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Sinh viên được mượn ba cuốn sách trong hai tuần. | Người học có thể mượn 3 tài liệu trong 14 ngày. | cao | 0.7873 | Có |
| 2 | Phí trả sách quá hạn được tính theo ngày. | Hôm nay đội tuyển bóng đá thi đấu trận chung kết. | thấp | -0.0097 | Có |
| 3 | Người dùng không nên thanh toán lại khi giao dịch thất bại. | Users should not submit another payment after a failed transaction. | cao | 0.8371 | Có |
| 4 | Sách được giữ trong hai ngày để người dùng đến nhận. | Thiết bị quá hạn bị phạt 10.000 đồng mỗi ngày. | thấp | 0.0718 | Có |
| 5 | Sinh viên được phép gia hạn sách một lần. | Sinh viên không được phép gia hạn sách. | thấp | 0.5122 | Không hoàn toàn — điểm vẫn ở mức trung bình |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp 5 bất ngờ nhất: hai câu trái nghĩa vì có và không có từ phủ định “không”, nhưng vẫn đạt 0.5122 do gần như toàn bộ từ còn lại giống nhau. Kết quả cho thấy embedding nắm bắt chủ đề và từ vựng tốt nhưng cosine similarity không tự bảo đảm hiểu chính xác phép phủ định. Cặp 3 đạt 0.8371 cũng xác nhận model có khả năng nối ý nghĩa giữa tiếng Việt và tiếng Anh.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed? | Chính sách mượn sách của sinh viên đại học | 0.655 | Có | Context cho biết: 3 tài liệu, 2 tuần và được gia hạn 1 lần |
| 2 | How many Course Reserve books may one user borrow at a time? | Trang Course Reserve nói về thời hạn sử dụng nhưng thiếu giới hạn một tài liệu | 0.629 | Chỉ liên quan một phần | Context chỉ đủ kết luận thời hạn 2 giờ; chưa đủ căn cứ cho “1 item/user” |
| 3 | What is the overdue fine for normal material, Course Reserve material, and equipment? | Quy định tài chính về ba loại phí quá hạn | 0.593 | Có | 10.000 VND/ngày cho tài liệu thường; 10.000 VND/giờ cho Course Reserve; 10.000 VND/ngày cho thiết bị |
| 4 | How long is a requested library item held after it is ready for collection? | Phần Requests and Holds của chính sách sinh viên; nguồn chuẩn circulation policy xuất hiện ở rank 2 | 0.738 | Có về nội dung; khác nguồn chuẩn | Tài liệu được giữ 2 ngày, sau đó yêu cầu bị hủy nếu không đến nhận |
| 5 | What should a user do when an online library payment fails after accurate card information was entered? | Phần Unsuccessful Transactions và hướng dẫn liên hệ quầy thư viện | 0.698 | Có | Không gửi lại thanh toán nhiều lần; liên hệ nhân viên tại circulation desk |

**Bao nhiêu câu hỏi trả về đủ bằng chứng liên quan trong top-3?** **4 / 5** với local multilingual embedder. Câu 2 lấy đúng chủ đề nhưng thiếu giới hạn “1 Course Reserve item per user”. Các câu trả lời trong bảng là phần tóm tắt có thể trích từ context; chưa dùng generative LLM để diễn đạt lại.

### Thử nghiệm nhiều chiến thuật Chunking

Tôi chạy cùng 5 benchmark queries trên 7 tài liệu trong `data/k3_library` bằng model thật `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Metric `AnswerHit@k` yêu cầu các chunk từ đúng tài liệu bao phủ ít nhất 65% content tokens của gold answer; `MRR@5` thưởng cho chiến thuật đưa đủ bằng chứng lên thứ hạng sớm. Cách chấm này nghiêm ngặt hơn việc chỉ kiểm tra đúng tên tài liệu.

| Chiến thuật | Số chunk | Độ dài TB | Dữ liệu tăng/giảm | AnswerHit@1 | AnswerHit@3 | AnswerHit@5 | MRR@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed 500, overlap 0 | 33 | 435.3 | +0.0% | 3/5 | 4/5 | 4/5 | 0.667 |
| **Fixed 500, overlap 100** | **38** | **459.6** | **+21.6%** | **3/5** | **4/5** | **4/5** | **0.700** |
| 4 câu, overlap 0 câu | 40 | 356.8 | -0.7% | 2/5 | 2/5 | 2/5 | 0.400 |
| 4 câu, overlap 1 câu | 50 | 364.7 | +26.9% | 3/5 | 4/5 | 4/5 | 0.700 |
| Recursive 500 | 41 | 348.8 | -0.5% | 3/5 | 4/5 | 4/5 | 0.700 |
| Heading + Recursive 500 | 57 | 254.1 | +0.8% | 3/5 | 3/5 | 4/5 | 0.640 |

#### Tại sao chọn Fixed 500, overlap 100 ký tự?

Với local multilingual embedder, Fixed 500 + overlap 100 đạt AnswerHit@3 bằng 4/5 và MRR@5 bằng 0.700. Sentence overlap và Recursive cũng đạt 4/5, MRR 0.700, nhưng lần lượt tạo 50 và 41 chunk; Fixed overlap chỉ tạo 38 chunk nên cần ít embedding và ít bản ghi hơn. So với Fixed không overlap, overlap 100 đưa bằng chứng câu 4 từ rank 3 lên rank 2, làm MRR tăng từ 0.667 lên 0.700.

Overlap bằng 100 tương đương 20% kích thước chunk. Với `chunk_size=500`, bước trượt là `500 - 100 = 400` ký tự:

```text
Chunk 1: text[0:500]
                     └── 100 ký tự dùng chung ──┐
Chunk 2:                              text[400:900]
```

Như vậy 100 ký tự cuối của chunk trước chính là 100 ký tự đầu của chunk sau. Phần dùng chung giúp một câu hoặc điều kiện nằm sát ranh giới vẫn xuất hiện đầy đủ hơn ở ít nhất một chunk. Đánh đổi là dữ liệu tăng 21.6%; vì Hit@k không tăng nhưng thứ hạng câu 4 tốt hơn, tôi xem đây là mức overlap vừa phải chứ không tăng cao hơn.

#### Tại sao chọn embedding này?

Tôi chọn `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` vì bộ dữ liệu và câu hỏi có thể gồm cả tiếng Việt lẫn tiếng Anh; kết quả cặp similarity số 3 (0.8371) cho thấy model nối được hai câu cùng nghĩa khác ngôn ngữ. Model chạy cục bộ, không cần API key và trả vector chuẩn hóa, nên dot product trong `EmbeddingStore` tương đương cosine similarity. Mock embedder không được chọn vì gần như ngẫu nhiên theo toàn chuỗi; TF-IDF chỉ khớp từ vựng và xử lý paraphrase/chuyển ngữ kém hơn.

#### Tại sao chọn `top_k=3`?

| top_k | Số câu có đủ bằng chứng | Đánh đổi |
|---:|---:|---|
| 1 | 3/5 | Ít context nhất nhưng thiếu bằng chứng cho câu 2 và 4 |
| 2 | 4/5 | Lấy được bằng chứng câu 4 ở rank 2 nhưng vẫn thiếu câu 2 |
| **3** | **4/5** | Phù hợp rubric top-3 và có thêm một chunk dự phòng |
| 5 | 4/5 | Không sửa được câu 2, nhưng tăng nhiễu và số token prompt |

Với chiến thuật đã chọn, bằng chứng xuất hiện ở rank `[1, không tìm thấy trong top-5, 1, 2, 1]`. Top-k bằng 2 đã lấy được toàn bộ bốn câu mà hệ thống có thể truy xuất trong thí nghiệm này; tôi vẫn chọn mặc định `top_k=3` vì rubric đánh giá top-3 và chunk thứ ba là biên an toàn nhỏ cho câu hỏi mới. Top-k bằng 5 không cải thiện coverage nên chỉ tăng độ dài prompt và nguy cơ gây nhiễu.

#### Failure case và cách cải thiện

Câu 2 về Course Reserve là failure case: top-1 là trang `course-reserve`, trong đó có thời hạn sử dụng 2 giờ nhưng không có giới hạn “1 item per user”; thông tin đầy đủ nằm trong `circulation-policy` phiên bản 4.0. Tăng top-k đến 5 vẫn không đạt ngưỡng bằng chứng. Có thể cải thiện bằng cách ưu tiên metadata `document_version=4.0` hoặc `category=circulation-policy`, tăng trọng số nguồn chính sách có phiên bản, và giữ tiêu đề bảng cùng các dòng Course Reserve trong một chunk.

**Lệnh tái lập:**

```powershell
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
py -3.11 scripts/compare_individual_strategies.py --embedding local
py -3.11 scripts/run_similarity_predictions.py
```

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Điều quan trọng nhất tôi rút ra khi so sánh các chiến thuật là không nên chọn chunking chỉ bằng cảm giác. Cần chạy cùng một benchmark và xem đồng thời độ bao phủ, thứ hạng, số chunk và failure case; overlap nhiều hơn không tự động làm retrieval tốt hơn.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá |
|----------|-------------------|
| Khởi động (Warm-up) | 5 / 5 |
| Hướng tiếp cận của tôi (My Approach) | 10 / 10 |
| Hoàn thiện code (Core Implementation — tests) | 30 / 30 |
| Dự đoán độ tương tự (Similarity Predictions) | 5 / 5 |
| Kết quả truy xuất của tôi (Competition Results) | 8 / 10 |
| **Tổng phần cá nhân** | **58 / 60** |
