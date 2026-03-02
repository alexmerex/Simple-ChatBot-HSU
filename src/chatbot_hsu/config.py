import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class ChatbotConfig:
    app_title: str = os.getenv("CHATBOT_APP_TITLE", "ChatBot Đại Học Hoa Sen")
    knowledge_file: Path = Path(os.getenv("CHATBOT_KNOWLEDGE_FILE", "knowledge.txt"))

    vector_max_df: float = float(os.getenv("CHATBOT_VECTOR_MAX_DF", "0.95"))
    vector_min_df: int = int(os.getenv("CHATBOT_VECTOR_MIN_DF", "1"))
    vector_max_features: int = int(os.getenv("CHATBOT_VECTOR_MAX_FEATURES", "3000"))

    retrieval_k: int = int(os.getenv("CHATBOT_RETRIEVAL_K", "5"))
    explanation_top_k: int = int(os.getenv("CHATBOT_EXPLANATION_TOP_K", "3"))
    similarity_threshold: float = float(os.getenv("CHATBOT_SIMILARITY_THRESHOLD", "0.18"))
    fallback_message: str = os.getenv(
        "CHATBOT_FALLBACK_MESSAGE",
        "I don't know that yet. Please try rephrasing your question or update knowledge.txt.",
    )

    mode: str = os.getenv("CHATBOT_MODE", "gui")  # gui | cli
    show_explanations: bool = os.getenv("CHATBOT_SHOW_EXPLANATIONS", "true").lower() == "true"
    hot_reload: bool = os.getenv("CHATBOT_HOT_RELOAD", "true").lower() == "true"

    history_export_dir: Path = Path(os.getenv("CHATBOT_HISTORY_EXPORT_DIR", "exports"))
    history_keep_last_exports: int = int(os.getenv("CHATBOT_HISTORY_KEEP_LAST_EXPORTS", "20"))

    debug: bool = os.getenv("CHATBOT_DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("CHATBOT_LOG_LEVEL", "INFO")
