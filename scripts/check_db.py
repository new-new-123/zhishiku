"""
快速检查数据库状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.database import MilvusManager, get_all_collections_stats
from config import CATEGORIES
from loguru import logger

def check_database():
    """检查数据库状态"""
    logger.info("=" * 60)
    logger.info("检查 Milvus 数据库状态")
    logger.info("=" * 60)
    
    # 检查所有专业
    from pymilvus import utility

    for category in CATEGORIES.keys():
        logger.info(f"\n检查专业: {category}")
        try:
            manager = MilvusManager(category=category, auto_create=False)
            collection_name = manager.collection_name

            # 检查集合是否存在
            if not utility.has_collection(collection_name):
                logger.warning(f"  ✗ 集合不存在: {collection_name}")
            else:
                # 加载集合
                from pymilvus import Collection
                collection = Collection(collection_name)
                collection.load()
                count = collection.num_entities

                logger.info(f"  ✓ 集合存在: {collection_name}")
                logger.info(f"  ✓ 数据量: {count}")

                if count == 0:
                    logger.warning(f"  ⚠️  集合为空，需要导入数据")

        except Exception as e:
            logger.error(f"  ✗ 检查失败: {e}")
    
    # 统计信息
    logger.info("\n" + "=" * 60)
    logger.info("总体统计")
    logger.info("=" * 60)
    
    try:
        stats = get_all_collections_stats()
        if stats:
            for category, info in stats.items():
                logger.info(f"{category}: {info['total_entities']} 条")
        else:
            logger.warning("没有找到任何数据")
            logger.info("\n请先导入数据:")
            logger.info("  python scripts/import_data.py chunks/GB55002-2021_optimized.json 结构")
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")

if __name__ == "__main__":
    check_database()

