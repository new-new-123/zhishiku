"""
向量化模型封装 - BGE Large
"""
from typing import List, Union
import torch
from langchain_community.embeddings import HuggingFaceEmbeddings
from loguru import logger

from config import embedding_config


class Embedder:
    """BGE Large 向量化模型（单例模式）"""

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self.config = embedding_config
        self.model = None
        self._load_model()
        self._initialized = True

    def _load_model(self):
        """加载 BGE Large 模型"""
        model_path = self.config.model_path or self.config.model_name
        logger.info(f"正在加载向量模型: {model_path}")

        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = HuggingFaceEmbeddings(
                model_name=model_path,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info(f"模型加载成功 (设备: {device})")
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise

    def encode(self, texts: Union[str, List[str]],
               batch_size: int = None, show_progress: bool = False) -> List[List[float]]:
        """文本向量化"""
        if isinstance(texts, str):
            texts = [texts]

        try:
            embeddings = self.model.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"向量化失败: {e}")
            raise

    def encode_queries(self, queries: Union[str, List[str]]) -> List[List[float]]:
        """查询文本向量化"""
        if isinstance(queries, str):
            queries = [queries]

        try:
            embeddings = self.model.embed_documents(queries)
            return embeddings
        except Exception as e:
            logger.error(f"查询向量化失败: {e}")
            raise

    @property
    def dimension(self) -> int:
        """返回向量维度"""
        return 1024  # BGE Large 维度


# 兼容旧代码
EmbeddingModel = Embedder

# 全局单例
_embedding_model = None

def get_embedding_model() -> Embedder:
    """获取全局向量模型实例"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = Embedder()
    return _embedding_model
