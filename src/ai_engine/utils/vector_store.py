"""Vector similarity search and semantic memory store (RAG) using Sentence-Transformers, ChromaDB, and BeautifulSoup4."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import chromadb
    _CHROMADB_AVAILABLE = True
except ImportError:
    _CHROMADB_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


def _hash_embed(text: str, dim: int = 128) -> np.ndarray:
    """High-speed deterministic token & n-gram embedding fallback in NumPy."""
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().strip().split()
    if not words:
        return vec
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[idx] += sign * (1.0 / math.sqrt(len(words)))
    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec /= norm
    return vec


class VectorMemory:
    """Semantic vector database supporting dense retrieval, ChromaDB collections, and URL scraping."""

    def __init__(self, embedding_model: str | None = None, dim: int = 128) -> None:
        self.dim = dim
        self.model = None
        if _SENTENCE_TRANSFORMERS_AVAILABLE and embedding_model:
            try:
                self.model = SentenceTransformer(embedding_model)
                self.dim = self.model.get_sentence_embedding_dimension()
            except Exception:
                self.model = None

        self.chroma_client = None
        self.chroma_collection = None
        if _CHROMADB_AVAILABLE:
            try:
                self.chroma_client = chromadb.Client()
                self.chroma_collection = self.chroma_client.get_or_create_collection("ai_model_rag")
            except Exception:
                self.chroma_client = None
                self.chroma_collection = None

        self.doc_ids: list[str] = []
        self.doc_texts: list[str] = []
        self.doc_metas: list[dict[str, Any]] = []
        self.embeddings: list[np.ndarray] = []

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text string into a normalized dense vector."""
        if self.model is not None:
            try:
                emb = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
                return emb.astype(np.float32)
            except Exception:
                pass
        return _hash_embed(text, dim=self.dim)

    def add_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Add and embed a document into both local memory and ChromaDB."""
        emb = self.embed(text)
        self.doc_ids.append(doc_id)
        self.doc_texts.append(text)
        meta = metadata or {}
        self.doc_metas.append(meta)
        self.embeddings.append(emb)

        if self.chroma_collection is not None:
            try:
                self.chroma_collection.add(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[{k: str(v) for k, v in meta.items()}],
                    embeddings=[emb.tolist()],
                )
            except Exception:
                pass

    def search(self, query: str, top_k: int = 3, min_score: float = 0.1) -> list[dict[str, Any]]:
        """Search the vector store for top-k semantically relevant documents."""
        if not self.embeddings:
            return []
        q_emb = self.embed(query)
        matrix = np.vstack(self.embeddings)  # (N, D)
        scores = np.dot(matrix, q_emb)       # (N,)

        ranked_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score >= min_score:
                results.append({
                    "id": self.doc_ids[idx],
                    "text": self.doc_texts[idx],
                    "score": round(score, 4),
                    "metadata": self.doc_metas[idx],
                })
        return results

    def scrape_and_index_url(self, url: str, html_content: str | None = None) -> dict[str, Any]:
        """Scrape webpage content using BeautifulSoup4 and index it into vector memory."""
        if not _BS4_AVAILABLE:
            return {"error": "BeautifulSoup4 not available", "success": False}

        text = ""
        title = url
        try:
            if html_content:
                soup = BeautifulSoup(html_content, "html.parser")
            else:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "AIEngineScraper/1.0"})
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(html, "html.parser")

            if soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.extract()

            text = " ".join(soup.get_text().split())
            if not text:
                return {"error": "No textual content found in URL", "success": False}

            # Chunk into paragraphs
            chunk_size = 500
            chunks = [text[i:i + chunk_size] for i in range(0, min(len(text), 2500), chunk_size)]
            indexed_count = 0
            for idx, chunk in enumerate(chunks):
                doc_id = f"url_{hashlib.md5(url.encode()).hexdigest()[:8]}_{idx}"
                self.add_document(doc_id=doc_id, text=chunk, metadata={"source": url, "title": title, "chunk": idx})
                indexed_count += 1

            return {
                "url": url,
                "title": title,
                "indexed_chunks": indexed_count,
                "total_chars": len(text),
                "success": True,
            }
        except Exception as exc:
            return {"url": url, "error": str(exc), "success": False}

    def load_knowledge_base(self, json_path: str | Path, max_items: int = 100) -> int:
        """Pre-indexes documents from a knowledge base JSON file."""
        p = Path(json_path)
        if not p.exists():
            return 0
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded = 0
            for item in data[:max_items]:
                prompt = item.get("prompt", "")
                response = item.get("response", "")
                if prompt and response:
                    doc_id = f"kb_{loaded}"
                    content = f"{prompt}\n{response}"
                    self.add_document(doc_id=doc_id, text=content, metadata={"intent": item.get("intent")})
                    loaded += 1
            return loaded
        except Exception:
            return 0

    def count(self) -> int:
        return len(self.doc_ids)
