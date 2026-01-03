"""
数据导入脚本 - 支持多专业分类
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from loguru import logger
from tqdm import tqdm

from modules.database import MilvusManager
from modules.embedder import Embedder
from config import CATEGORIES, DATA_DIR_CHUNKS

def auto_detect_category(std_name: str, std_id: str) -> str:
    """
    自动识别规范专业类别
    
    Args:
        std_name: 规范名称
        std_id: 规范编号
        
    Returns:
        专业类别
    """
    for category, info in CATEGORIES.items():
        for keyword in info["keywords"]:
            if keyword in std_name or keyword in std_id:
                return category
    return "其他"

def import_from_json(json_path: str, category: str = None):
    """
    从 JSON 文件导入数据

    Args:
        json_path: JSON 文件路径
        category: 专业类别，如果为 None 则自动识别
    """
    # 加载数据
    with open(json_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    if not chunks:
        logger.warning(f"文件为空: {json_path}")
        return

    # 自动识别专业类别
    if category is None:
        std_name = chunks[0]["metadata"].get("std_name", "")
        std_id = chunks[0]["metadata"].get("std_id", "")
        category = auto_detect_category(std_name, std_id)
        logger.info(f"自动识别专业类别: {category}")

    # 标准化元数据字段
    for chunk in chunks:
        metadata = chunk["metadata"]

        # 统一字段名
        if "chapter" in metadata and "chapter_title" not in metadata:
            metadata["chapter_title"] = metadata.pop("chapter")
        if "clause" in metadata and "clause_number" not in metadata:
            metadata["clause_number"] = metadata.pop("clause")

        # 确保所有必需字段存在
        metadata.setdefault("category", category)
        metadata.setdefault("level", "国标")
        metadata.setdefault("publish_year", 2024)
        metadata.setdefault("has_table", False)
        metadata.setdefault("has_figure", False)
        metadata.setdefault("status", "active")
        metadata.setdefault("page_number", 0)
        metadata.setdefault("is_mandatory", False)
        metadata.setdefault("chapter_title", "")
        metadata.setdefault("clause_number", "")

    # 初始化向量化模型
    logger.info("加载向量化模型...")
    embedder = Embedder()

    # 向量化
    logger.info("生成向量...")
    texts = [chunk.get("enhanced_text", chunk["text"]) for chunk in chunks]
    embeddings = embedder.encode(texts, show_progress=True)

    # 添加向量到 chunks
    # HuggingFaceEmbeddings 返回的已经是 list，不需要 tolist()
    for chunk, embedding in zip(chunks, embeddings):
        if isinstance(embedding, list):
            chunk["embedding"] = embedding
        else:
            chunk["embedding"] = embedding.tolist()

    # 初始化数据库
    logger.info(f"连接数据库 (专业: {category})...")
    db = MilvusManager(category=category, auto_create=True)

    # 插入数据
    logger.info("插入数据...")
    db.insert(chunks)

    logger.info(f"✓ 导入完成: {json_path} -> {category}")

def batch_import():
    """批量导入 chunks 目录下的所有 JSON 文件"""
    json_files = list(Path(DATA_DIR_CHUNKS).glob("*.json"))
    
    if not json_files:
        logger.warning(f"未找到 JSON 文件: {DATA_DIR_CHUNKS}")
        return
    
    logger.info(f"找到 {len(json_files)} 个文件")
    
    for json_file in tqdm(json_files, desc="批量导入"):
        try:
            import_from_json(str(json_file))
        except Exception as e:
            logger.error(f"导入失败 {json_file}: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 导入指定文件
        json_path = sys.argv[1]
        category = sys.argv[2] if len(sys.argv) > 2 else None
        import_from_json(json_path, category)
    else:
        # 批量导入
        batch_import()

