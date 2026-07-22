from pathlib import Path
import time

from chatbot_hsu.config import ChatbotConfig
from chatbot_hsu.engine import ChatbotEngine


def _write_knowledge(tmp_path: Path, lines: list[str]) -> Path:
    file_path = tmp_path / "knowledge.txt"
    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path


def test_accent_insensitive_retrieval(tmp_path: Path):
    knowledge = _write_knowledge(
        tmp_path,
        [
            "Đại học Hoa Sen có nhiều chương trình quốc tế.",
            "Trường có nhiều câu lạc bộ sinh viên.",
        ],
    )

    config = ChatbotConfig(knowledge_file=knowledge, similarity_threshold=0.1)
    engine = ChatbotEngine(config)

    result = engine.ask("dai hoc hoa sen co chuong trinh quoc te khong")
    assert "quốc tế" in result.answer.lower()


def test_low_confidence_returns_fallback(tmp_path: Path):
    knowledge = _write_knowledge(
        tmp_path,
        [
            "Đại học Hoa Sen có nhiều chương trình quốc tế.",
            "Trường có nhiều câu lạc bộ sinh viên.",
        ],
    )

    config = ChatbotConfig(
        knowledge_file=knowledge,
        similarity_threshold=0.95,
        fallback_message="I don't know",
    )
    engine = ChatbotEngine(config)

    result = engine.ask("thời tiết hôm nay thế nào")
    assert result.answer == "I don't know"
    assert result.used_fallback is True


def test_unrelated_query_uses_fallback_with_default_threshold(tmp_path: Path):
    knowledge = _write_knowledge(tmp_path, ["Đại học Hoa Sen có chương trình quốc tế."])
    engine = ChatbotEngine(ChatbotConfig(knowledge_file=knowledge))

    result = engine.ask("dự báo thời tiết ngày mai")

    assert result.used_fallback is True
    assert result.similarity == 0.0


def test_local_knowledge_source_is_returned_as_citation(tmp_path: Path):
    source_url = "https://www.hoasen.edu.vn/tuyensinh/"
    knowledge = _write_knowledge(
        tmp_path,
        [f"Đại học Hoa Sen có năm phương thức xét tuyển năm 2026. || {source_url}"],
    )
    engine = ChatbotEngine(ChatbotConfig(knowledge_file=knowledge, similarity_threshold=0.1))

    result = engine.ask("phương thức xét tuyển 2026")

    assert result.answer == "Đại học Hoa Sen có năm phương thức xét tuyển năm 2026."
    assert result.citation_urls == [source_url]


def test_top_candidates_explanations(tmp_path: Path):
    knowledge = _write_knowledge(
        tmp_path,
        [
            "Đại học Hoa Sen có chương trình quốc tế.",
            "Hoa Sen có nhiều câu lạc bộ.",
            "Thư viện Hoa Sen mở cửa cả cuối tuần.",
            "Học phí thay đổi theo từng ngành học.",
        ],
    )

    config = ChatbotConfig(knowledge_file=knowledge, retrieval_k=4, explanation_top_k=3)
    engine = ChatbotEngine(config)

    result = engine.ask("chuong trinh quoc te hoa sen")
    assert len(result.candidates) == 3
    assert result.candidates[0].final_score >= result.candidates[1].final_score


def test_hot_reload_knowledge(tmp_path: Path):
    knowledge = _write_knowledge(tmp_path, ["Thông tin ban đầu về Hoa Sen."])

    config = ChatbotConfig(
        knowledge_file=knowledge,
        similarity_threshold=0.1,
        hot_reload=True,
    )
    engine = ChatbotEngine(config)

    first = engine.ask("thong tin ban dau")
    assert "ban đầu" in first.answer.lower()

    time.sleep(1.1)
    knowledge.write_text("Thông tin mới sau cập nhật nóng.", encoding="utf-8")

    second = engine.ask("cap nhat nong")
    assert "cập nhật nóng" in second.answer.lower()
