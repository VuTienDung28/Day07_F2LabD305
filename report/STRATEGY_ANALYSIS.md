# Phân Tích Chiến Lược Chunking và Retrieval — Lab 7

**Sinh viên:** Chu Nguyễn Tuấn Anh  
**Nhóm:** F2  
**Corpus:** `k3_library.zip`  
**Benchmark:** 5 câu hỏi trong `benchmark.csv`

## 1. Mục tiêu và môi trường thử nghiệm

Mục tiêu của thử nghiệm là tìm chiến lược đưa đúng **chunk chứa đầy đủ bằng chứng của gold answer** lên top-3, ưu tiên top-1. Chỉ trùng `doc_id` chưa được tính là đúng nếu chunk trả về thuộc sai section hoặc không chứa dữ kiện cần thiết.

- Corpus: 7 tài liệu chính sách, FAQ và hướng dẫn thư viện VinUni.
- Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` qua `LocalEmbedder`.
- Similarity: cosine similarity trên embedding đã chuẩn hóa.
- Store: `EmbeddingStore`.
- Số kết quả kiểm tra: top-10 để xác định thứ hạng evidence; chất lượng chính thức được tính ở top-1 và top-3.
- Filter chung của benchmark: Q1 và Q3 bắt đầu với `audience=student`; các câu khác không lọc trừ khi ghi rõ.

### Tiêu chí liên quan của từng câu

| Câu | Evidence bắt buộc phải có trong cùng chunk |
|---|---|
| Q1 | 3 tài liệu, 2 tuần và gia hạn 1 lần |
| Q2 | 1 Course Reserve item/người/lần và thời hạn 2 giờ |
| Q3 | Cả ba mức phí cho tài liệu thường, Course Reserve và thiết bị |
| Q4 | Giữ 2 ngày và hủy yêu cầu nếu không nhận |
| Q5 | Không gửi lại thanh toán và liên hệ nhân viên thư viện |

Ký hiệu thứ hạng trong các bảng sau: `1` là evidence ở top-1, `2` là top-2, `0` là không có một chunk chứa **đủ** evidence trong top-10.

## 2. Phạm vi chiến lược đã thử

Các phép dò ban đầu bao phủ:

- `FixedSizeChunker`: `chunk_size` từ 300 đến 800, overlap 0, 50, 100 và 150.
- `SentenceChunker`: 1, 2, 3, 4, 5, 6, 8 và 10 câu/chunk.
- `RecursiveChunker`: nhiều kích thước từ 150 đến 650, sau đó chọn các mốc đại diện 250, 400, 500 và 600.
- Recursive ưu tiên heading: thử `##`, `###`, đoạn văn, dòng, câu và từ theo thứ tự.
- Heading-only: mỗi section Markdown là một chunk.
- Recursive 500 kết hợp metadata pre-filter theo từng query.

Không có cấu hình Fixed Size hoặc Sentence nào trong phạm vi trên đạt đủ 5/5 evidence ở top-3. Vì vậy, bảng dưới đây giữ các cấu hình đại diện thay vì liệt kê toàn bộ tổ hợp.

## 3. Kết quả so sánh đại diện

| Chiến lược | Số chunk | Q1 | Q2 | Q3 | Q4 | Q5 | Top-1 | Top-3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed 500, overlap 0 | 33 | 1 | 4 | 1 | 0 | 1 | 3/5 | 3/5 |
| Fixed 500, overlap 100 | 38 | 1 | 7 | 1 | 2 | 1 | 3/5 | 4/5 |
| Sentence, 3 câu/chunk | 51 | 0 | 0 | 1 | 1 | 1 | 3/5 | 3/5 |
| Sentence, 5 câu/chunk | 33 | 1 | 0 | 1 | 3 | 0 | 2/5 | 3/5 |
| Recursive 250 | 87 | 1 | 2 | 1 | 1 | 1 | 4/5 | 5/5 |
| Recursive 400 | 51 | 1 | 1 | 2 | 5 | 1 | 3/5 | 4/5 |
| Recursive 500 | 41 | 1 | 1 | 2 | 1 | 1 | 4/5 | 5/5 |
| Recursive 600 | 32 | 1 | 8 | 1 | 1 | 1 | 4/5 | 4/5 |
| Heading-aware Recursive 450 | 54 | 0 | 2 | 1 | 1 | 1 | 3/5 | 4/5 |
| Heading-only | 49 | 0 | 0 | 1 | 4 | 1 | 2/5 | 2/5 |
| **Recursive 500 + filter theo query** | **41** | **1** | **1** | **1** | **1** | **1** | **5/5** | **5/5** |

Hai cấu hình Recursive 250 và Recursive 500 đều đạt 5/5 top-3 trước khi thêm filter chi tiết. Recursive 500 tốt hơn về cân bằng vì dùng 41 chunks thay vì 87, giảm số vector cần lưu và tìm kiếm mà vẫn giữ được evidence.

## 4. Phân tích từng nhóm chiến lược

### 4.1. Fixed-size chunking

Fixed Size đơn giản và tạo các chunk có độ dài tương đối đồng đều, nhưng nó không hiểu ranh giới section, bảng hay câu. Với size 500 và overlap 0, Q4 không có đầy đủ evidence trong top-10 vì điểm cắt rơi vào khu vực thông tin request/hold. Overlap 100 giúp Q4 lên top-2 nhờ lặp lại ngữ cảnh ở biên, nhưng Q2 vẫn ở top-7.

Overlap làm tăng số chunk từ 33 lên 38 và cải thiện recall cho một số câu, nhưng không giải quyết được bản chất: một dòng bảng hoặc section có thể bị cắt theo số ký tự. Tăng overlap quá mức còn làm nhiều chunk gần như trùng nhau cạnh tranh trong kết quả.

### 4.2. Sentence chunking

Sentence chunking giữ câu hoàn chỉnh tốt hơn Fixed Size nhưng không phù hợp hoàn toàn với corpus có bảng Markdown và bullet list. Regex tách câu dựa trên `.`, `!`, `?`, trong khi một dòng bảng như `1 item/user/time` không nhất thiết có dấu kết câu.

Với 3 câu/chunk, Q3–Q5 hoạt động nhưng Q1 và Q2 không có một chunk chứa đủ evidence. Với 5 câu/chunk, Q1 được ghép đủ nhưng Q2 và Q5 lại thất bại. Số câu cố định không phản ánh độ dài và cấu trúc khác nhau giữa bảng, danh sách và đoạn văn.

### 4.3. Recursive chunking

Recursive Chunker thử separator từ cấu trúc lớn đến nhỏ và chỉ cắt cứng khi không còn lựa chọn. Nó giữ đoạn văn và bảng tốt hơn trong khi vẫn khống chế kích thước chunk.

- Size 250: recall tốt nhất trong nhóm nhỏ, 5/5 top-3, nhưng tạo 87 chunks và Q2 chỉ ở top-2.
- Size 400: Q2 lên top-1 nhưng Q4 tụt xuống top-5 vì cách ghép section tại ngưỡng này.
- Size 500: đạt 4/5 top-1 và 5/5 top-3 với 41 chunks; chỉ Q3 đứng top-2.
- Size 600: chỉ còn 32 chunks nhưng Q2 tụt xuống top-8. Chunk lớn đã ghép thêm nội dung không liên quan, làm embedding của evidence bị pha loãng.

Kết quả không thay đổi đơn điệu theo `chunk_size`: lớn hơn không luôn tốt hơn. Ranh giới separator và nội dung được ghép ở mỗi ngưỡng ảnh hưởng trực tiếp tới vector đại diện.

### 4.4. Heading-aware và heading-only

Heading-aware ưu tiên tách ở `##` và `###` trước đoạn văn. Cấu hình 450 đạt 4/5 top-3, nhưng Q1 không có một chunk chứa đủ cả quyền mượn và điều kiện gia hạn. Hai ý nằm ở các section gần nhau nhưng bị tách ra.

Heading-only thể hiện vấn đề rõ hơn:

- Q1: `Borrowing Privileges` chứa số lượng và thời hạn, còn `Renewal` chứa số lần gia hạn; không section nào đủ toàn bộ gold answer.
- Q2: heading giữ được cấu trúc section nhưng truy vấn dễ khớp với các section nói chung về số lượng mượn hơn dòng Course Reserve trong bảng.
- Q4: evidence ở top-4, ngoài top-3 mục tiêu.

Heading có ích để bảo toàn chủ đề nhưng không nên là quy tắc duy nhất. Một gold answer có thể cần hai section liền kề.

## 5. Phân tích lỗi theo câu hỏi

### Q1 — Quyền mượn của sinh viên đại học

Q1 cần ba dữ kiện nằm trong `Borrowing Privileges` và `Renewal`. Chunk quá nhỏ hoặc heading-only tách hai phần, khiến retrieval lấy đúng tài liệu nhưng context không đủ để trả lời hoàn chỉnh. Recursive 500 ghép được hai section vào `undergraduate-borrowing::chunk_0` và đưa evidence lên top-1 với score 0.6621.

### Q2 — Giới hạn Course Reserve

Q2 là failure case quan trọng nhất khi đánh giá chỉ bằng `doc_id`. Ở Recursive 600, top-1 mang `doc_id=circulation-policy`, nhưng chunk đó thuộc phần requesting và chỉ nói item Course Reserve không được request; nó không chứa giới hạn `1 item/user/time`. Evidence thật đứng top-8.

Điều này cho thấy “đúng tài liệu” không đồng nghĩa “đúng chunk”. Recursive 500 giữ nguyên dòng bảng chính sách và đưa evidence lên top-1, score 0.6869.

### Q3 — Ba mức phí quá hạn

Với Recursive 500 và chỉ lọc `audience=student`, top-1 là một chunk từ `undergraduate-borrowing` có các từ “fines”, “overdue materials” và “equipment”, score 0.6017. Nguồn biểu phí chính thức đứng top-2, score 0.5967. Khoảng cách chỉ 0.0050 nên cosine similarity không đủ để phân biệt nguồn có thẩm quyền.

Thêm `category=library-fees` loại các tài liệu không phải biểu phí trước khi xếp hạng. Evidence trở thành top-1 với score giữ nguyên 0.5967. Filter không làm embedding tốt hơn; nó làm candidate set chính xác hơn.

### Q4 — Thời gian giữ tài liệu

Fixed Size dễ cắt ranh giới giữa thời gian chuẩn bị, thông báo và thời gian giữ. Recursive 500 giữ câu “held for two days” cùng điều kiện hủy request, đưa evidence lên top-1 với score 0.7566.

### Q5 — Thanh toán thất bại

Q5 tương đối ổn định ở Recursive vì hai hành động cần thiết nằm trong cùng một đoạn ngắn. Recursive 500 trả về `fines-and-payment::chunk_4` ở top-1, score 0.7556. Sentence 5 thất bại theo tiêu chí evidence đầy đủ vì cách nhóm câu không giữ cả hai hành động trong một chunk top-10 phù hợp.

## 6. Thử nghiệm A/B với metadata filtering

| Query | Filter A | Thứ hạng evidence | Filter B | Thứ hạng evidence | Tác động |
|---|---|---:|---|---:|---|
| Q1 | `audience=student` | 1 | Giữ nguyên | 1 | Filter audience đã đủ |
| Q2 | Không filter | 1 | `category=circulation-policy` | 1 | Không đổi hạng, nhưng loại trang dịch vụ không có thẩm quyền |
| Q3 | `audience=student` | 2 | `audience=student`, `category=library-fees` | 1 | Cải thiện top-2 thành top-1 |
| Q4 | Không filter | 1 | Không cần thêm | 1 | Truy vấn đã đủ rõ |
| Q5 | Không filter | 1 | Không cần thêm | 1 | Truy vấn đã đủ rõ |

Metadata hữu ích nhất khi query có nhiều tài liệu gần nghĩa nhưng chỉ một loại nguồn nên cung cấp gold answer. Tuy nhiên, filter quá hẹp có thể làm mất recall nếu metadata sai hoặc corpus thiếu nhãn. Vì vậy filter chỉ được dùng khi query thể hiện rõ audience hoặc category.

## 7. Chiến lược cuối và kết quả chính thức

Chiến lược được chọn:

```python
chunker = RecursiveChunker(chunk_size=500)
```

Filter theo query:

```text
Q1: audience=student
Q2: category=circulation-policy
Q3: audience=student, category=library-fees
Q4: không filter
Q5: không filter
```

| Câu | Top-1 chunk | Score | Evidence đầy đủ? |
|---|---|---:|---|
| Q1 | `undergraduate-borrowing::chunk_0` | 0.6621 | Có |
| Q2 | `circulation-policy::chunk_2` | 0.6869 | Có |
| Q3 | `financial-regulations-library-fees::chunk_0` | 0.5967 | Có |
| Q4 | `circulation-policy::chunk_10` | 0.7566 | Có |
| Q5 | `fines-and-payment::chunk_4` | 0.7556 | Có |

Kết quả cuối: **41 chunks, 5/5 evidence ở top-1 và 5/5 ở top-3**.

## 8. Kết luận

`RecursiveChunker(chunk_size=500)` kết hợp metadata pre-filter theo từng query là phương án tốt nhất trong các cấu hình đã thử. Nó cân bằng ba yếu tố:

1. Giữ đủ ngữ cảnh cho gold answer.
2. Không tạo quá nhiều chunk như size 250.
3. Cho phép metadata loại các tài liệu gần nghĩa nhưng không có thẩm quyền.

Bài học chính là retrieval không nên được đánh giá chỉ bằng score hoặc `doc_id`. Cần kiểm tra đúng nội dung chunk, nguồn có thẩm quyền và khả năng context hỗ trợ đầy đủ gold answer. Trong repository này `demo_llm` chỉ là LLM giả lập, nên phân tích tập trung vào việc context top-k có đủ căn cứ để tạo câu trả lời đúng, không tuyên bố đã đo chất lượng của một generative LLM thật.
