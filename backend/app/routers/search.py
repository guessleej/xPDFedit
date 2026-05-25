"""語意搜尋 API — bge-m3 + Elasticsearch kNN"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..core.deps import get_current_user
from ..models.user import User
from ..config import settings

router = APIRouter()
ES_INDEX = "xcloudpdf_semantic"


class SemanticSearchResult(BaseModel):
    filename: str
    page: int
    chunk: int
    text: str
    score: float


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SemanticSearchResult]
    total: int


@router.get("/semantic", response_model=SemanticSearchResponse, summary="語意搜尋")
async def semantic_search(
    q: str = Query(..., description="搜尋問句"),
    top_k: int = Query(10, ge=1, le=50, description="回傳筆數"),
    filename: str | None = Query(None, description="限定檔名（選填）"),
    current_user: User = Depends(get_current_user),
):
    """向量化查詢句，在 Elasticsearch 中做 kNN 搜尋，回傳最相關段落"""
    import httpx
    from elasticsearch import Elasticsearch

    if not settings.llm_base_url:
        from fastapi import HTTPException
        raise HTTPException(503, "尚未設定 LLM 服務")

    # 取得查詢向量
    ollama_base = settings.llm_base_url.rstrip("/").replace("/v1", "")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{ollama_base}/api/embed",
            json={"model": settings.embedding_model, "input": q},
        )
        r.raise_for_status()
        query_vec = r.json()["embeddings"][0]

    # kNN 搜尋
    es = Elasticsearch(settings.elasticsearch_url)
    knn_body: dict = {
        "knn": {
            "field": "embedding",
            "query_vector": query_vec,
            "k": top_k,
            "num_candidates": top_k * 10,
        },
        "_source": ["filename", "page", "chunk", "text"],
    }
    if filename:
        knn_body["knn"]["filter"] = {"term": {"filename": filename}}

    resp = es.search(index=ES_INDEX, body=knn_body, ignore_unavailable=True)
    hits = resp.get("hits", {}).get("hits", [])

    results = [
        SemanticSearchResult(
            filename=h["_source"].get("filename", ""),
            page=h["_source"].get("page", 0),
            chunk=h["_source"].get("chunk", 0),
            text=h["_source"].get("text", ""),
            score=round(h.get("_score", 0), 4),
        )
        for h in hits
    ]

    return SemanticSearchResponse(query=q, results=results, total=len(results))


@router.get("/semantic/stats", summary="索引統計")
async def semantic_stats(current_user: User = Depends(get_current_user)):
    """回傳已索引的文件列表與段落數"""
    from elasticsearch import Elasticsearch
    es = Elasticsearch(settings.elasticsearch_url)
    try:
        agg = es.search(index=ES_INDEX, ignore_unavailable=True, body={
            "size": 0,
            "aggs": {
                "files": {
                    "terms": {"field": "filename", "size": 100}
                }
            }
        })
        buckets = agg.get("aggregations", {}).get("files", {}).get("buckets", [])
        files = [{"filename": b["key"], "chunks": b["doc_count"]} for b in buckets]
        total_chunks = sum(b["doc_count"] for b in buckets)
    except Exception:
        files, total_chunks = [], 0

    return {"files": files, "total_chunks": total_chunks, "index": ES_INDEX}
