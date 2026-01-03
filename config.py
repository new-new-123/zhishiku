"""
建筑规范知识库系统配置文件 - 多专业分类架构
"""
import os
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DATA_DIR_CHUNKS = BASE_DIR / 'chunks'
DATA_DIR_CHUNKS.mkdir(exist_ok=True)

# ==================== 专业分类配置 ====================
CATEGORIES = {
    "建筑": {
        "collection": "standards_architecture",
        "keywords": ["建筑设计", "防火", "住宅", "公共建筑", "装修", "无障碍"],
        "description": "建筑设计规范"
    },
    "结构": {
        "collection": "standards_structure",
        "keywords": ["抗震", "混凝土", "钢结构", "砌体", "地基", "荷载"],
        "description": "结构设计规范"
    },
    "给排水": {
        "collection": "standards_plumbing",
        "keywords": ["给水", "排水", "消防", "水暖"],
        "description": "给排水规范"
    },
    "暖通": {
        "collection": "standards_hvac",
        "keywords": ["暖通", "空调", "通风", "采暖", "制冷"],
        "description": "暖通空调规范"
    },
    "电气": {
        "collection": "standards_electrical",
        "keywords": ["电气", "照明", "供配电", "防雷", "弱电"],
        "description": "电气工程规范"
    },
    "造价": {
        "collection": "standards_cost",
        "keywords": ["工程量", "计价", "定额", "清单", "造价"],
        "description": "工程造价规范"
    },
    "其他": {
        "collection": "standards_others",
        "keywords": [],
        "description": "其他规范"
    }
}

# ==================== 向量模型配置 ====================
class EmbeddingConfig(BaseModel):
    """向量化模型配置"""
    model_name: str = "BAAI/bge-large-zh-v1.5"
    # 本地模型路径
    model_path: Optional[str] = os.getenv("BGE_MODEL_PATH", r"D:\RAG\niu_weitiao\bge-large-zh-v1___5")
    max_length: int = 512
    batch_size: int = 32
    device: str = "cuda"

# ==================== Milvus 配置 ====================
class MilvusConfig(BaseModel):
    """Milvus 向量数据库配置"""
    host: str = "localhost"
    port: int = 19530
    dimension: int = 1024  # BGE Large 维度
    index_type: str = "IVF_FLAT"
    metric_type: str = "IP"
    nlist: int = 1024

    def get_collection_name(self, category: str) -> str:
        """根据专业获取集合名称"""
        return CATEGORIES.get(category, CATEGORIES["其他"])["collection"]

# ==================== PDF 解析配置 ====================
class ParserConfig(BaseModel):
    """PDF 解析配置"""
    chunk_size: int = 512
    chunk_overlap: int = 50
    enable_table_extraction: bool = True
    enable_ocr: bool = False
    clause_pattern: str = r"^(?:第\s*)?(\d+[\.\-]\d+[\.\-]\d+|\d+\.\d+\.\d+\.\d+)(?:\s*条)?"

# ==================== 检索配置 ====================
class RetrievalConfig(BaseModel):
    """检索配置"""
    vector_top_k: int = 50
    bm25_top_k: int = 30
    # 重排模型路径 - 优先使用本地路径
    rerank_model: str = os.getenv("RERANK_MODEL_PATH", "BAAI/bge-reranker-v2-m3")
    rerank_top_k: int = 10
    vector_weight: float = 0.6
    bm25_weight: float = 0.4
    # 是否启用重排（如果模型加载失败，可以禁用）
    enable_rerank: bool = os.getenv("ENABLE_RERANK", "true").lower() == "true"

# ==================== DEEP_SEEK LLM 配置 ====================
class LLMConfig(BaseModel):
    """大模型配置"""
    model_name: str = os.getenv("DEEPSEEK_MODEL")
    api_key: Optional[str] =  os.getenv("DEEPSEEK_API_KEY")
    base_url: Optional[str] = os.getenv("DEEPSEEK_BASE_URL")
    temperature: float = 0.1
    max_tokens: int = 2000

# ==================== MySQL 配置 ====================
class MySQLConfig(BaseModel):
    """MySQL 数据库配置"""
    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3306"))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "")
    database: str = os.getenv("MYSQL_DATABASE", "building_standards")
    charset: str = "utf8mb4"

# ==================== 元数据 Schema ====================
METADATA_SCHEMA = {
    "std_id": "规范编号 (如 GB50016-2014)",
    "std_name": "规范名称",
    "category": "专业类别 (建筑/结构/给排水/暖通/电气/造价/其他)",
    "level": "规范等级 (国标/行标/地标)",
    "chapter_title": "章节标题",
    "clause_number": "条文号 (如 3.2.1)",
    "is_mandatory": "是否强制性条文 (bool)",
    "publish_year": "发布年份",
    "status": "状态 (active/deprecated)",
    "page_number": "页码",
    "has_table": "是否包含表格",
    "has_figure": "是否包含图片",
    "description": "条文描述（用于检索展示）"
}

# ==================== 实例化配置 ====================
embedding_config = EmbeddingConfig()
milvus_config = MilvusConfig()
parser_config = ParserConfig()
retrieval_config = RetrievalConfig()
llm_config = LLMConfig()
mysql_config = MySQLConfig()

