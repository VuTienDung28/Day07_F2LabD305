# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** F2

**Thành viên:** Vũ Tiến Dũng, Chu Nguyễn Tuấn Anh, Đào Thị Trang, Lê Minh Ngọc, Nguyễn Đức Chung

**Ngày:** 03/08/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề cố định theo lớp K3:** dịch vụ và quy định đại học.

Nhóm tập trung vào **dịch vụ và quy định thư viện VinUniversity**, gồm quyền mượn tài liệu, Course Reserve, yêu cầu giữ tài liệu, tiền phạt và thanh toán trực tuyến. Các tài liệu đều cùng một miền chủ đề nên có các câu hỏi gần nghĩa để đánh giá khả năng chunking, phân biệt nguồn và lọc metadata.

Corpus chính thức là `k3_library.zip`, gồm 7 tài liệu Markdown, `sources.csv` và `benchmark.csv`. Bộ benchmark có 5 câu hỏi chung cho tất cả thành viên.

### Danh sách tài liệu (Data Inventory)

Số ký tự dưới đây là số ký tự của toàn bộ file Markdown, bao gồm YAML front matter.

| #   | Tên tài liệu                                                                                 | Nguồn (Source URL)                                                                            | Ngày lấy / Phiên bản                                              | Số ký tự | Metadata đã gán                                                                                    |
| --- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | -------: | -------------------------------------------------------------------------------------------------- |
| 1   | `undergraduate-borrowing.md` — Undergraduate Student Borrowing Policy                        | `https://library.vinuni.edu.vn/services/borrow-and-request/undergraduate-and-staff/`          | 03/08/2026 / không nêu phiên bản                                  |    2.250 | `audience=student`, `category=borrowing-policy`                                                    |
| 2   | `circulation-policy.md` — Library Circulation Policy                                         | `https://policy.vinuni.edu.vn/all-policies/library-policies-for-users/`                       | 03/08/2026 / `POL-LLR-001-V4.0`, hiệu lực 09/07/2025              |    4.615 | `audience=all`, `category=circulation-policy`                                                      |
| 3   | `graduate-faculty-borrowing.md` — Graduate Student, Faculty, and Instructor Library Services | `https://library.vinuni.edu.vn/services/borrow-and-request/graduate-faculty-and-instructors/` | 03/08/2026 / không nêu phiên bản                                  |    2.132 | `audience=all`, `audience_detail=graduate-student-faculty-instructor`, `category=borrowing-policy` |
| 4   | `borrowing-faq.md` — Library Borrowing FAQ                                                   | `https://library.vinuni.edu.vn/faq/`                                                          | 03/08/2026 / không nêu phiên bản                                  |    3.539 | `audience=all`, `category=borrowing-faq`                                                           |
| 5   | `course-reserve.md` — Course Reserve Policy                                                  | `https://library.vinuni.edu.vn/course-reserve/`                                               | 03/08/2026 / không nêu phiên bản                                  |    1.227 | `audience=student`, `category=course-reserve`                                                      |
| 6   | `fines-and-payment.md` — Library Fines and Online Payment Guidelines                         | `https://library.vinuni.edu.vn/online-payment-guidelines/`                                    | 03/08/2026 / không nêu phiên bản                                  |    2.122 | `audience=all`, `category=fines-and-payment`                                                       |
| 7   | `financial-regulations-library-fees.md` — Financial Regulations and Tariff — Library Fees    | `https://policy.vinuni.edu.vn/all-policies/financial-regulations-and-tariff-for-student-2/`   | 03/08/2026 / `VUNI_TS03_Student`, ban hành và hiệu lực 08/10/2025 |    1.548 | `audience=student`, `category=library-fees`                                                        |

Tổng kích thước corpus là **17.433 ký tự**. `sources.csv` có đúng một dòng cho mỗi trong 7 tài liệu, với `source_url`, `retrieved_at`, phiên bản hoặc ngày hiệu lực nếu nguồn công bố, `reference_number` khi có và quyền sử dụng `public-page-manual-collection`.

### Danh sách kiểm tra quản trị dữ liệu (Data governance checklist)

- [x] Corpus chỉ chứa các trang công khai của VinUniversity, không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at` và `document_version` trong YAML metadata; nguồn không công bố phiên bản được ghi rõ `not-stated`.
- [x] `sources.csv` ánh xạ một-một tới 7 file Markdown.
- [x] `benchmark.csv` nằm ngoài nội dung tài liệu được ingest và có đúng 5 câu hỏi, gold answer, file bằng chứng và section.
- [x] Các thông tin mâu thuẫn được ưu tiên theo nguồn có thẩm quyền: policy có phiên bản được ưu tiên hơn trang dịch vụ hoặc FAQ không phiên bản.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata                       | Kiểu        | Ví dụ giá trị                        | Tại sao hữu ích cho truy xuất (retrieval)?                             |
| ------------------------------------- | ----------- | ------------------------------------ | ---------------------------------------------------------------------- |
| `doc_id`                              | string      | `circulation-policy`                 | Xác định tài liệu gốc và truy vết chunk về nguồn.                      |
| `source_url`                          | string      | URL trang chính sách công khai       | Kiểm tra nguồn và độ tin cậy của bằng chứng.                           |
| `retrieved_at`                        | date string | `2026-08-03`                         | Biết thời điểm thu thập, quan trọng với quy định có thể thay đổi.      |
| `document_version` / `effective_date` | string      | `4.0`, `2025-07-09`                  | Ưu tiên chính sách có phiên bản hoặc ngày hiệu lực rõ ràng.            |
| `audience`                            | string      | `student`, `all`                     | Lọc tài liệu theo đối tượng trong câu hỏi.                             |
| `category`                            | string      | `circulation-policy`, `library-fees` | Loại các nguồn gần nghĩa nhưng không đúng loại chính sách cần trả lời. |
| `department`                          | string      | `library`, `finance`                 | Hỗ trợ phân biệt nội dung thư viện và biểu phí tài chính.              |
| `reference_number`                    | string/null | `POL-LLR-001-V4.0`                   | Tăng khả năng nhận diện nguồn chính sách có mã hiệu.                   |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

### Phân tích đường cơ sở (Baseline Analysis)

Nhóm chạy trực tiếp `ChunkingStrategyComparator().compare(..., chunk_size=500)` trên ba tài liệu đại diện. Comparator dùng `FixedSizeChunker(500, overlap=0)`, `SentenceChunker(max_sentences_per_chunk=3)` và `RecursiveChunker(chunk_size=500)` với separator mặc định. Độ dài trung bình tính trên phần nội dung sau khi tách metadata.

| Tài liệu                                | Chiến lược            | Số lượng Chunk | Độ dài trung bình | Giữ được ngữ cảnh không?                                                      |
| --------------------------------------- | --------------------- | -------------: | ----------------: | ----------------------------------------------------------------------------- |
| `undergraduate-borrowing.md`            | Fixed 500 / overlap 0 |              4 |            455,50 | Giữ độ dài ổn định nhưng có thể cắt giữa các section.                         |
| `undergraduate-borrowing.md`            | Sentence, 3 câu/chunk |              7 |            258,29 | Giữ câu hoàn chỉnh nhưng có thể tách quyền mượn và gia hạn.                   |
| `undergraduate-borrowing.md`            | Recursive 500         |              5 |            362,80 | Giữ đoạn và ranh giới cấu trúc tốt hơn.                                       |
| `circulation-policy.md`                 | Fixed 500 / overlap 0 |              9 |            458,78 | Bảng và section có thể bị cắt theo vị trí ký tự.                              |
| `circulation-policy.md`                 | Sentence, 3 câu/chunk |             13 |            316,00 | Không luôn giữ được một dòng bảng cùng ngữ cảnh liên quan.                    |
| `circulation-policy.md`                 | Recursive 500         |             14 |            293,29 | Bảo toàn cấu trúc tốt hơn nhưng tạo nhiều chunk vì tài liệu có nhiều section. |
| `financial-regulations-library-fees.md` | Fixed 500 / overlap 0 |              3 |            336,00 | Đủ cho tài liệu ngắn nhưng phụ thuộc vị trí điểm cắt.                         |
| `financial-regulations-library-fees.md` | Sentence, 3 câu/chunk |              3 |            334,33 | Hoạt động ổn với tài liệu ngắn, ít phù hợp hơn với bảng/list dài.             |
| `financial-regulations-library-fees.md` | Recursive 500         |              3 |            334,67 | Giữ được nhóm các mức phí trong cùng ngữ cảnh.                                |

Fixed-size đơn giản và kiểm soát được số chunk, nhưng overlap làm tăng dữ liệu trùng lặp và không hiểu ranh giới ngữ nghĩa. Sentence chunking giữ câu trọn vẹn nhưng không xử lý hoàn hảo bảng Markdown và các bullet list. Recursive chunking phù hợp hơn với corpus này vì thử tách từ đoạn lớn đến câu/từ, chỉ cắt cứng khi không còn separator phù hợp.

### Chiến lược của từng thành viên

#### Thành viên 1 — Lê Minh Ngọc

- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=100)`.
- **Mô tả & lý do chọn:** Fixed-size tạo chunk đều, còn overlap 100 giữ lại ngữ cảnh ở biên section và câu. Cấu hình có 38 chunk, ít hơn các cấu hình recursive nhỏ trong thử nghiệm của cá nhân, nhưng vẫn đạt kết quả self-reported `AnswerHit@1=3/5`, `AnswerHit@3=4/5`, `MRR@5=0.700`.
- **Kết quả rerun strict:** 38 chunk, trung bình 459,61 ký tự; 3/5 evidence ở top-1 và 4/5 ở top-3.
- **Điểm mạnh:** đơn giản, độ dài ổn định; overlap giúp Q4 có full evidence ở top-2 và Q5 ở top-1.
- **Điểm yếu:** Q2 có full evidence nhưng chỉ ở top-7; overlap không bảo đảm chunk chính sách đúng được xếp hạng cao.

#### Thành viên 2 — Nguyễn Đức Chung

- **Loại chiến lược:** `FixedSizeChunker(chunk_size=500, overlap=50)`.
- **Mô tả & lý do chọn:** Overlap 50 là mức cân bằng giữa giữ ngữ cảnh và tránh nhân bản quá nhiều dữ liệu. Chiến lược dùng 34 chunk và thành viên báo cáo 4/5 câu có evidence đầy đủ trong top-3; tác tử được dùng là hàm extractive cục bộ, không phải generative LLM bên ngoài.
- **Kết quả rerun strict:** 34 chunk, trung bình 462,21 ký tự; 3/5 evidence ở top-1 và 4/5 ở top-3.
- **Điểm mạnh:** ít chunk nhất trong hai cấu hình Fixed được so sánh; Q1, Q3 và Q5 lên top-1, Q4 nằm ở top-3.
- **Điểm yếu:** Q2 có full evidence nhưng chỉ ở top-5, ngoài mục tiêu top-3, do bị các chunk gần nghĩa xếp trên.

#### Thành viên 3 — Vũ Tiến Dũng

- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)` với separator tùy chỉnh:
  `['\\n## ', '\\n### ', '\\n\\n', '\\n', '. ', ' ', '']`.
- **Mô tả & lý do chọn:** Separator ưu tiên heading `##` và `###` trước đoạn văn, dòng, câu rồi từ, nhằm giữ cấu trúc policy và heading. Thành viên dùng filter `audience=student` cho Q1 và Q3, đồng thời dùng extractive local LLM function; báo cáo không tuyên bố đã đánh giá generative LLM thật.
- **Kết quả rerun strict:** 47 chunk, trung bình 302,13 ký tự; 3/5 evidence ở top-1 và 3/5 ở top-3. Con số này khác 50 chunk tự báo cáo do rerun dùng implementation chung của working tree để so sánh đồng nhất.
- **Điểm mạnh:** Q2, Q3 và Q5 có evidence top-1; cấu trúc heading giúp truy vết section rõ.
- **Điểm yếu:** Q1 bị tách phần gia hạn khỏi quyền mượn; Q4 có evidence nhưng xuống top-5. Ưu tiên heading quá sớm làm chunk nhỏ hơn đáng kể so với Recursive mặc định.

#### Thành viên 4 — Đào Thị Trang

- **Loại chiến lược:** `RecursiveChunker(chunk_size=350)` với separator mặc định.
- **Mô tả & lý do chọn:** Kích thước 350 giữ đoạn vừa đủ ngắn để embedding tập trung vào một ý, đồng thời recursive splitting ưu tiên ranh giới đoạn/câu trước khi cắt cứng. Báo cáo cá nhân sử dụng cùng model multilingual MiniLM và ghi nhận 5/5 top-3, với điểm tự đánh giá retrieval 10/10.
- **Kết quả rerun strict:** 59 chunk, trung bình 241,83 ký tự; 3/5 evidence ở top-1 và 3/5 ở top-3.
- **Điểm mạnh:** Q3, Q4 và Q5 có evidence top-1; chunk nhỏ giúp các ý riêng biệt ít bị pha loãng.
- **Điểm yếu:** số chunk lớn hơn và Q1 vẫn bị tách hai phần bắt buộc. Nhãn “relevant” trong báo cáo cá nhân dùng tiêu chí ít chặt hơn tiêu chí full-evidence của bảng rerun này, nên nhóm dùng kết quả rerun để so sánh công bằng.

#### Thành viên 5 — Chu Nguyễn Tuấn Anh

- **Loại chiến lược:** `RecursiveChunker(chunk_size=500)` với separator mặc định `['\\n\\n', '\\n', '. ', ' ', '']` và pre-filter metadata theo từng query.
- **Mô tả & lý do chọn:** Recursive 500 giữ được đoạn, bảng và các section liền kề mà không tạo quá nhiều chunk. Filter chỉ được dùng khi câu hỏi cho biết rõ audience hoặc loại chính sách: Q1 `audience=student`; Q2 `category=circulation-policy`; Q3 `audience=student, category=library-fees`; Q4 và Q5 không filter.
- **Kết quả rerun strict:** 41 chunk, trung bình 348,78 ký tự; 5/5 evidence ở top-1 và 5/5 ở top-3.
- **Điểm mạnh:** giữ đủ evidence trong chunk và loại được nguồn gần nghĩa nhưng không có thẩm quyền; Q3 cải thiện từ top-2 lên top-1 khi thêm `category=library-fees`.
- **Điểm yếu:** kết quả phụ thuộc metadata đúng; filter quá hẹp có thể làm giảm recall nếu nhãn nguồn sai hoặc corpus thiếu tài liệu.

### So Sánh Giữa Các Thành Viên

Bảng dưới dùng cùng một rerun trên corpus hiện tại và cùng tiêu chí strict: một chunk chỉ được tính là evidence khi chứa **toàn bộ dữ kiện cần thiết của gold answer**. Điểm `/10` là điểm tự đánh giá retrieval trong báo cáo cá nhân, còn các cột `strict` là phép so sánh lại của nhóm.

| Thành viên          | Chiến lược                   | Chunk | Strict top-1 | Strict top-3 | Điểm retrieval tự đánh giá | Điểm mạnh                                      | Điểm yếu                                  |
| ------------------- | ---------------------------- | ----: | -----------: | -----------: | -------------------------: | ---------------------------------------------- | ----------------------------------------- |
| Lê Minh Ngọc        | Fixed 500 / overlap 100      |    38 |          3/5 |          4/5 |                       8/10 | Ít chunk, overlap giữ ngữ cảnh biên            | Q2 chỉ có full evidence ở top-7           |
| Nguyễn Đức Chung    | Fixed 500 / overlap 50       |    34 |          3/5 |          4/5 |                       8/10 | Ít chunk nhất, Q1/Q3/Q5 top-1                  | Q2 chỉ có full evidence ở top-5           |
| Vũ Tiến Dũng        | Recursive 500, heading-aware |    47 |          3/5 |          3/5 |                       8/10 | Giữ heading, Q2/Q3/Q5 top-1                    | Q1 tách renewal, Q4 xuống top-5           |
| Đào Thị Trang       | Recursive 350                |    59 |          3/5 |          3/5 |                      10/10 | Chunk tập trung, Q3/Q4/Q5 top-1                | Q1 không có full evidence, Q2 xuống top-5 |
| Chu Nguyễn Tuấn Anh | Recursive 500 + query filter |    41 |      **5/5** |      **5/5** |                      10/10 | Cân bằng kích thước và lọc nguồn có thẩm quyền | Phụ thuộc chất lượng metadata             |

**Chiến lược được chọn cho nhóm:** `RecursiveChunker(chunk_size=500)` kết hợp metadata pre-filter theo query. Đây là chiến lược duy nhất trong rerun strict đưa đủ evidence của cả 5 câu lên top-1, trong khi chỉ tạo 41 chunk — ít hơn Recursive 350 và heading-aware Recursive 500. Kết quả cũng cho thấy overlap hoặc chunk nhỏ có thể cải thiện recall cục bộ, nhưng không tự giải quyết được trường hợp gold answer cần dữ kiện từ hai section hoặc cần phân biệt nguồn có thẩm quyền.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

Năm câu dưới đây được lấy nguyên văn từ `data/k3_library/benchmark.csv`. Bằng chứng phải được kiểm tra theo nội dung chunk, không chỉ theo `doc_id`.

| #   | Câu hỏi (Query)                                                                                         | Câu trả lời chuẩn (Gold Answer)                                                                                                                                                             | Chunk/section chứa thông tin                                                  |
| --- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1   | How many items may an undergraduate student borrow, for how long, and how many renewals are allowed?    | An undergraduate student may borrow 3 items for 2 weeks and renew once.                                                                                                                     | `undergraduate-borrowing.md`, `Borrowing Privileges` + `Renewal`              |
| 2   | How many Course Reserve books may one user borrow at a time?                                            | The versioned Library Access & Services Policy allows 1 Course Reserve item per user at a time; Course Reserve use is limited to 2 hours.                                                   | `circulation-policy.md`, `Circulation Regulations for Library Materials`      |
| 3   | What is the overdue fine for normal material, Course Reserve material, and equipment?                   | Normal material costs 10,000 VND per overdue document per day; Course Reserve material costs 10,000 VND per overdue document per hour; equipment costs 10,000 VND per overdue item per day. | `financial-regulations-library-fees.md`, `Overdue Borrowing and Recall Fines` |
| 4   | How long is a requested library item held after it is ready for collection?                             | A requested item is held for 2 days; if it is not collected within that period, the request is canceled.                                                                                    | `circulation-policy.md`, `Requesting Books or CDs/DVDs`                       |
| 5   | What should a user do when an online library payment fails after accurate card information was entered? | The user should not submit another payment and should contact library staff at the circulation desk for assistance.                                                                         | `fines-and-payment.md`, `Unsuccessful Transactions`                           |

### Tổng hợp chất lượng truy xuất của nhóm

Bảng này chọn kết quả của chiến lược cuối cùng `Recursive 500 + filter` vì nó đạt kết quả strict tốt nhất. Các score là cosine similarity của chunk top-1; kết quả agent được đối chiếu với gold answer trong báo cáo cá nhân của Chu Nguyễn Tuấn Anh. `demo_llm` mặc định trong repository chỉ là hàm preview, nên nhóm không tuyên bố đây là đánh giá của một generative LLM thật.

| #   | Câu hỏi                             | Chunk top-1 của chiến lược nhóm               |  Score | Có chunk liên quan trong top-3? | Câu trả lời kiểm tra                                                                      |
| --- | ----------------------------------- | --------------------------------------------- | -----: | ------------------------------- | ----------------------------------------------------------------------------------------- |
| 1   | Quyền mượn của sinh viên đại học    | `undergraduate-borrowing::chunk_0`            | 0,6621 | Có, evidence top-1              | 3 tài liệu trong 2 tuần, gia hạn 1 lần.                                                   |
| 2   | Giới hạn Course Reserve             | `circulation-policy::chunk_2`                 | 0,6869 | Có, evidence top-1              | 1 tài liệu/người/lần, sử dụng tối đa 2 giờ.                                               |
| 3   | Ba mức phí quá hạn                  | `financial-regulations-library-fees::chunk_0` | 0,5967 | Có, evidence top-1              | Tài liệu thường 10.000 VND/ngày; Course Reserve 10.000 VND/giờ; thiết bị 10.000 VND/ngày. |
| 4   | Thời gian giữ tài liệu được yêu cầu | `circulation-policy::chunk_10`                | 0,7566 | Có, evidence top-1              | Giữ 2 ngày, sau đó hủy yêu cầu nếu không nhận.                                            |
| 5   | Thanh toán trực tuyến thất bại      | `fines-and-payment::chunk_4`                  | 0,7556 | Có, evidence top-1              | Không gửi lại thanh toán; liên hệ nhân viên tại quầy lưu hành.                            |

Kết quả strict của chiến lược nhóm là **5/5 câu có full evidence ở top-1 và 5/5 ở top-3**. Theo rubric, đây là cơ sở để tự đánh giá phần retrieval ở mức **10/10**, với điều kiện câu trả lời được kiểm tra đúng theo gold answer thay vì chỉ kiểm tra tài liệu chứa chunk.

### So sánh evidence theo từng câu

| #   | Chiến lược tốt nhất cho câu này         | Kết quả strict của các chiến lược                                                                                | Nhận xét                                                                                                                     |
| --- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1   | Recursive 500 + filter                  | Ngọc top-1; Chung top-1; Dũng không có full evidence top-10; Trang không có full evidence top-10; Tuấn Anh top-1 | Dữ kiện quyền mượn và renewal nằm ở hai section; chunk phải đủ rộng hoặc gộp được section liền kề.                           |
| 2   | Recursive 500 + filter; Dũng cũng top-1 | Ngọc top-7; Chung top-5; Dũng top-1; Trang top-5; Tuấn Anh top-1                                                 | Phải có đồng thời giới hạn 1 item và thời hạn 2 giờ. Đúng `doc_id` nhưng sai section không được tính.                        |
| 3   | Recursive 500 + filter                  | Ngọc top-1; Chung top-1; Dũng top-1; Trang top-1; Tuấn Anh top-1                                                 | Filter `category=library-fees` loại chunk gần nghĩa từ FAQ/borrowing và chọn nguồn biểu phí có phiên bản.                    |
| 4   | Recursive 500 + filter                  | Ngọc top-2; Chung top-3; Dũng top-5; Trang top-1; Tuấn Anh top-1                                                 | Recursive mặc định giữ thời gian giữ và điều kiện hủy request trong cùng chunk; heading-aware quá sớm làm evidence tụt hạng. |
| 5   | Recursive 500 + filter                  | Tất cả năm chiến lược top-1                                                                                      | Hai hành động “không gửi lại” và “liên hệ quầy” cùng xuất hiện trong chunk top-1 của mọi cấu hình rerun.                     |

### Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?

Có. Q3 là ví dụ rõ nhất: khi chỉ dùng `audience=student`, một chunk về undergraduate borrowing có các từ khóa gần nghĩa về fines/overdue/equipment đứng top-1, còn biểu phí chính thức đứng top-2; thêm `category=library-fees` đưa evidence lên top-1. Q1 dùng `audience=student` để giới hạn đối tượng, còn Q2 dùng `category=circulation-policy` để ưu tiên policy phiên bản 4.0 thay vì trang Course Reserve không có giới hạn một item. Filter là bước lọc ứng viên trước khi tính similarity, không làm embedding tốt hơn; hiệu quả của nó phụ thuộc vào metadata chính xác.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

Phần dưới là các insight nhóm đã chuẩn bị để trình bày. Repository không có biên bản hoặc log xác nhận một buổi demo đã diễn ra, nên nhóm không gắn thêm số liệu hay tuyên bố về người xem ngoài các kết quả chạy được.

**Những phân tích nhóm sẽ trình bày:**

1. **Đúng tài liệu chưa chắc đúng bằng chứng:** Q2 cho thấy một chunk có cùng `doc_id=circulation-policy` vẫn có thể thuộc section Requesting và không chứa giới hạn Course Reserve. Vì vậy cần kiểm tra nội dung chunk và section, không chỉ ID tài liệu.
2. **Chunk size không có quan hệ đơn điệu với chất lượng:** Recursive 250 đạt recall top-3 tốt nhưng tạo 87 chunk; Recursive 600 giảm còn 32 chunk nhưng Q2 tụt xuống top-8 trong thử nghiệm cá nhân. Recursive 500 cân bằng tốt hơn với 41 chunk.
3. **Metadata bổ sung thẩm quyền cho cosine similarity:** Q3 có khoảng cách score rất nhỏ giữa chunk gần nghĩa và nguồn biểu phí. `category=library-fees` giúp chọn đúng nguồn chính sách hiện hành.

**Bài học rút ra khi so sánh trong nhóm:**

Cùng corpus và embedding model nhưng ranh giới chunk khác nhau làm thay đổi việc một gold answer có nằm trọn trong một chunk hay không. Fixed-size có ưu điểm đơn giản và ít chunk, nhưng overlap không bảo đảm giữ được các dữ kiện ở hai section; recursive giữ cấu trúc tốt hơn, còn metadata filter giải quyết một loại lỗi khác là nguồn gần nghĩa nhưng không có thẩm quyền.

Khi so sánh, nhóm phân biệt rõ hai loại kết quả: số liệu tự báo cáo trong từng `REPORT_CANHAN.md` và bảng rerun strict của nhóm. Bảng rerun dùng một tiêu chí chung là chunk phải chứa toàn bộ evidence của gold answer, vì một số báo cáo cá nhân dùng nhãn “relevant” rộng hơn hoặc chỉ kiểm tra một phần bằng chứng.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu?**

Nhóm sẽ tự động hóa bước kiểm tra schema và manifest trước khi ingest, bắt buộc mỗi benchmark row chỉ rõ evidence section và các facts cần có, đồng thời lưu thêm `authority_level` hoặc `is_versioned` trong metadata. Với corpus lớn hơn, nhóm sẽ thử chunking theo section có cơ chế gộp hai section liền kề khi gold answer cần nhiều dữ kiện, thay vì chỉ tăng overlap hoặc giảm chunk size.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá     |
| ---------------------------------------- | -------------------- |
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10              |
| Thiết kế chiến lược (Strategy Design)    | 15 / 15              |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10              |
| Thuyết trình (Demo)                      | Chưa tự đánh giá / 5 |
| **Tổng phần đã có bằng chứng**           | **35 / 40**          |

Phần demo chưa tự chấm vì repository hiện chỉ chứng minh nội dung đã được chuẩn bị, chưa xác nhận buổi thuyết trình đã thực hiện. Sau buổi demo, nhóm cập nhật điểm này theo phần trình bày thực tế.
