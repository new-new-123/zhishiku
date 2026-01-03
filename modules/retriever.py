"""
统一检索模块 - 支持向量检索 + BM25 + 重排
整合了单专业和多专业检索功能
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
import jieba
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

sys.path.append(str(Path(__file__).parent.parent))

from modules.embedder import Embedder
from modules.database import MilvusManager
from config import CATEGORIES, retrieval_config

try:
    from FlagEmbedding import FlagReranker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logger.warning("FlagReranker 未安装，重排功能将不可用")


class UnifiedRetriever:
    """统一检索器 - 支持向量检索、BM25、重排"""

    def __init__(self, categories: Optional[List[str]] = None, enable_bm25: bool = True):
        """
        初始化检索器

        Args:
            categories: 专业类别列表，None 表示所有专业
            enable_bm25: 是否启用 BM25 检索
        """
        self.config = retrieval_config
        self.embedder = Embedder()
        self.enable_bm25 = enable_bm25
        self.executor = ThreadPoolExecutor(max_workers=4)

        # 初始化数据库管理器
        self.categories = categories or list(CATEGORIES.keys())
        self.managers = {}

        for category in self.categories:
            try:
                manager = MilvusManager(category=category, auto_create=False)
                if manager.collection and manager.collection.num_entities > 0:
                    self.managers[category] = manager
                    logger.info(f"✓ 加载 {category} 专业: {manager.collection.num_entities} 条数据")
                else:
                    logger.warning(f"✗ {category} 专业无数据，跳过")
            except Exception as e:
                logger.warning(f"✗ 初始化 {category} 失败: {e}")

        # BM25 索引
        self.bm25_indices = {}
        self.corpus_data = {}

        if enable_bm25 and self.managers:
            self._build_bm25_indices()

        # 重排模型
        self.reranker = None
        if RERANKER_AVAILABLE and self.config.enable_rerank:
            self._load_reranker()

    def _build_bm25_indices(self):
        """为每个专业构建 BM25 索引"""
        logger.info("正在构建 BM25 索引...")

        for category, manager in self.managers.items():
            try:
                # 从数据库查询数据
                results = manager.collection.query(
                    expr="id > 0",
                    output_fields=["id", "text", "std_id", "std_name", "category", "level",
                                   "chapter_title", "clause_number", "is_mandatory",
                                   "publish_year", "page_number", "has_table", "has_figure", "status"],
                    limit=10000
                )

                if not results:
                    continue

                # 保存语料库数据
                corpus_texts = [r["text"] for r in results]
                corpus_ids = [r["id"] for r in results]
                corpus_metadata = [{
                    "std_id": r.get("std_id"),
                    "std_name": r.get("std_name"),
                    "category": r.get("category"),
                    "level": r.get("level"),
                    "chapter_title": r.get("chapter_title"),
                    "clause_number": r.get("clause_number"),
                    "is_mandatory": r.get("is_mandatory"),
                    "publish_year": r.get("publish_year"),
                    "page_number": r.get("page_number"),
                    "has_table": r.get("has_table"),
                    "has_figure": r.get("has_figure"),
                    "status": r.get("status")
                } for r in results]

                # 分词并构建索引
                tokenized_corpus = [list(jieba.cut(text)) for text in corpus_texts]
                bm25_index = BM25Okapi(tokenized_corpus)

                self.bm25_indices[category] = bm25_index
                self.corpus_data[category] = {
                    "texts": corpus_texts,
                    "ids": corpus_ids,
                    "metadata": corpus_metadata
                }

                logger.info(f"✓ {category} BM25 索引构建完成: {len(corpus_texts)} 条")

            except Exception as e:
                logger.warning(f"✗ {category} BM25 索引构建失败: {e}")

    def _load_reranker(self):
        """加载重排模型"""
        try:
            logger.info(f"正在加载重排模型: {self.config.rerank_model}")
            self.reranker = FlagReranker(
                self.config.rerank_model,
                use_fp16=True
            )
            logger.info("✓ 重排模型加载成功")
        except Exception as e:
            logger.warning(f"✗ 重排模型加载失败: {e}")
            self.reranker = None



    def search(
        self,
        query: str,
        top_k: int = 10,
        is_mandatory_only: bool = False,
        categories: Optional[List[str]] = None
    ) -> List[Dict]:
        """混合检索（并行优化）"""
        search_categories = categories or list(self.managers.keys())

        # 并行执行向量检索和 BM25 检索
        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(self._vector_search, query, search_categories, is_mandatory_only)

            if self.enable_bm25 and self.bm25_indices:
                bm25_future = executor.submit(self._bm25_search, query, search_categories)
                vector_results = vector_future.result()
                bm25_results = bm25_future.result()
            else:
                vector_results = vector_future.result()
                bm25_results = []

        # 融合
        if bm25_results:
            fused_results = self._rrf_fusion(vector_results, bm25_results)
        else:
            fused_results = vector_results

        # 重排
        if self.reranker and len(fused_results) > 0:
            reranked_results = self._rerank(query, fused_results)
            return reranked_results[:top_k]

        return fused_results[:top_k]

    def _vector_search(self, query: str, categories: List[str], is_mandatory_only: bool) -> List[Dict]:
        """向量检索（并行多专业）"""
        query_embedding = self.embedder.encode([query])[0]
        if not isinstance(query_embedding, list):
            query_embedding = query_embedding.tolist()

        def search_category(category):
            if category not in self.managers:
                return []
            try:
                filters = {}
                if is_mandatory_only:
                    filters["is_mandatory"] = True

                return self.managers[category].search(
                    query_embedding=query_embedding,
                    top_k=self.config.vector_top_k,
                    filters=filters
                )
            except Exception as e:
                logger.warning(f"检索 {category} 失败: {e}")
                return []

        # 并行检索多个专业
        with ThreadPoolExecutor(max_workers=len(categories)) as executor:
            results_list = list(executor.map(search_category, categories))

        all_results = [r for results in results_list for r in results]
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:self.config.vector_top_k]

    def _bm25_search(self, query: str, categories: List[str]) -> List[Dict]:
        """BM25 检索"""
        tokenized_query = list(jieba.cut(query))
        all_results = []

        for category in categories:
            if category not in self.bm25_indices:
                continue

            try:
                bm25_index = self.bm25_indices[category]
                corpus_data = self.corpus_data[category]
                scores = bm25_index.get_scores(tokenized_query)

                top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:self.config.bm25_top_k]

                for idx in top_indices:
                    all_results.append({
                        "id": corpus_data["ids"][idx],
                        "text": corpus_data["texts"][idx],
                        "score": float(scores[idx]),
                        "category": category,
                        "metadata": corpus_data["metadata"][idx]
                    })
            except Exception as e:
                logger.warning(f"BM25 检索 {category} 失败: {e}")

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:self.config.bm25_top_k]

    def _rrf_fusion(self, vector_results: List[Dict], bm25_results: List[Dict], k: int = 60) -> List[Dict]:
        """RRF 融合"""
        rrf_scores = {}

        for rank, result in enumerate(vector_results):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        for rank, result in enumerate(bm25_results):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        id_to_result = {r["id"]: r for r in vector_results}
        id_to_result.update({r["id"]: r for r in bm25_results})

        fused_results = []
        for doc_id in sorted_ids:
            result = id_to_result[doc_id].copy()
            result["rrf_score"] = rrf_scores[doc_id]
            fused_results.append(result)

        return fused_results

    def _rerank(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """重排（批量处理优化）"""
        if not self.reranker or not candidates:
            return candidates

        try:
            # 批量计算分数
            pairs = [[query, cand.get("text", cand.get("enhanced_text", ""))] for cand in candidates]
            scores = self.reranker.compute_score(pairs, batch_size=32)

            for i, cand in enumerate(candidates):
                cand["rerank_score"] = float(scores[i]) if isinstance(scores, list) else float(scores)

            return sorted(candidates, key=lambda x: x.get("rerank_score", 0), reverse=True)
        except Exception as e:
            logger.warning(f"重排失败: {e}")
            return candidates


# 全局检索器实例（单例模式）
_global_retriever = None

def get_retriever(categories: Optional[List[str]] = None, enable_bm25: bool = True) -> UnifiedRetriever:
    """获取全局检索器实例（单例）"""
    global _global_retriever
    if _global_retriever is None:
        _global_retriever = UnifiedRetriever(categories=None, enable_bm25=enable_bm25)
        logger.info("✓ 全局检索器初始化完成")
    return _global_retriever


def search_standards(query: str, category: Optional[str] = None, is_mandatory_only: bool = False,
                    top_k: int = 10, enable_bm25: bool = True) -> List[Dict]:
    """检索建筑规范（统一接口）"""
    retriever = get_retriever(enable_bm25=enable_bm25)
    categories = [category] if category else None
    return retriever.search(query=query, top_k=top_k, is_mandatory_only=is_mandatory_only, categories=categories)


if __name__ == "__main__":
    query = "建筑抗震设防烈度有哪几个等级？"
    logger.info(f"查询: {query}")
    results = search_standards(query, category="结构", top_k=5)
    logger.info(f"\n检索到 {len(results)} 条结果：\n")

    for i, result in enumerate(results, 1):
        print(f"{'='*60}")
        print(f"结果 {i}:")
        print(f"规范: {result['metadata']['std_name']} ({result['metadata']['std_id']})")
        print(f"条文号: {result['metadata']['clause_number']}")
        print(f"章节: {result['metadata']['chapter_title']}")
        print(f"强制性: {'是' if result['metadata']['is_mandatory'] else '否'}")
        score = result.get('rerank_score') or result.get('rrf_score') or result.get('score', 0)
        print(f"相关度: {score:.4f}")
        print(f"\n内容:\n{result['text'][:300]}...")
        print()
