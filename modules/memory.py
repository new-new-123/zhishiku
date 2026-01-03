"""
对话记忆管理 - 保持10轮对话，超出部分生成摘要存入MySQL
"""
from typing import List, Dict, Optional
from datetime import datetime
import pymysql
from loguru import logger
from openai import OpenAI

from config import llm_config


class ConversationMemory:
    """对话记忆管理器（单例模式）"""

    _llm_client = None  # 共享 LLM 客户端

    def __init__(self, session_id: str, db_config: Dict):
        self.session_id = session_id
        self.db_config = db_config
        self.recent_messages: List[Dict] = []  # 最近10轮
        self.max_recent = 10

        # 共享 LLM 客户端
        if ConversationMemory._llm_client is None:
            ConversationMemory._llm_client = OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
        self.llm_client = ConversationMemory._llm_client

        self._init_db()
        self._load_session()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(100),
                        summary TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX(session_id)
                    )
                """)
            conn.commit()
        finally:
            conn.close()
    
    def _load_session(self):
        """加载会话历史摘要"""
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT summary FROM conversation_history WHERE session_id=%s ORDER BY created_at DESC LIMIT 1",
                    (self.session_id,)
                )
                result = cursor.fetchone()
                if result:
                    logger.info(f"加载历史摘要: {result['summary'][:50]}...")
        finally:
            conn.close()
    
    def add_message(self, role: str, content: str):
        """添加消息"""
        self.recent_messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 超过10轮，生成摘要并存储
        if len(self.recent_messages) > self.max_recent * 2:
            self._summarize_and_store()
    
    def _summarize_and_store(self):
        """生成摘要并存储到数据库"""
        old_messages = self.recent_messages[:10]
        self.recent_messages = self.recent_messages[10:]
        
        # 生成摘要
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
        prompt = f"请用2-3句话总结以下对话的核心内容：\n\n{conversation_text}"
        
        try:
            response = self.llm_client.chat.completions.create(
                model=llm_config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            summary = response.choices[0].message.content
            
            # 存入数据库
            conn = pymysql.connect(**self.db_config)
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO conversation_history (session_id, summary) VALUES (%s, %s)",
                        (self.session_id, summary)
                    )
                conn.commit()
                logger.info(f"对话摘要已存储: {summary[:50]}...")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
    
    def get_context(self) -> List[Dict]:
        """获取对话上下文（用于LLM）"""
        context = []
        
        # 添加历史摘要
        conn = pymysql.connect(**self.db_config)
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(
                    "SELECT summary FROM conversation_history WHERE session_id=%s ORDER BY created_at",
                    (self.session_id,)
                )
                summaries = cursor.fetchall()
                if summaries:
                    combined_summary = "\n".join([s['summary'] for s in summaries])
                    context.append({
                        "role": "system",
                        "content": f"历史对话摘要：\n{combined_summary}"
                    })
        finally:
            conn.close()
        
        # 添加最近10轮对话
        context.extend([{"role": m["role"], "content": m["content"]} for m in self.recent_messages])
        return context
    
    def clear(self):
        """清空当前会话"""
        self.recent_messages = []
        logger.info(f"会话 {self.session_id} 已清空")


# 全局会话管理
_sessions: Dict[str, ConversationMemory] = {}

def get_memory(session_id: str, db_config: Dict) -> ConversationMemory:
    """获取或创建会话记忆"""
    if session_id not in _sessions:
        _sessions[session_id] = ConversationMemory(session_id, db_config)
    return _sessions[session_id]

