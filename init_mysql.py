"""
快速初始化 MySQL 数据库
"""
import pymysql
from loguru import logger

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "n13835951712",  # 你的密码
    "charset": "utf8mb4"
}

def init_database():
    """初始化数据库和表"""
    try:
        # 1. 连接 MySQL（不指定数据库）
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 2. 创建数据库
        cursor.execute("CREATE DATABASE IF NOT EXISTS building_standards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info("✓ 数据库 building_standards 已创建")
        
        # 3. 使用数据库
        cursor.execute("USE building_standards")
        
        # 4. 创建对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(100),
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX(session_id)
            )
        """)
        logger.info("✓ 表 conversation_history 已创建")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✓ 数据库初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}")
        return False

if __name__ == "__main__":
    init_database()

