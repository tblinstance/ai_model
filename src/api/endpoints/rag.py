"""RAG (Retrieval-Augmented Generation), semantic vector search, and web knowledge scraping endpoints."""

from typing import Any
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/rag", tags=["RAG & Vector Memory"])


class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Semantic search query")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of results to return")
    min_score: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum cosine similarity")


class RAGIndexRequest(BaseModel):
    id: str = Field(..., description="Unique document ID")
    text: str = Field(..., description="Document content to embed and store")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Custom metadata tags")


class RAGScrapeRequest(BaseModel):
    url: str = Field(..., description="Webpage URL to scrape with BeautifulSoup4 and index into ChromaDB")
    html: str | None = Field(default=None, description="Optional raw HTML content to parse")


@router.post("/query")
async def query_rag(payload: RAGQueryRequest, request: Request) -> dict[str, Any]:
    """Search semantic vector memory for top-k relevant knowledge snippets."""
    router_instance = request.app.state.engine_router
    results = router_instance.query_rag(
        query=payload.query,
        top_k=payload.top_k,
        min_score=payload.min_score,
    )
    return {
        "query": payload.query,
        "count": len(results),
        "results": results,
    }


@router.post("/index")
async def index_rag(payload: RAGIndexRequest, request: Request) -> dict[str, Any]:
    """Index a custom document into semantic vector memory and ChromaDB."""
    router_instance = request.app.state.engine_router
    router_instance.add_rag_document(
        doc_id=payload.id,
        text=payload.text,
        metadata=payload.metadata,
    )
    total_docs = router_instance.registry.vector_memory.count()
    return {
        "status": "indexed",
        "id": payload.id,
        "total_documents": total_docs,
    }


@router.post("/scrape")
async def scrape_rag(payload: RAGScrapeRequest, request: Request) -> dict[str, Any]:
    """Scrape webpage content using BeautifulSoup4 and index text into vector memory."""
    router_instance = request.app.state.engine_router
    return router_instance.scrape_rag_url(url=payload.url, html_content=payload.html)
