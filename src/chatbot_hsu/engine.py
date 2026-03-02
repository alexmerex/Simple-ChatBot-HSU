import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import KDTree

from .config import ChatbotConfig
from .text_utils import normalize_text

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CandidateScore:
    index: int
    answer: str
    similarity: float
    lexical_score: float
    final_score: float


@dataclass(slots=True)
class RetrievalResult:
    answer: str
    similarity: float
    index: int
    candidates: list[CandidateScore]
    used_fallback: bool = False


class ChatbotEngine:
    def __init__(self, config: ChatbotConfig):
        self.config = config
        self.knowledge_path: Path = config.knowledge_file
        self._knowledge_mtime: float | None = None

        self.raw_data: list[str] = []
        self.normalized_data: list[str] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.tree: KDTree | None = None

        self._build_index()

    def _load_knowledge(self) -> list[str]:
        if not self.knowledge_path.exists():
            raise FileNotFoundError(
                f"Missing required file: {self.knowledge_path}. "
                "Please create it and add at least one knowledge line."
            )

        with self.knowledge_path.open("r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]

        if not lines:
            raise ValueError(
                f"{self.knowledge_path} is empty. "
                "Please add at least one non-empty knowledge line."
            )

        processed_lines = [normalize_text(line, fold_accents=True) for line in lines]
        if not any(processed_lines):
            raise ValueError(
                f"{self.knowledge_path} does not contain usable text after preprocessing."
            )

        return lines

    def _build_index(self) -> None:
        self.raw_data = self._load_knowledge()
        self.normalized_data = [normalize_text(line, fold_accents=True) for line in self.raw_data]

        self.vectorizer = TfidfVectorizer(
            max_df=self.config.vector_max_df,
            min_df=self.config.vector_min_df,
            max_features=self.config.vector_max_features,
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(self.normalized_data)
        self.tree = KDTree(self.matrix.toarray(), leaf_size=10)

        self._knowledge_mtime = self.knowledge_path.stat().st_mtime
        logger.info(
            "Knowledge index built: lines=%d vocab=%d",
            len(self.raw_data),
            len(self.vectorizer.vocabulary_),
        )

    def force_reload(self) -> None:
        logger.info("Manual reload requested.")
        self._build_index()

    def set_retrieval_k(self, value: int) -> int:
        safe_value = max(1, int(value))
        self.config.retrieval_k = safe_value
        return self.config.retrieval_k

    def config_snapshot(self) -> dict:
        return {
            "mode": self.config.mode,
            "knowledge_file": str(self.config.knowledge_file),
            "retrieval_k": self.config.retrieval_k,
            "explanation_top_k": self.config.explanation_top_k,
            "similarity_threshold": self.config.similarity_threshold,
            "show_explanations": self.config.show_explanations,
            "hot_reload": self.config.hot_reload,
            "debug": self.config.debug,
            "log_level": self.config.log_level,
        }

    def _reload_if_needed(self) -> None:
        if not self.config.hot_reload:
            return

        try:
            current_mtime = self.knowledge_path.stat().st_mtime
        except FileNotFoundError:
            return

        if self._knowledge_mtime is None or current_mtime > self._knowledge_mtime:
            logger.info("Detected knowledge.txt change. Rebuilding index.")
            self._build_index()

    @staticmethod
    def _similarity(distance: float) -> float:
        return 1.0 / (1.0 + distance)

    def _score_candidate(self, query_norm: str, idx: int) -> CandidateScore:
        query_tokens = set(query_norm.split())
        candidate = self.normalized_data[idx]
        candidate_tokens = set(candidate.split())

        overlap = len(query_tokens & candidate_tokens)
        union = len(query_tokens | candidate_tokens) or 1
        lexical_score = overlap / union

        query_vector = self.vectorizer.transform([query_norm]).toarray()
        cand_vector = self.matrix[idx].toarray()
        distance = np.linalg.norm(query_vector - cand_vector)
        similarity = self._similarity(float(distance))

        final_score = 0.75 * similarity + 0.25 * lexical_score
        return CandidateScore(
            index=idx,
            answer=self.raw_data[idx],
            similarity=similarity,
            lexical_score=lexical_score,
            final_score=final_score,
        )

    def ask(self, query: str) -> RetrievalResult:
        self._reload_if_needed()

        query_norm = normalize_text(query, fold_accents=True)
        if not query_norm:
            return RetrievalResult(
                answer="Please enter a meaningful question.",
                similarity=0.0,
                index=-1,
                candidates=[],
                used_fallback=True,
            )

        query_vector = self.vectorizer.transform([query_norm]).toarray()
        k = min(self.config.retrieval_k, len(self.raw_data))
        _, indices = self.tree.query(query_vector, k=k)

        scored = [self._score_candidate(query_norm, int(idx)) for idx in indices[0]]
        scored.sort(key=lambda c: c.final_score, reverse=True)

        best = scored[0]
        top_explanations = scored[: self.config.explanation_top_k]

        if best.similarity < self.config.similarity_threshold:
            return RetrievalResult(
                answer=self.config.fallback_message,
                similarity=best.similarity,
                index=best.index,
                candidates=top_explanations,
                used_fallback=True,
            )

        return RetrievalResult(
            answer=best.answer,
            similarity=best.similarity,
            index=best.index,
            candidates=top_explanations,
            used_fallback=False,
        )
