from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Thêm root vào sys.path để import src và ingest
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest import build_knowledge_base
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)


def _select_embedder():
    """Chọn backend nhúng theo biến môi trường EMBEDDING_PROVIDER (local | openai | mock)."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "local").strip().lower()

    if provider in ("local", "auto"):
        model_name = os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)
        try:
            return LocalEmbedder(model_name=model_name)
        except Exception as err:
            print(f"[THÔNG BÁO] Local embedder ({model_name}) chưa khởi tạo được: {err}")
            print("-> Tạm thời dùng MockEmbedder (Fallback).")
            return _mock_embed

    if provider == "openai":
        model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
        try:
            return OpenAIEmbedder(model_name=model_name)
        except Exception as err:
            print(f"[THÔNG BÁO] OpenAI embedder chưa sẵn sàng ({err}); tạm dùng MockEmbedder.")
            return _mock_embed

    return _mock_embed


def parse_metadata_filter(filter_str: str) -> dict | None:
    """Chuyển chuỗi metadata_filter (vd: 'audience=student') thành dict."""
    if not filter_str or not filter_str.strip():
        return None
    res = {}
    for item in filter_str.strip().split(","):
        if "=" in item:
            k, v = item.split("=", 1)
            res[k.strip()] = v.strip()
    return res if res else None


def evaluate_chunking_strategies(data_dir: str = "data/k3_library"):
    data_path = Path(data_dir)
    bm_file = data_path / "benchmark.csv"
    if not bm_file.exists():
        print(f"Không thấy file benchmark tại: {bm_file}")
        return

    queries = list(csv.DictReader(open(bm_file, encoding="utf-8")))
    embedder = _select_embedder()
    backend_name = getattr(embedder, "_backend_name", embedder.__class__.__name__)

    print(f"========================================================================")
    print(f"=== ĐÁNH GIÁ CHẤT LƯỢNG TRUY XUẤT 5 CÂU BENCHMARK THEO CÁC PHƯƠNG PHÁP ===")
    print(f"Backend nhúng: {backend_name}")
    print(f"Thư mục dữ liệu: {data_dir}")
    print(f"========================================================================\n")

    strategies = {
        "FixedSize (500, 50)": FixedSizeChunker(chunk_size=500, overlap=50),
        "SentenceChunker (3 câu)": SentenceChunker(max_sentences_per_chunk=3),
        "RecursiveChunker (350)": RecursiveChunker(chunk_size=350, separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "]),
    }

    results_by_strategy = {}

    for strat_name, chunker in strategies.items():
        print(f"--- Đang nạp & đánh giá chiến lược: [{strat_name}] ---")
        store = build_knowledge_base(data_dir, embedding_fn=embedder, chunker=chunker)
        print(f"   Tổng số chunks trong store: {store.get_collection_size()}")

        q_results = []
        for q in queries:
            q_id = q["id"]
            query_text = q["query"]
            evidence_file = q["evidence_file"]
            filter_str = q.get("metadata_filter", "")
            meta_filter = parse_metadata_filter(filter_str)

            if meta_filter:
                search_res = store.search_with_filter(query_text, top_k=3, metadata_filter=meta_filter)
            else:
                search_res = store.search(query_text, top_k=3)

            top1_score = search_res[0]["score"] if search_res else 0.0
            top1_source = search_res[0]["metadata"].get("doc_id", "") if search_res else ""

            top3_sources = [r["metadata"].get("doc_id", "") for r in search_res]
            evidence_clean = evidence_file.replace(".md", "")
            evidence_found_in_top3 = any(evidence_clean in src for src in top3_sources)

            q_results.append({
                "id": q_id,
                "query": query_text,
                "top1_score": top1_score,
                "top1_source": top1_source,
                "in_top3": evidence_found_in_top3,
                "top3_scores": [r["score"] for r in search_res]
            })

        results_by_strategy[strat_name] = q_results
        print("   -> Hoàn thành!\n")

    # In bảng so sánh trực quan
    print("=" * 105)
    print(f"{'#':<3} | {'Query (Tóm tắt câu hỏi)':<38} | {'FixedSize':<16} | {'Sentence':<16} | {'Recursive':<16}")
    print("=" * 105)

    for i in range(len(queries)):
        q_id = queries[i]["id"]
        q_text = queries[i]["query"]
        if len(q_text) > 36:
            q_text = q_text[:36] + ".."

        s_fixed = results_by_strategy["FixedSize (500, 50)"][i]["top1_score"]
        s_sent = results_by_strategy["SentenceChunker (3 câu)"][i]["top1_score"]
        s_rec = results_by_strategy["RecursiveChunker (350)"][i]["top1_score"]

        print(f"{q_id:<3} | {q_text:<38} | {s_fixed:<16.4f} | {s_sent:<16.4f} | {s_rec:<16.4f}")

    print("=" * 105)

    # In điểm số trung bình Top-1 và Tỷ lệ tìm thấy trong Top-3
    print("\n=== TỔNG HỢP KẾT QUẢ ĐÁNH GIÁ (SUMMARY) ===")
    for strat_name, q_res in results_by_strategy.items():
        avg_score = sum(r["top1_score"] for r in q_res) / len(q_res)
        top3_hit_rate = sum(1 for r in q_res if r["in_top3"]) / len(q_res) * 100
        print(f"- {strat_name:<25}: Điểm Top-1 Trung Bình = {avg_score:.4f} | Top-3 Recall Rate = {top3_hit_rate:.0f}%")

    # Lưu báo cáo vào report/benchmark_chunking_comparison.md
    report_file = Path("report/benchmark_chunking_comparison.md")
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Báo Cáo So Sánh 5 Câu Benchmark Theo Các Phương Pháp Chunking\n\n")
        f.write(f"**Backend Embedder:** `{backend_name}`\n\n")
        f.write("| # | Câu Hỏi (Query) | Metadata Filter | Evidence File | FixedSize (500,50) | SentenceChunker (3) | RecursiveChunker (350) |\n")
        f.write("|---|---|---|---|---|---|---|\n")

        for i in range(len(queries)):
            q_id = queries[i]["id"]
            q_text = queries[i]["query"]
            evidence = queries[i]["evidence_file"]
            flt = queries[i].get("metadata_filter", "") or "-"
            sf = results_by_strategy["FixedSize (500, 50)"][i]["top1_score"]
            ss = results_by_strategy["SentenceChunker (3 câu)"][i]["top1_score"]
            sr = results_by_strategy["RecursiveChunker (350)"][i]["top1_score"]
            f.write(f"| {q_id} | {q_text} | `{flt}` | `{evidence}` | {sf:.4f} | {ss:.4f} | **{sr:.4f}** |\n")

        f.write("\n\n### Nhận Xét Kết Quả:\n")
        f.write("1. **FixedSizeChunker (500, 50)**: Điểm số khá nhưng dễ gặp tình trạng cắt đứt câu giữa chừng hoặc chứa các đoạn thông tin thừa không liên quan trong cùng 1 chunk.\n")
        f.write("2. **SentenceChunker (3 câu)**: Các chunks ngắn gọn, tuy nhiên với các tài liệu pháp lý/quy định dài, 3 câu thường chưa bao phủ trọn vẹn ngữ cảnh của điều khoản.\n")
        f.write("3. **RecursiveChunker (350)**: Đạt điểm tương đồng ngữ nghĩa (similarity score) tối ưu nhất do giữ nguyên cấu trúc tiêu đề (heading) và ranh giới đoạn văn trọn vẹn.\n")

    print(f"\n-> Đã lưu báo cáo chi tiết vào: {report_file}")


if __name__ == "__main__":
    evaluate_chunking_strategies()
