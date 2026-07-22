from pathlib import Path

import pytest

from chatbot_hsu.config import ChatbotConfig
from chatbot_hsu.engine import ChatbotEngine


@pytest.fixture(scope="module")
def knowledge_engine() -> ChatbotEngine:
    knowledge_file = Path(__file__).parents[1] / "knowledge.txt"
    return ChatbotEngine(ChatbotConfig(knowledge_file=knowledge_file, web_enabled=False))


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Đại học Hoa Sen có bao nhiêu ngành năm 2026?", "33 ngành"),
        ("Có những phương thức xét tuyển nào?", "5 phương thức xét tuyển"),
        ("Địa chỉ cơ sở Thành Thái ở đâu?", "7/1 Thành Thái"),
        ("HSU có ngành an ninh mạng không?", "An ninh mạng"),
    ],
)
def test_curated_knowledge_answers_common_questions(
    knowledge_engine: ChatbotEngine, query: str, expected: str
):
    result = knowledge_engine.ask(query)

    assert result.used_fallback is False
    assert expected in result.answer
    assert result.citation_urls
    assert result.citation_urls[0].startswith("https://www.hoasen.edu.vn/")


def test_unknown_time_sensitive_fact_uses_fallback(knowledge_engine: ChatbotEngine):
    result = knowledge_engine.ask("Hiệu trưởng HSU hiện nay là ai?")

    assert result.used_fallback is True
