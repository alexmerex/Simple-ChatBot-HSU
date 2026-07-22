from pathlib import Path

from chatbot_hsu.config import ChatbotConfig
from chatbot_hsu.engine import ChatbotEngine
from chatbot_hsu.faiss_store import FaissWebStore
from chatbot_hsu.web_crawler import CrawledPage, _is_allowed_url, _normalize_url


def _page() -> CrawledPage:
    return CrawledPage(
        url="https://www.hoasen.edu.vn/tuyen-sinh",
        title="Tuyển sinh",
        text="Đại học Hoa Sen công bố thông tin tuyển sinh năm mới.",
    )


def test_web_store_search_and_round_trip_preserves_original_text(tmp_path: Path):
    store = FaissWebStore()
    store.build([_page()])

    first_hit = store.search("thong tin tuyen sinh", top_k=1)[0]
    assert "Đại học Hoa Sen" in first_hit.chunk.text
    assert first_hit.score > 0

    store.save(tmp_path, meta={"config_hash": "test"})
    restored = FaissWebStore()
    assert restored.load(tmp_path) is True
    assert restored.search("tuyen sinh", top_k=1)[0].chunk.source_url == _page().url


def test_engine_returns_web_citation_when_web_hit_is_confident(tmp_path: Path):
    knowledge = tmp_path / "knowledge.txt"
    knowledge.write_text("Thông tin chung về trường.", encoding="utf-8")
    config = ChatbotConfig(knowledge_file=knowledge, web_enabled=False, similarity_threshold=0.1)
    engine = ChatbotEngine(config)
    engine.web_store = FaissWebStore()
    engine.web_store.build([_page()])
    engine.config.web_enabled = True

    result = engine.ask("tuyển sinh Hoa Sen")

    assert result.citation_urls == [_page().url]
    assert "Đại học Hoa Sen" in result.answer


def test_url_whitelist_rejects_lookalike_domains_and_non_http_urls():
    allowed = ("hoasen.edu.vn",)
    assert _is_allowed_url("https://tuyensinh.hoasen.edu.vn/path", allowed)
    assert not _is_allowed_url("https://hoasen.edu.vn.evil.example/path", allowed)
    assert not _is_allowed_url("ftp://hoasen.edu.vn/file", allowed)
    assert _normalize_url("HTTPS://WWW.HOASEN.EDU.VN#section").endswith("/")


def test_corrupt_web_cache_is_ignored(tmp_path: Path):
    store = FaissWebStore()
    store.build([_page()])
    store.save(tmp_path, meta={"config_hash": "test"})
    (tmp_path / "web_chunks.jsonl").write_text("not-json", encoding="utf-8")

    assert FaissWebStore().load(tmp_path) is False
