"""
Web UI 界面 - 基于 Streamlit (多专业分类架构)
提供友好的交互界面
"""
import sys
from pathlib import Path
import streamlit as st

sys.path.append(str(Path(__file__).parent))

from modules.retriever import search_standards
from modules.rag_engine import RAGEngine
from modules.database import get_all_collections_stats
from config import CATEGORIES

# 页面配置
st.set_page_config(
    page_title="建筑规范知识库",
    page_icon="🏗️",
    layout="wide"
)

# 标题
st.title("🏗️ 建筑规范知识库系统 (多专业分类)")
st.markdown("---")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 系统设置")

    # 数据库统计
    try:
        stats = get_all_collections_stats()
        st.subheader("📊 数据统计")
        for category, info in stats.items():
            st.metric(f"{category}", info["total_entities"])
    except:
        st.warning("⚠️ 无法连接到 Milvus")

    st.markdown("---")

    # 功能选择
    page = st.radio(
        "选择功能",
        ["🔍 检索规范", "💬 智能问答"]
    )

# 主界面
if page == "🔍 检索规范":
    st.header("🔍 规范检索")

    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_input("输入查询内容", placeholder="例如：高层建筑防火墙的耐火极限要求")

    with col2:
        category = st.selectbox(
            "专业类别",
            ["全部"] + list(CATEGORIES.keys())
        )

    col3, col4 = st.columns([1, 1])

    with col3:
        is_mandatory = st.checkbox("仅显示强制性条文")

    with col4:
        top_k = st.slider("返回结果数", 5, 20, 10)

    if st.button("🔍 开始检索", type="primary"):
        if not query:
            st.warning("请输入查询内容")
        else:
            with st.spinner("正在检索..."):
                try:
                    results = search_standards(
                        query=query,
                        category=None if category == "全部" else category,
                        is_mandatory_only=is_mandatory,
                        top_k=top_k
                    )

                    if not results:
                        st.info("未找到相关结果")
                    else:
                        st.success(f"找到 {len(results)} 条相关结果")

                        for i, result in enumerate(results, 1):
                            with st.expander(
                                f"**{i}. {result['metadata']['std_name']}** - {result['metadata']['clause_number']}"
                            ):
                                col_a, col_b = st.columns([3, 1])

                                with col_a:
                                    st.markdown(f"**规范编号**: {result['metadata']['std_id']}")
                                    st.markdown(f"**专业**: {result['metadata']['category']}")
                                    st.markdown(f"**章节**: {result['metadata']['chapter_title']}")
                                    st.markdown(f"**页码**: {result['metadata']['page_number']}")

                                with col_b:
                                    if result['metadata']['is_mandatory']:
                                        st.error("🔴 强制性条文")
                                    else:
                                        st.info("⚪ 一般条文")
                                    
                                    score = result.get('score', 0)
                                    st.metric("相关度", f"{score:.4f}")
                                
                                st.markdown("---")
                                st.markdown(f"**条文内容**:\n\n{result['text']}")
                
                except Exception as e:
                    st.error(f"检索失败: {e}")

elif page == "💬 智能问答":
    st.header("💬 智能问答")

    st.info("💡 提示：基于检索到的规范条文，AI 将为您生成专业的回答")

    # 初始化 session_state
    if "session_id" not in st.session_state:
        st.session_state.session_id = "default"
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    question = st.text_area(
        "请输入您的问题",
        placeholder="例如：女儿墙高度有什么要求？",
        height=100
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        category = st.selectbox(
            "专业类别（可选）",
            ["全部"] + list(CATEGORIES.keys()),
            key="qa_category"
        )

    with col2:
        is_mandatory = st.checkbox("优先检索强制性条文", key="qa_mandatory")

    with col3:
        if st.button("🗑️ 清空历史"):
            st.session_state.chat_history = []
            st.success("对话历史已清空")

    if st.button("💬 获取回答", type="primary"):
        if not question:
            st.warning("请输入问题")
        else:
            with st.spinner("正在思考..."):
                try:
                    rag_engine = RAGEngine(session_id=st.session_state.session_id)
                    result = rag_engine.query(
                        question=question,
                        category=None if category == "全部" else category,
                        is_mandatory_only=is_mandatory
                    )

                    # 显示回答
                    st.markdown("### 📝 回答")
                    st.markdown(result["answer"])

                    # 显示来源
                    st.markdown("---")
                    st.markdown("### 📚 参考来源")

                    for i, ref in enumerate(result["references"], 1):
                        with st.expander(f"{i}. {ref['std_name']} - {ref['clause_number']}"):
                            st.markdown(f"**规范编号**: {ref['std_id']}")
                            st.markdown(f"**专业**: {ref.get('category', 'N/A')}")
                            if ref['is_mandatory']:
                                st.error("🔴 强制性条文")
                            st.markdown(f"\n{ref['text']}")

                except Exception as e:
                    st.error(f"问答失败: {e}")

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        建筑规范知识库系统 v2.0 | 基于 RAG 技术 | Powered by BGE-M3 + Milvus + 对话记忆
    </div>
    """,
    unsafe_allow_html=True
)

