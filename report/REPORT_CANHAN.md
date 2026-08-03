# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Sinh viên
**Nhóm:** K3_Library
**Ngày:** 03/08/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Độ tương tự cosine cao nghĩa là góc giữa hai vector embedding trong không gian đa chiều rất nhỏ (tiệm cận 0 độ, giá trị cosine tiệm cận 1.0), chứng tỏ hai đoạn văn bản có sự tương đồng hoặc rất gần gũi về mặt ý nghĩa ngữ nghĩa (semantic meaning), dù cách dùng từ hay cấu trúc câu có thể khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Thư viện trường mở cửa vào những khung giờ nào?"
- Câu B: "Thời gian hoạt động chi tiết của thư viện như thế nào?"
- Tại sao tương đồng: Cả hai câu đều hướng tới cùng một ý định tra cứu (intent) về lịch mở cửa của thư viện, mặc dù không sử dụng chính xác các từ giống hệt nhau.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Sinh viên đại học được mượn tối đa bao nhiêu quyển sách?"
- Câu B: "Hướng dẫn quy trình thanh toán học phí qua thẻ ngân hàng."
- Tại sao khác: Hai câu đề cập đến hai chủ đề hoàn toàn độc lập (quy định mượn sách thư viện vs thủ tục tài chính học phí), nằm ở hai vùng không gian ngữ nghĩa khác nhau.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Khoảng cách Euclid bị phụ thuộc mạnh vào độ dài (độ lớn/magnitude) của vector (thường bị ảnh hưởng bởi độ dài văn bản). Trong khi đó, Cosine similarity chỉ đo hướng (độ lệch góc) của vector, giúp đánh giá mức độ tương đồng ngữ nghĩa một cách chính xác mà không bị biến dạng khi so sánh giữa đoạn văn dài và đoạn văn ngắn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
> `số lượng chunk = làm_tròn_lên((10000 - 50) / (500 - 50)) = làm_tròn_lên(9950 / 450) = làm_tròn_lên(22.111)`
> *Đáp án:* **23 chunks**

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Khi overlap tăng lên 100: `số lượng chunk = làm_tròn_lên((10000 - 100) / (500 - 100)) = làm_tròn_lên(9900 / 400) = làm_tròn_lên(24.75) = 25 chunks` (tăng 2 chunks).
> Việc tăng độ chồng chéo giúp giữ lại ngữ cảnh liên tục ở đường ranh giới giữa 2 chunk liền kề, tránh việc cắt đôi một câu hoặc một ý quan trọng, từ đó giúp mô hình truy xuất ngữ cảnh đầy đủ hơn.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Sử dụng biểu thức chính quy `re.split(r'(?<=[.!?])\s+|(?<=\.\n)\s*', text)` để tách các câu dựa trên dấu chấm, dấu chấm cảm, dấu hỏi hoặc xuống dòng sau dấu chấm. Xử lý các edge case như văn bản rỗng bằng cách trả về danh sách rỗng, đồng thời dùng `.strip()` làm sạch từng câu và gộp tối đa `max_sentences_per_chunk` câu vào mỗi chunk.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Áp dụng thuật toán đệ quy thử nghiệm danh sách các dấu phân tách theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]`. Nếu đoạn văn bản hiện tại có độ dài $\le$ `chunk_size` thì giữ nguyên (base case); nếu lớn hơn thì tách theo separator đầu tiên và tiếp tục gọi đệ quy `_split` trên các phần tử nhỏ hơn, sau đó gộp các phần tử lân cận lại nếu tổng độ dài vẫn $\le$ `chunk_size`.

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:
> Với `add_documents`, chuẩn hóa dữ liệu thành các dictionary gồm `id`, `content`, `metadata` và vector nhúng `embedding` thu được từ `_embedding_fn`, sau đó lưu vào danh sách `self._store`. Với `search`, nhúng câu hỏi `query`, tính điểm tương đồng (tích vô hướng `_dot`) với từng bản ghi trong `_store`, sắp xếp giảm dần theo điểm `score` và trả về `top_k` kết quả tốt nhất.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> Trong `search_with_filter`, thực hiện tiền lọc (pre-filtering) dữ liệu trước bằng cách chỉ giữ lại các bản ghi mà toàn bộ thuộc tính trong `metadata_filter` khớp với `metadata` của chunk, sau đó mới tính điểm tương đồng. Trong `delete_document`, lọc bỏ các bản ghi có `id == doc_id` hoặc `metadata['doc_id'] == doc_id` và trả về `True` nếu kích thước store giảm xuống.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Gọi `self.store.search(question, top_k=top_k)` để thu thập các chunks ngữ cảnh có độ tương đồng cao nhất. Sau đó ghép nội dung các chunks phân cách bởi `\n---\n` để tạo thành ngữ cảnh (Context), xây dựng Prompt theo cấu trúc `f"Context:\n{context_str}\n\nQuestion: {question}\nAnswer:"` và truyền cho hàm `llm_fn` tạo câu trả lời.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
```

**Số lượng bài test vượt qua (pass):** 42 / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

| Cặp | Câu A | Câu B | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Quy định mượn sách thư viện VinUni | Thủ tục mượn sách cho sinh viên đại học | cao | 0.92 | Đúng |
| 2 | Thời hạn trả sách thư viện là bao lâu? | Hướng dẫn nộp học phí trực tuyến | thấp | 0.15 | Đúng |
| 3 | Giảng viên mượn tối đa 5 tài liệu | Sinh viên cao học mượn 5 tài liệu | cao | 0.85 | Đúng |
| 4 | Nộp phạt quá hạn trực tuyến | Thanh toán phí dịch vụ qua cổng ngân hàng | cao | 0.78 | Đúng |
| 5 | Sách Course Reserve đọc tại chỗ 2 giờ | Thiết bị thư viện mượn 1 ngày làm việc | thấp | 0.32 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> Cặp số 4 cho điểm độ tương tự khá cao (0.78) mặc dù một câu nói về nộp phạt thư viện còn một câu nói về thanh toán học phí nói chung. Điều này cho thấy mô hình nhúng (embeddings) biểu diễn văn bản dựa trên không gian khái niệm rộng (khái niệm thanh toán trực tuyến/phí) thay vì chỉ khớp chính xác từng từ khóa đơn lẻ.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trong `data/k3_library/benchmark.csv` bằng mô hình nhúng `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` và chiến lược `RecursiveChunker (350)`.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed? *(audience=student)* | An undergraduate student may borrow 3 items for 2 weeks and renew once. (`undergraduate-borrowing.md`) | 0.6599 | Có | Sinh viên đại học được mượn tối đa 3 tài liệu, thời hạn 2 tuần và gia hạn 1 lần. |
| 2 | How many Course Reserve books may one user borrow at a time? | 1 Course Reserve item per user at a time; Course Reserve use is limited to 2 hours. (`circulation-policy.md`) | 0.8153 | Có | Mỗi người dùng được mượn tối đa 1 tài liệu Course Reserve tại một thời điểm, dùng tối đa 2 giờ. |
| 3 | What is the overdue fine for normal material, Course Reserve material, and equipment? *(audience=student)* | Normal: 10,000 VND/day; Course Reserve: 10,000 VND/hour; Equipment: 10,000 VND/day. (`financial-regulations-library-fees.md`) | 0.5751 | Có | Phạt quá hạn: Tài liệu thường 10k/ngày, Course Reserve 10k/giờ, Thiết bị 10k/ngày. |
| 4 | How long is a requested library item held after it is ready for collection? | A requested item is held for 2 days; if not collected within that period, the request is canceled. (`circulation-policy.md`) | 0.6543 | Có | Tài liệu yêu cầu giữ trong 2 ngày; quá thời hạn yêu cầu sẽ tự động bị hủy. |
| 5 | What should a user do when an online library payment fails after accurate card information was entered? | The user should not submit another payment and should contact library staff at the circulation desk. (`fines-and-payment.md`) | 0.7556 | Có | Không thực hiện lại thanh toán và liên hệ ngay nhân viên thư viện tại bàn lưu thông để hỗ trợ. |

### So Sánh Điểm Số Giữa Các Chiến Lược Chunking (từ `report/benchmark_chunking_comparison.md`):
- **FixedSizeChunker (500, 50)**: Điểm trung bình `0.6504` — cắt kích thước cố định, dễ gây đứt đoạn câu giữa chừng hoặc chứa thông tin thừa.
- **SentenceChunker (3 câu)**: Điểm trung bình `0.6382` — chunk ngắn gọn, nhưng với các văn bản quy định dài 3 câu chưa bao phủ đủ ngữ cảnh.
- **RecursiveChunker (350)**: Điểm trung bình `0.6920` (**Tối ưu nhất, Top-1 Match đạt cao nhất `0.8153`**) — bảo tồn trọn vẹn ranh giới tiêu đề mục và đoạn văn.

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** 5 / 5

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> Sử dụng pre-filtering theo metadata (`audience: student`) trước khi tìm kiếm vector giúp loại bỏ hoàn toàn các đoạn nhiêu thuộc về đối tượng khác (như giảng viên hay nhân viên), giúp câu trả lời của Agent chính xác và đúng đối tượng hơn.

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
