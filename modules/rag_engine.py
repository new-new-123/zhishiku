"""
RAG 问答引擎 - 集成检索和对话记忆
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))

from modules.retriever import search_standards
from modules.memory import get_memory
from config import llm_config, mysql_config


class RAGEngine:
    """RAG 问答引擎（单例模式）"""

    _instances = {}  # 按 session_id 缓存实例
    _llm_client = None  # 共享 LLM 客户端

    def __new__(cls, session_id: str = "guoteng"):
        if session_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[session_id] = instance
        return cls._instances[session_id]

    def __init__(self, session_id: str = "guoteng"):
        if hasattr(self, '_initialized'):
            return

        self.session_id = session_id

        # 共享 LLM 客户端
        if RAGEngine._llm_client is None:
            RAGEngine._llm_client = OpenAI(api_key=llm_config.api_key, base_url=llm_config.base_url)
        self.llm_client = RAGEngine._llm_client

        # 初始化记忆管理（可选）
        try:
            db_config = {
                "host": mysql_config.host,
                "port": mysql_config.port,
                "user": mysql_config.user,
                "password": mysql_config.password,
                "database": mysql_config.database,
                "charset": mysql_config.charset
            }
            self.memory = get_memory(session_id, db_config)
            logger.info(f"✓ 对话记忆已启用 (session: {session_id})")
        except Exception as e:
            logger.warning(f"✗ 对话记忆初始化失败，将使用无记忆模式: {e}")
            self.memory = None
        self._initialized = True
    
    def query(
        self,
        question: str,
        category: Optional[str] = None,
        is_mandatory_only: bool = False,
        top_k: int = 5
    ) -> Dict:
        """
        RAG 问答

        Args:
            question: 用户问题
            category: 专业类别（None 表示全专业检索）
            is_mandatory_only: 是否仅检索强制性条文
            top_k: 返回结果数量

        Returns:
            包含答案和引用的字典
        """
        logger.info(f"[{self.session_id}] 用户提问: {question}")

        # 1. 检索相关规范
        retrieved_docs = search_standards(
            query=question,
            category=category,
            is_mandatory_only=is_mandatory_only,
            top_k=top_k
        )

        if not retrieved_docs:
            return {
                "answer": "抱歉，未找到相关规范内容。",
                "references": [],
                "session_id": self.session_id
            }

        # 2. 构建上下文
        context = self._build_context(retrieved_docs)

        # 3. 获取对话历史（如果启用）
        conversation_history = []
        if self.memory:
            try:
                conversation_history = self.memory.get_context()
            except Exception as e:
                logger.warning(f"获取对话历史失败: {e}")

        # 4. 生成回答
        answer = self._generate_answer(question, context, conversation_history)

        # 5. 保存对话（如果启用）
        if self.memory:
            try:
                self.memory.add_message("user", question)
                self.memory.add_message("assistant", answer)
            except Exception as e:
                logger.warning(f"保存对话失败: {e}")

        # 6. 格式化引用
        references = self._format_references(retrieved_docs)

        return {
            "answer": answer,
            "references": references,
            "session_id": self.session_id
        }
    
    def _build_context(self, docs: List[Dict]) -> str:
        """构建检索上下文"""
        context_parts = []
        for i, doc in enumerate(docs, 1):
            metadata = doc.get("metadata", {})
            text = doc.get("text", "")
            
            context_parts.append(
                f"[文档{i}] {metadata.get('std_name', '')} ({metadata.get('std_id', '')})\n"
                f"条文号: {metadata.get('clause_number', '')}\n"
                f"内容: {text}\n"
            )
        
        return "\n".join(context_parts)
    
    def _generate_answer(self, question: str, context: str, history: List[Dict]) -> str:
        """生成回答"""
        system_prompt = """你是一个专业的建筑规范问答助手。请基于提供的规范文档回答用户问题。

要求：
1. 回答必须基于提供的规范内容，不要编造信息
2. 引用具体的规范编号和条文号
3. 如果规范内容不足以回答问题，请明确说明
4. 回答要专业、准确、简洁
5. 对于强制性条文，请特别标注"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话（最多保留系统提示 + 历史摘要 + 最近对话）
        messages.extend(history)
        
        # 添加当前问题和上下文
        user_message = f"参考规范：\n{context}\n\n用户问题：{question}"
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.llm_client.chat.completions.create(
                model=llm_config.model_name,
                messages=messages,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"抱歉，生成回答时出错：{str(e)}"
    
    def _format_references(self, docs: List[Dict]) -> List[Dict]:
        """格式化引用"""
        references = []
        for doc in docs:
            metadata = doc.get("metadata", {})
            references.append({
                "std_id": metadata.get("std_id"),
                "std_name": metadata.get("std_name"),
                "clause_number": metadata.get("clause_number"),
                "chapter_title": metadata.get("chapter_title"),
                "is_mandatory": metadata.get("is_mandatory", False),
                "text": doc.get("text", "")[:500] + "...",
                "score": doc.get("rerank_score") or doc.get("rrf_score") or doc.get("score", 0)
            })
        return references
    
    def clear_history(self):
        """清空对话历史"""
        if self.memory:
            try:
                self.memory.clear()
                logger.info(f"会话 {self.session_id} 历史已清空")
            except Exception as e:
                logger.warning(f"清空历史失败: {e}")
        else:
            logger.warning("对话记忆未启用，无需清空")

