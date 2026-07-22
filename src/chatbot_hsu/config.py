import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _parse_csv_env(value: str, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value.strip():
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {value!r}.")


@dataclass(slots=True)
class ChatbotConfig:
    app_title: str = field(
        default_factory=lambda: os.getenv("CHATBOT_APP_TITLE", "ChatBot Đại Học Hoa Sen")
    )
    knowledge_file: Path = field(
        default_factory=lambda: Path(os.getenv("CHATBOT_KNOWLEDGE_FILE", "knowledge.txt"))
    )

    vector_max_df: float = field(
        default_factory=lambda: float(os.getenv("CHATBOT_VECTOR_MAX_DF", "0.95"))
    )
    vector_min_df: int = field(default_factory=lambda: int(os.getenv("CHATBOT_VECTOR_MIN_DF", "1")))
    vector_max_features: int = field(
        default_factory=lambda: int(os.getenv("CHATBOT_VECTOR_MAX_FEATURES", "3000"))
    )

    retrieval_k: int = field(default_factory=lambda: int(os.getenv("CHATBOT_RETRIEVAL_K", "5")))
    explanation_top_k: int = field(
        default_factory=lambda: int(os.getenv("CHATBOT_EXPLANATION_TOP_K", "3"))
    )
    similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("CHATBOT_SIMILARITY_THRESHOLD", "0.18"))
    )
    fallback_message: str = field(
        default_factory=lambda: os.getenv(
            "CHATBOT_FALLBACK_MESSAGE",
            "I don't know that yet. Please try rephrasing your question or update knowledge.txt.",
        )
    )

    mode: str = field(default_factory=lambda: os.getenv("CHATBOT_MODE", "gui"))
    show_explanations: bool = field(
        default_factory=lambda: _parse_bool_env("CHATBOT_SHOW_EXPLANATIONS", True)
    )
    hot_reload: bool = field(default_factory=lambda: _parse_bool_env("CHATBOT_HOT_RELOAD", True))

    history_export_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CHATBOT_HISTORY_EXPORT_DIR", "exports"))
    )
    history_keep_last_exports: int = field(
        default_factory=lambda: int(os.getenv("CHATBOT_HISTORY_KEEP_LAST_EXPORTS", "20"))
    )

    # Crawling is opt-in so startup and tests never depend on network availability.
    web_enabled: bool = field(default_factory=lambda: _parse_bool_env("CHATBOT_WEB_ENABLED", False))
    web_seed_urls: tuple[str, ...] = field(
        default_factory=lambda: _parse_csv_env(
            os.getenv("CHATBOT_WEB_SEED_URLS", "https://www.hoasen.edu.vn"),
            ("https://www.hoasen.edu.vn",),
        )
    )
    web_allowed_domains: tuple[str, ...] = field(
        default_factory=lambda: _parse_csv_env(
            os.getenv("CHATBOT_WEB_ALLOWED_DOMAINS", "hoasen.edu.vn"),
            ("hoasen.edu.vn",),
        )
    )
    web_max_pages: int = field(
        default_factory=lambda: int(os.getenv("CHATBOT_WEB_MAX_PAGES", "60"))
    )
    web_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("CHATBOT_WEB_TIMEOUT_SECONDS", "12"))
    )
    web_index_dir: Path = field(
        default_factory=lambda: Path(os.getenv("CHATBOT_WEB_INDEX_DIR", "web_index"))
    )
    web_top_k: int = field(default_factory=lambda: int(os.getenv("CHATBOT_WEB_TOP_K", "3")))

    debug: bool = field(default_factory=lambda: _parse_bool_env("CHATBOT_DEBUG", False))
    log_level: str = field(default_factory=lambda: os.getenv("CHATBOT_LOG_LEVEL", "INFO"))

    def __post_init__(self) -> None:
        self.mode = self.mode.strip().lower()
        if self.mode not in {"gui", "cli"}:
            raise ValueError("CHATBOT_MODE must be either 'gui' or 'cli'.")
        if self.retrieval_k < 1 or self.explanation_top_k < 1:
            raise ValueError("Retrieval and explanation top-k values must be at least 1.")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("CHATBOT_SIMILARITY_THRESHOLD must be between 0 and 1.")
        if self.vector_min_df < 1 or self.vector_max_features < 1:
            raise ValueError("Vectorizer limits must be positive.")
        if not 0.0 < self.vector_max_df <= 1.0:
            raise ValueError("CHATBOT_VECTOR_MAX_DF must be in the range (0, 1].")
        if self.history_keep_last_exports < 1:
            raise ValueError("CHATBOT_HISTORY_KEEP_LAST_EXPORTS must be at least 1.")
        if self.web_max_pages < 1 or self.web_timeout_seconds < 1 or self.web_top_k < 1:
            raise ValueError("Web limits and timeout must be at least 1.")

        self.web_allowed_domains = tuple(
            domain.strip().lower().lstrip(".")
            for domain in self.web_allowed_domains
            if domain.strip().lstrip(".")
        )
        if self.web_enabled and (not self.web_seed_urls or not self.web_allowed_domains):
            raise ValueError("Web retrieval requires seed URLs and allowed domains.")
