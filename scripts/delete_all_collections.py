"""
删除 Milvus 数据库中的所有集合
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import connections, utility
from loguru import logger
from config import milvus_config

def delete_all_collections():
    """删除所有集合"""
    # 连接 Milvus
    connections.connect(
        alias="default",
        host=milvus_config.host,
        port=milvus_config.port
    )
    logger.info(f"已连接到 Milvus: {milvus_config.host}:{milvus_config.port}")
    
    # 获取所有集合
    collections = utility.list_collections()
    
    if not collections:
        logger.info("没有找到任何集合")
        return
    
    logger.warning(f"找到 {len(collections)} 个集合:")
    for col in collections:
        logger.warning(f"  - {col}")
    
    # 确认删除
    confirm = input("\n确认删除所有集合? (yes/no): ")
    
    if confirm.lower() != 'yes':
        logger.info("已取消删除")
        return
    
    # 删除所有集合
    for collection_name in collections:
        try:
            utility.drop_collection(collection_name)
            logger.info(f"✓ 已删除: {collection_name}")
        except Exception as e:
            logger.error(f"✗ 删除失败 {collection_name}: {e}")
    
    logger.info("\n所有集合已删除完成")

if __name__ == "__main__":
    delete_all_collections()

