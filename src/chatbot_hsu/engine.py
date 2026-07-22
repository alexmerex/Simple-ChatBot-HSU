import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import ChatbotConfig
from .faiss_store import FaissWebStore
from .text_utils import normalize_text
from .web_crawler import crawl_website

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
    citation_urls: list[str] | None = None


class ChatbotEngine:
    def __init__(self, config: ChatbotConfig):
        self.config = config
        self.knowledge_path: Path = config.knowledge_file
        self._knowledge_mtime_ns: int | None = None

        self.raw_data: list[str] = []
        self.local_source_urls: list[str | None] = []
        self.normalized_data: list[str] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self.web_store: FaissWebStore | None = None

        self._build_index()
        if self.config.web_enabled:
            self._ensure_web_index(force_rebuild=False)

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
                f"{self.knowledge_path} is empty. Please add at least one non-empty knowledge line."
            )

        processed_lines = [normalize_text(line, fold_accents=True) for line in lines]
        if not any(processed_lines):
            raise ValueError(
                f"{self.knowledge_path} does not contain usable text after preprocessing."
            )

        return lines

    def _build_index(self) -> None:
        knowledge_lines = self._load_knowledge()
        parsed_lines = [self._parse_knowledge_line(line) for line in knowledge_lines]
        self.raw_data = [answer for answer, _ in parsed_lines]
        self.local_source_urls = [source_url for _, source_url in parsed_lines]
        self.normalized_data = [normalize_text(line, fold_accents=True) for line in self.raw_data]

        max_df = self.config.vector_max_df
        if (
            isinstance(max_df, float)
            and max_df * len(self.normalized_data) < self.config.vector_min_df
        ):
            max_df = 1.0

        self.vectorizer = TfidfVectorizer(
            max_df=max_df,
            min_df=self.config.vector_min_df,
            max_features=self.config.vector_max_features,
            ngram_range=(1, 2),
        )
        self.matrix = self.vectorizer.fit_transform(self.normalized_data)
        self._knowledge_mtime_ns = self.knowledge_path.stat().st_mtime_ns
        logger.info(
            "Knowledge index built: lines=%d vocab=%d",
            len(self.raw_data),
            len(self.vectorizer.vocabulary_),
        )

    @staticmethod
    def _parse_knowledge_line(line: str) -> tuple[str, str | None]:
        answer, separator, source_url = line.rpartition(" || ")
        if not separator:
            return line, None

        parsed_url = urlparse(source_url.strip())
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            return line, None
        return answer.strip(), source_url.strip()

    def _web_config_payload(self) -> dict:
        return {
            "allowed_domains": sorted(self.config.web_allowed_domains),
            "seed_urls": sorted(self.config.web_seed_urls),
            "max_pages": self.config.web_max_pages,
            "timeout_seconds": self.config.web_timeout_seconds,
            "web_top_k": self.config.web_top_k,
        }

    def _web_config_hash(self) -> str:
        payload_json = json.dumps(self._web_config_payload(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    def _web_cache_diff(self, meta: dict) -> list[str]:
        cached_config = meta.get("config") or {}
        current_config = self._web_config_payload()

        diffs: list[str] = []
        for key in sorted(current_config.keys()):
            cached_value = cached_config.get(key)
            current_value = current_config.get(key)
            if cached_value != current_value:
                diffs.append(f"{key}: cached={cached_value!r} -> current={current_value!r}")

        if not meta.get("config_hash"):
            diffs.append("config_hash: missing in cache meta")

        return diffs

    def _is_web_cache_valid(self, meta: dict) -> bool:
        cached_hash = meta.get("config_hash")
        if not cached_hash:
            return False
        return cached_hash == self._web_config_hash()

    def _crawl_and_build_web_index(self) -> None:
        logger.info(
            "Building web index from whitelisted domains: %s",
            self.config.web_allowed_domains,
        )
        pages = crawl_website(
            seed_urls=list(self.config.web_seed_urls),
            allowed_domains=self.config.web_allowed_domains,
            max_pages=self.config.web_max_pages,
            timeout_seconds=self.config.web_timeout_seconds,
        )

        if not pages:
            logger.warning("No web pages crawled. Web retrieval disabled for this run.")
            self.web_store = None
            return

        store = FaissWebStore()
        store.build(pages)
        meta = {
            "config": self._web_config_payload(),
            "config_hash": self._web_config_hash(),
        }
        store.save(self.config.web_index_dir, meta=meta)
        self.web_store = store
        logger.info("Web FAISS index ready with %d chunks.", len(store.chunks))

    def _ensure_web_index(self, force_rebuild: bool) -> None:
        store = FaissWebStore()
        if not force_rebuild and store.load(self.config.web_index_dir):
            meta = store.load_meta(self.config.web_index_dir)
            if self._is_web_cache_valid(meta):
                self.web_store = store
                logger.info("Loaded cached web index with %d chunks.", len(store.chunks))
                return

            diffs = self._web_cache_diff(meta)
            if diffs:
                logger.info(
                    "Cached web index invalidated. Changed fields:\n- %s",
                    "\n- ".join(diffs),
                )
            else:
                logger.info(
                    "Cached web index invalidated due to hash mismatch with no field-level diff."
                )

        self._crawl_and_build_web_index()

    def reindex_web(self) -> None:
        if not self.config.web_enabled:
            raise ValueError("Web retrieval is disabled. Set CHATBOT_WEB_ENABLED=true first.")
        self._ensure_web_index(force_rebuild=True)

    def force_reload(self) -> None:
        logger.info("Manual reload requested.")
        self._build_index()
        if self.config.web_enabled:
            self._ensure_web_index(force_rebuild=False)

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
            "web_enabled": self.config.web_enabled,
            "web_allowed_domains": self.config.web_allowed_domains,
            "web_seed_urls": self.config.web_seed_urls,
            "web_max_pages": self.config.web_max_pages,
            "web_top_k": self.config.web_top_k,
            "web_index_dir": str(self.config.web_index_dir),
            "web_config_hash": self._web_config_hash(),
            "debug": self.config.debug,
            "log_level": self.config.log_level,
        }

    def _reload_if_needed(self) -> None:
        if not self.config.hot_reload:
            return

        try:
            current_mtime_ns = self.knowledge_path.stat().st_mtime_ns
        except FileNotFoundError:
            return

        if self._knowledge_mtime_ns is None or current_mtime_ns != self._knowledge_mtime_ns:
            logger.info("Detected knowledge.txt change. Rebuilding index.")
            self._build_index()

    def _score_candidate(self, query_norm: str, idx: int, similarity: float) -> CandidateScore:
        query_tokens = set(query_norm.split())
        candidate = self.normalized_data[idx]
        candidate_tokens = set(candidate.split())

        overlap = len(query_tokens & candidate_tokens)
        union = len(query_tokens | candidate_tokens) or 1
        lexical_score = overlap / union

        final_score = 0.75 * similarity + 0.25 * lexical_score
        return CandidateScore(
            index=idx,
            answer=self.raw_data[idx],
            similarity=similarity,
            lexical_score=lexical_score,
            final_score=final_score,
        )

    def _ask_web(self, query: str) -> RetrievalResult | None:
        if not self.web_store:
            return None

        hits = self.web_store.search(query, top_k=self.config.web_top_k)
        if not hits:
            return None

        top = hits[0]
        citations = []
        seen = set()
        for hit in hits:
            url = hit.chunk.source_url
            if url not in seen:
                citations.append(url)
                seen.add(url)

        answer = f"{top.chunk.text}\n\nSource: {top.chunk.source_url}"
        return RetrievalResult(
            answer=answer,
            similarity=top.score,
            index=top.chunk.chunk_id,
            candidates=[],
            used_fallback=False,
            citation_urls=citations,
        )

    def ask(self, query: str) -> RetrievalResult:
        self._reload_if_needed()

        if self.config.web_enabled:
            web_result = self._ask_web(query)
            if web_result and web_result.similarity >= self.config.similarity_threshold:
                return web_result

        query_norm = normalize_text(query, fold_accents=True)
        if not query_norm:
            return RetrievalResult(
                answer="Please enter a meaningful question.",
                similarity=0.0,
                index=-1,
                candidates=[],
                used_fallback=True,
                citation_urls=None,
            )

        if self.vectorizer is None or self.matrix is None:
            raise RuntimeError("Knowledge index is not ready.")

        query_vector = self.vectorizer.transform([query_norm])
        k = min(self.config.retrieval_k, len(self.raw_data))
        similarities = cosine_similarity(query_vector, self.matrix)[0]
        indices = similarities.argsort()[::-1][:k]

        scored = [
            self._score_candidate(query_norm, int(idx), float(similarities[idx])) for idx in indices
        ]
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
                citation_urls=None,
            )

        return RetrievalResult(
            answer=best.answer,
            similarity=best.similarity,
            index=best.index,
            candidates=top_explanations,
            used_fallback=False,
            citation_urls=(
                [self.local_source_urls[best.index]] if self.local_source_urls[best.index] else None
            ),
        )
