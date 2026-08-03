"""Run the five personal-report similarity pairs with the local embedder."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import LocalEmbedder, compute_similarity  # noqa: E402


PAIRS = [
    (
        "Sinh viên được mượn ba cuốn sách trong hai tuần.",
        "Người học có thể mượn 3 tài liệu trong 14 ngày.",
    ),
    (
        "Phí trả sách quá hạn được tính theo ngày.",
        "Hôm nay đội tuyển bóng đá thi đấu trận chung kết.",
    ),
    (
        "Người dùng không nên thanh toán lại khi giao dịch thất bại.",
        "Users should not submit another payment after a failed transaction.",
    ),
    (
        "Sách được giữ trong hai ngày để người dùng đến nhận.",
        "Thiết bị quá hạn bị phạt 10.000 đồng mỗi ngày.",
    ),
    (
        "Sinh viên được phép gia hạn sách một lần.",
        "Sinh viên không được phép gia hạn sách.",
    ),
]


def main() -> int:
    embedder = LocalEmbedder()
    print(f"Embedding: {embedder._backend_name}")
    for index, (sentence_a, sentence_b) in enumerate(PAIRS, start=1):
        score = compute_similarity(embedder(sentence_a), embedder(sentence_b))
        print(f"{index}: {score:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
