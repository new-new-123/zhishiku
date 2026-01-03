"""
主程序 - API 接口 (多专业分类架构)
提供：
1. 文档灌库接口
2. 多专业检索接口
3. RAG 问答接口
"""
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

sys.path.append(str(Path(__file__).parent))

from scripts.import_data import import_from_json
from modules.retriever import search_standards
from modules.database import get_all_collections_stats
from modules.rag_engine import RAGEngine
from config import CATEGORIES

# 初始化 FastAPI
app = FastAPI(title="建筑规范知识库 API (多专业分类)", version="2.0.0")


# ==================== 数据模型 ====================
class IngestRequest(BaseModel):
    """灌库请求"""
    json_path: str
    category: Optional[str] = None  # None 表示自动识别


class SearchRequest(BaseModel):
    """检索请求"""
    query: str
    category: Optional[str] = None  # None 表示全部专业
    is_mandatory_only: bool = False
    top_k: int = 10


class RAGRequest(BaseModel):
    """RAG 问答请求"""
    question: str
    category: Optional[str] = None
    is_mandatory_only: bool = False
    session_id: str = "default"
    top_k: int = 5


class ClearHistoryRequest(BaseModel):
    """清空历史请求"""
    session_id: str


# ==================== API 接口 ====================
@app.get("/")
def root():
    """根路径"""
    return {
        "message": "建筑规范知识库 API (多专业分类架构)",
        "version": "2.0.0",
        "categories": list(CATEGORIES.keys()),
        "endpoints": {
            "stats": "/stats - 查看统计信息",
            "ingest": "/ingest - 导入 JSON 数据",
            "search": "/search - 检索规范",
            "ask": "/ask - RAG 问答",
            "clear_history": "/clear_history - 清空对话历史"
        }
    }


@app.get("/stats")
def api_stats():
    """获取统计信息"""
    try:
        stats = get_all_collections_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
def api_ingest(request: IngestRequest):
    """导入 JSON 数据"""
    try:
        import_from_json(request.json_path, request.category)
        return {"status": "success", "message": f"导入完成: {request.json_path}"}
    except Exception as e:
        logger.error(f"导入失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def api_search(request: SearchRequest):
    """检索规范"""
    try:
        results = search_standards(
            query=request.query,
            category=request.category,
            is_mandatory_only=request.is_mandatory_only,
            top_k=request.top_k
        )

        # 格式化返回结果
        formatted_results = []
        for result in results:
            formatted_results.append({
                "std_id": result["metadata"]["std_id"],
                "std_name": result["metadata"]["std_name"],
                "category": result["metadata"]["category"],
                "clause_number": result["metadata"]["clause_number"],
                "chapter_title": result["metadata"]["chapter_title"],
                "is_mandatory": result["metadata"]["is_mandatory"],
                "page_number": result["metadata"]["page_number"],
                "text": result["text"],
                "score": result.get("score", 0)
            })

        return {
            "status": "success",
            "query": request.query,
            "category": request.category or "全部专业",
            "total": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        logger.error(f"检索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def api_ask(request: RAGRequest):
    """RAG 问答"""
    try:
        rag_engine = RAGEngine(session_id=request.session_id)
        result = rag_engine.query(
            question=request.question,
            category=request.category,
            is_mandatory_only=request.is_mandatory_only,
            top_k=request.top_k
        )

        return {
            "status": "success",
            "answer": result["answer"],
            "references": result["references"],
            "session_id": result["session_id"]
        }

    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/clear_history")
def api_clear_history(request: ClearHistoryRequest):
    """清空对话历史"""
    try:
        rag_engine = RAGEngine(session_id=request.session_id)
        rag_engine.clear_history()
        return {
            "status": "success",
            "message": f"会话 {request.session_id} 历史已清空"
        }
    except Exception as e:
        logger.error(f"清空历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logger.info("启动建筑规范知识库 API (多专业分类架构)...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

