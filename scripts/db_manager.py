"""
数据库管理工具
提供数据库维护功能
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from modules.database import MilvusManager
from loguru import logger
import argparse


def show_stats():
    """显示数据库统计信息"""
    db = MilvusManager()
    stats = db.get_stats()
    
    logger.info("=" * 60)
    logger.info("数据库统计信息")
    logger.info("=" * 60)
    logger.info(f"集合名称: {stats['collection_name']}")
    logger.info(f"总条目数: {stats['total_entities']}")
    logger.info("=" * 60)


def clear_database():
    """清空数据库"""
    logger.warning("⚠️  警告：此操作将删除所有数据！")
    confirm = input("确认清空数据库？(yes/no): ")
    
    if confirm.lower() == "yes":
        db = MilvusManager()
        db.create_collection(drop_existing=True)
        logger.info("✅ 数据库已清空")
    else:
        logger.info("已取消操作")


def backup_database():
    """备份数据库（导出为 JSON）"""
    logger.info("备份功能开发中...")
    # TODO: 实现数据导出功能


def main():
    parser = argparse.ArgumentParser(description="数据库管理工具")
    parser.add_argument(
        "action",
        choices=["stats", "clear", "backup"],
        help="操作类型: stats(统计), clear(清空), backup(备份)"
    )
    
    args = parser.parse_args()
    
    if args.action == "stats":
        show_stats()
    elif args.action == "clear":
        clear_database()
    elif args.action == "backup":
        backup_database()


if __name__ == "__main__":
    main()

