"""
重置 Milvus 集合
删除旧集合并重新创建
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from pymilvus import connections, utility
from modules.database import MilvusManager
from config import milvus_config
from loguru import logger


def reset_collection():
    """删除并重新创建集合"""
    # 连接 Milvus
    connections.connect(
        alias="default",
        host=milvus_config.host,
        port=milvus_config.port
    )
    
    collection_name = milvus_config.collection_name
    
    # 检查集合是否存在
    if utility.has_collection(collection_name):
        logger.warning(f"发现旧集合: {collection_name}")
        logger.warning("准备删除...")
        
        # 删除集合
        utility.drop_collection(collection_name)
        logger.info(f"✅ 已删除旧集合: {collection_name}")
    else:
        logger.info(f"集合不存在: {collection_name}")
    
    # 重新创建集合
    logger.info("正在创建新集合...")
    db = MilvusManager(auto_create=False)
    db.create_collection(drop_existing=False)
    
    logger.info("✅ 集合重置完成！")
    logger.info(f"集合名称: {collection_name}")
    logger.info("现在可以运行灌库脚本了")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Milvus 集合重置工具")
    logger.info("=" * 60)
    logger.warning("⚠️  此操作将删除所有现有数据！")
    logger.info("\n按 Enter 继续，Ctrl+C 取消...")
    
    try:
        input()
    except KeyboardInterrupt:
        logger.info("\n已取消")
        sys.exit(0)
    
    reset_collection()

