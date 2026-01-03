"""
Milvus 向量数据库管理 - 多专业分类架构
支持：
1. 按专业分类创建独立集合
2. 向量插入与元数据过滤
3. 混合检索（向量 + 标量过滤）
"""
from typing import List, Dict, Optional
from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType,
    utility
)
from loguru import logger

from config import milvus_config, METADATA_SCHEMA, CATEGORIES


class MilvusManager:
    """Milvus 数据库管理器 - 支持多专业分类"""

    def __init__(self, category: str = "其他", auto_create: bool = True):
        """
        初始化
        Args:
            category: 专业类别 (建筑/结构/给排水/暖通/电气/造价/其他)
            auto_create: 是否自动创建集合
        """
        self.config = milvus_config
        self.category = category
        self.collection_name = self.config.get_collection_name(category)
        self.collection = None
        self._connect()

        # 检查集合是否存在
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.collection.load()
            logger.info(f"集合已加载: {self.collection_name} ({self.collection.num_entities} 条数据)")
        elif auto_create:
            self.create_collection(drop_existing=False)

    def _connect(self):
        """连接 Milvus"""
        try:
            connections.connect(
                alias="default",
                host=self.config.host,
                port=self.config.port
            )
            logger.info(f"已连接到 Milvus: {self.config.host}:{self.config.port}")
        except Exception as e:
            logger.error(f"Milvus 连接失败: {e}")
            raise

    def create_collection(self, drop_existing: bool = False):
        """
        创建集合

        Args:
            drop_existing: 是否删除已存在的集合
        """
        # 删除已存在的集合
        if drop_existing and utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            logger.info(f"已删除旧集合: {self.collection_name}")

        # 如果集合已存在，直接加载
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.collection.load()
            logger.info(f"集合已存在，直接加载: {self.collection_name} (专业: {self.category})")
            return

        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.config.dimension),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="enhanced_text", dtype=DataType.VARCHAR, max_length=65535),

            # 元数据字段
            FieldSchema(name="std_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="std_name", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="level", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="chapter_title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="clause_number", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="is_mandatory", dtype=DataType.BOOL),
            FieldSchema(name="publish_year", dtype=DataType.INT64),
            FieldSchema(name="page_number", dtype=DataType.INT64),
            FieldSchema(name="has_table", dtype=DataType.BOOL),
            FieldSchema(name="has_figure", dtype=DataType.BOOL),
            FieldSchema(name="status", dtype=DataType.VARCHAR, max_length=20),
        ]

        # 创建 Schema
        schema = CollectionSchema(
            fields=fields,
            description=f"建筑规范知识库 - {self.category}"
        )

        # 创建集合
        self.collection = Collection(
            name=self.collection_name,
            schema=schema
        )

        logger.info(f"集合创建成功: {self.collection_name} (专业: {self.category})")

        # 创建索引
        self._create_index()
    
    def _create_index(self):
        """创建向量索引"""
        index_params = {
            "index_type": self.config.index_type,
            "metric_type": self.config.metric_type,
            "params": {"nlist": self.config.nlist}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        logger.info("向量索引创建成功")
        
        # 加载集合到内存
        self.collection.load()
        logger.info("集合已加载到内存")
    
    def insert(self, chunks: List[Dict]):
        """
        批量插入文档块

        Args:
            chunks: 文档块列表，每个块包含 embedding, text, metadata
        """
        if not chunks:
            logger.warning("没有数据需要插入")
            return

        # 准备数据
        data = {
            "embedding": [],
            "text": [],
            "enhanced_text": [],
            "std_id": [],
            "std_name": [],
            "category": [],
            "level": [],
            "chapter_title": [],
            "clause_number": [],
            "is_mandatory": [],
            "publish_year": [],
            "page_number": [],
            "has_table": [],
            "has_figure": [],
            "status": []
        }

        for chunk in chunks:
            embedding = chunk["embedding"]

            # 调试：检查 embedding 类型
            if len(data["embedding"]) == 0:  # 只打印第一个
                logger.debug(f"Embedding 类型: {type(embedding)}, 长度: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
                if isinstance(embedding, list) and len(embedding) > 0:
                    logger.debug(f"第一个元素类型: {type(embedding[0])}")

            data["embedding"].append(embedding)
            data["text"].append(chunk["text"])
            data["enhanced_text"].append(chunk.get("enhanced_text", chunk["text"]))

            # 元数据（带默认值）
            metadata = chunk["metadata"]
            data["std_id"].append(metadata.get("std_id", "UNKNOWN"))
            data["std_name"].append(metadata.get("std_name", "未知规范"))
            data["category"].append(metadata.get("category", "其他"))
            data["level"].append(metadata.get("level", "国标"))
            data["chapter_title"].append(metadata.get("chapter_title", ""))
            data["clause_number"].append(metadata.get("clause_number", ""))
            data["is_mandatory"].append(metadata.get("is_mandatory", False))
            data["publish_year"].append(metadata.get("publish_year", 2024))
            data["page_number"].append(metadata.get("page_number", 0))
            data["has_table"].append(metadata.get("has_table", False))
            data["has_figure"].append(metadata.get("has_figure", False))
            data["status"].append(metadata.get("status", "active"))

        # 插入数据
        try:
            # Milvus 需要列式数据：每个字段是一个列表
            # 格式：[field1_list, field2_list, ...]
            entities = [
                data["embedding"],
                data["text"],
                data["enhanced_text"],
                data["std_id"],
                data["std_name"],
                data["category"],
                data["level"],
                data["chapter_title"],
                data["clause_number"],
                data["is_mandatory"],
                data["publish_year"],
                data["page_number"],
                data["has_table"],
                data["has_figure"],
                data["status"]
            ]

            logger.debug(f"准备插入 {len(chunks)} 条数据，共 {len(entities)} 个字段")

            self.collection.insert(entities)
            self.collection.flush()
            logger.info(f"成功插入 {len(chunks)} 条数据")
        except Exception as e:
            logger.error(f"数据插入失败: {e}")
            raise

    def search(self, query_embedding: List[float], top_k: int = 10,
               filters: Optional[Dict] = None) -> List[Dict]:
        """
        向量检索

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            filters: 元数据过滤条件，如 {"category": "结构", "is_mandatory": True}

        Returns:
            检索结果列表
        """
        # 确保集合已加载
        if self.collection is None:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                self.collection.load()
            else:
                logger.warning(f"集合 {self.collection_name} 不存在")
                return []

        # 检查集合是否有数据
        if self.collection.num_entities == 0:
            logger.warning(f"集合 {self.collection_name} 没有数据")
            return []

        search_params = {
            "metric_type": self.config.metric_type,
            "params": {"nprobe": 10}
        }

        # 构建过滤表达式
        expr = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f'{key} == "{value}"')
                elif isinstance(value, bool):
                    conditions.append(f'{key} == {str(value).lower()}')
                else:
                    conditions.append(f'{key} == {value}')
            expr = " && ".join(conditions)

        # 执行检索
        output_fields = ["text", "enhanced_text", "std_id", "std_name", "category",
                        "level", "chapter_title", "clause_number", "is_mandatory",
                        "publish_year", "page_number", "has_table", "has_figure", "status"]

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=output_fields
        )

        # 格式化结果
        formatted_results = []
        for hits in results:
            for hit in hits:
                formatted_results.append({
                    "id": hit.id,
                    "score": hit.score,
                    "text": hit.entity.get("text"),
                    "enhanced_text": hit.entity.get("enhanced_text"),
                    "metadata": {
                        "std_id": hit.entity.get("std_id"),
                        "std_name": hit.entity.get("std_name"),
                        "category": hit.entity.get("category"),
                        "level": hit.entity.get("level"),
                        "chapter_title": hit.entity.get("chapter_title"),
                        "clause_number": hit.entity.get("clause_number"),
                        "is_mandatory": hit.entity.get("is_mandatory"),
                        "publish_year": hit.entity.get("publish_year"),
                        "page_number": hit.entity.get("page_number"),
                        "has_table": hit.entity.get("has_table"),
                        "has_figure": hit.entity.get("has_figure"),
                        "status": hit.entity.get("status")
                    }
                })

        return formatted_results

    def get_stats(self) -> Dict:
        """获取集合统计信息"""
        stats = {
            "total_entities": self.collection.num_entities,
            "collection_name": self.collection_name,
            "category": self.category
        }
        return stats


def get_all_collections_stats() -> Dict:
    """获取所有专业集合的统计信息"""
    stats = {}
    for category in CATEGORIES.keys():
        try:
            manager = MilvusManager(category=category, auto_create=False)
            if utility.has_collection(manager.collection_name):
                # 确保集合已加载
                if manager.collection is None:
                    manager.collection = Collection(manager.collection_name)
                manager.collection.load()
                stats[category] = manager.get_stats()
        except Exception as e:
            logger.warning(f"获取 {category} 统计信息失败: {e}")
    return stats

