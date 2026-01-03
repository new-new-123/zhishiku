"""
RAG 问答测试脚本
"""
from modules.rag_engine import RAGEngine
from loguru import logger
import uuid


def test_rag_with_memory():
    """测试带记忆的 RAG 问答"""
    
    # 创建会话
    session_id = str(uuid.uuid4())[:8]
    engine = RAGEngine(session_id=session_id)
    
    logger.info(f"开始测试会话: {session_id}")
    
    # 测试问题列表
    questions = [
        "建筑抗震设防烈度有哪几个等级？",
        "那么8度设防的具体要求是什么？",  # 测试上下文理解
        "混凝土强度等级如何划分？",
        "C30混凝土的抗压强度是多少？",  # 测试上下文理解
        "建筑防火分区的面积限制是多少？",
        "高层建筑的防火要求有哪些？",
        "住宅建筑的层高标准是多少？",
        "无障碍设计有哪些基本要求？",
        "消防车道的宽度要求是多少？",
        "建筑物的耐火等级如何划分？",
        "钢结构防火涂料的厚度要求？",  # 第11个问题，会触发摘要
        "地下室防水等级如何确定？",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"问题 {i}: {question}")
        print(f"{'='*80}")
        
        result = engine.query(
            question=question,
            category="结构" if i <= 4 else None,  # 前4个问题限定结构专业
            top_k=3
        )
        
        print(f"\n回答:\n{result['answer']}")
        
        print(f"\n引用规范:")
        for j, ref in enumerate(result['references'], 1):
            print(f"  [{j}] {ref['std_name']} ({ref['std_id']})")
            print(f"      条文号: {ref['clause_number']}")
            print(f"      强制性: {'是' if ref['is_mandatory'] else '否'}")
            print(f"      相关度: {ref['score']:.4f}")
        
        if i == 11:
            print("\n[提示] 已超过10轮对话，历史对话已生成摘要并存储到数据库")
    
    # 测试清空历史
    print(f"\n{'='*80}")
    print("测试清空历史")
    engine.clear_history()


def test_multi_session():
    """测试多会话隔离"""
    logger.info("测试多会话隔离")
    
    # 会话1
    engine1 = RAGEngine(session_id="session_1")
    result1 = engine1.query("建筑抗震设防烈度有哪几个等级？", category="结构")
    print(f"\n会话1回答: {result1['answer'][:100]}...")
    
    # 会话2
    engine2 = RAGEngine(session_id="session_2")
    result2 = engine2.query("混凝土强度等级如何划分？", category="结构")
    print(f"\n会话2回答: {result2['answer'][:100]}...")
    
    # 验证会话隔离
    print("\n验证会话隔离:")
    print(f"会话1记忆数量: {len(engine1.memory.recent_messages)}")
    print(f"会话2记忆数量: {len(engine2.memory.recent_messages)}")


if __name__ == "__main__":
    # 测试1: 带记忆的长对话
    test_rag_with_memory()
    
    # 测试2: 多会话隔离
    # test_multi_session()

