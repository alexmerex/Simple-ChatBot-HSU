from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .text_utils import normalize_text

try:
    import faiss
except ImportError:  # Optional acceleration; NumPy remains fully functional.
    faiss = None


@dataclass(slots=True)
class WebChunk:
    chunk_id: int
    source_url: str
    title: str
    text: str


@dataclass(slots=True)
class SearchHit:
    chunk: WebChunk
    score: float


class FaissWebStore:
    def __init__(self):
        self.vectorizer: TfidfVectorizer | None = None
        self.index: Any | None = None
        self.chunks: list[WebChunk] = []
        self.backend = "faiss" if faiss is not None else "numpy"

    @staticmethod
    def _chunk_text(text: str, max_words: int = 120) -> list[str]:
        words = text.split()
        if not words:
            return []

        chunks: list[str] = []
        for i in range(0, len(words), max_words):
            segment = words[i : i + max_words]
            if segment:
                chunks.append(" ".join(segment))
        return chunks

    def build(self, pages: list, max_words_per_chunk: int = 120) -> None:
        all_chunks: list[WebChunk] = []
        chunk_id = 0

        for page in pages:
            for part in self._chunk_text(page.text, max_words=max_words_per_chunk):
                if normalize_text(part, fold_accents=True):
                    all_chunks.append(
                        WebChunk(
                            chunk_id=chunk_id,
                            source_url=page.url,
                            title=page.title,
                            text=part,
                        )
                    )
                    chunk_id += 1

        if not all_chunks:
            raise ValueError("No valid chunks extracted from crawled pages.")

        self.chunks = all_chunks
        corpus = [normalize_text(c.text, fold_accents=True) for c in all_chunks]

        max_df = 1.0 if len(corpus) == 1 else 0.98
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=1,
            max_df=max_df,
        )
        x = self.vectorizer.fit_transform(corpus).astype(np.float32)
        dense = x.toarray()

        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        dense = dense / norms

        if faiss is not None:
            index = faiss.IndexFlatIP(dense.shape[1])
            index.add(dense)
            self.index = index
            self.backend = "faiss"
        else:
            self.index = dense
            self.backend = "numpy"

    @staticmethod
    def _paths(output_dir: Path) -> dict[str, Path]:
        return {
            "index": output_dir / "web.index",
            "chunks": output_dir / "web_chunks.jsonl",
            "vectorizer": output_dir / "vectorizer.pkl",
            "meta": output_dir / "web_meta.json",
        }

    def save(self, output_dir: Path, meta: dict | None = None) -> None:
        if self.index is None or self.vectorizer is None:
            raise ValueError("Index is not built.")

        output_dir.mkdir(parents=True, exist_ok=True)
        paths = self._paths(output_dir)

        if self.backend == "faiss":
            faiss.write_index(self.index, str(paths["index"]))
        else:
            with paths["index"].open("wb") as file:
                np.save(file, self.index, allow_pickle=False)

        with paths["chunks"].open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

        with paths["vectorizer"].open("wb") as f:
            pickle.dump(self.vectorizer, f)

        meta_payload = {**(meta or {}), "store_backend": self.backend}
        paths["meta"].write_text(
            json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load(self, output_dir: Path) -> bool:
        paths = self._paths(output_dir)
        if not all(path.exists() for path in paths.values()):
            return False

        try:
            meta = self.load_meta(output_dir)
            backend = meta.get("store_backend", "faiss")
            if backend == "faiss":
                if faiss is None:
                    return False
                index = faiss.read_index(str(paths["index"]))
            elif backend == "numpy":
                with paths["index"].open("rb") as file:
                    index = np.load(file, allow_pickle=False)
            else:
                return False

            chunks: list[WebChunk] = []
            with paths["chunks"].open("r", encoding="utf-8") as file:
                for line in file:
                    if line.strip():
                        chunks.append(WebChunk(**json.loads(line)))

            with paths["vectorizer"].open("rb") as file:
                vectorizer = pickle.load(file)

            if not chunks:
                return False

            self.index = index
            self.chunks = chunks
            self.vectorizer = vectorizer
            self.backend = backend
            return True
        except (
            OSError,
            EOFError,
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
            json.JSONDecodeError,
            pickle.UnpicklingError,
        ):
            return False

    @staticmethod
    def load_meta(output_dir: Path) -> dict:
        meta_path = output_dir / "web_meta.json"
        if not meta_path.exists():
            return {}
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, json.JSONDecodeError):
            return {}

    def search(self, query: str, top_k: int = 3) -> list[SearchHit]:
        if self.index is None or self.vectorizer is None:
            raise ValueError("Index is not ready.")

        normalized = normalize_text(query, fold_accents=True)
        if not normalized:
            return []

        q = self.vectorizer.transform([normalized]).astype(np.float32).toarray()
        norm = np.linalg.norm(q, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        q = q / norm

        k = min(top_k, len(self.chunks))
        if self.backend == "faiss":
            scores, indices = self.index.search(q, k)
            score_row, index_row = scores[0], indices[0]
        else:
            score_row_all = np.asarray(self.index @ q[0], dtype=np.float32)
            index_row = np.argsort(score_row_all)[::-1][:k]
            score_row = score_row_all[index_row]

        hits: list[SearchHit] = []
        for score, idx in zip(score_row, index_row):
            if idx < 0:
                continue
            hits.append(SearchHit(chunk=self.chunks[int(idx)], score=float(score)))
        return hits
