# 建筑规范知识库 - 对话记忆机制

## 📋 更新内容

### 新增功能
1. **对话记忆管理** (`modules/memory.py`)
   - 保持最近10轮对话在内存
   - 超过10轮自动生成摘要存入MySQL
   - 支持多会话隔离

2. **RAG 问答引擎** (`modules/rag_engine.py`)
   - 集成检索和对话记忆
   - 支持上下文理解和连续对话
   - 自动引用规范条文

3. **性能优化** (`modules/retriever.py`)
   - 并行检索（向量 + BM25）
   - 多专业并行查询
   - 模型单例模式
   - 批量重排处理

### 配置文件更新
- `config.py`: 新增 MySQLConfig
- `.env.example`: 新增 MySQL 配置项
- `requirements.txt`: 新增 pymysql 依赖

## 🚀 快速开始

### 1. 安装新依赖
```bash
pip install pymysql
```

### 2. 配置 MySQL
```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE building_standards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 配置环境变量
在 `.env` 文件中添加：
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=building_standards
```

### 4. 运行测试
```bash
# 测试对话记忆（12轮对话，会触发摘要）
python test_rag_memory.py
```

## 📖 使用示例

```python
from modules.rag_engine import RAGEngine

# 创建会话
engine = RAGEngine(session_id="user_123")

# 第一轮对话
result = engine.query("建筑抗震设防烈度有哪几个等级？", category="结构")
print(result['answer'])
print(result['references'])

# 第二轮对话（理解上下文）
result = engine.query("那么8度设防的具体要求是什么？")
print(result['answer'])

# 清空历史
engine.clear_history()
```

## 🔧 核心改进

### 1. 对话记忆机制
- **短期记忆**：最近10轮保存在内存
- **长期记忆**：超过10轮生成摘要存MySQL
- **会话隔离**：每个用户独立的 session_id

### 2. 性能优化
- **并行检索**：向量和BM25同时执行，提速30-50%
- **多专业并行**：使用线程池并行查询多个专业
- **模型单例**：避免重复加载模型（节省1-2秒）
- **批量重排**：batch_size=32 批量计算分数

### 3. 检索优化
- BM25 结果现在包含完整的 metadata
- 修复了 KeyError: 'metadata' 的问题

## 📁 新增文件

```
modules/
├── memory.py           # 对话记忆管理
├── rag_engine.py       # RAG 问答引擎
└── retriever.py        # 检索模块（已优化）

test_rag_memory.py      # 测试脚本
MEMORY_USAGE.md         # 记忆机制使用文档
OPTIMIZATION_NOTES.md   # 性能优化说明
```

## 🗄️ 数据库表结构

```sql
CREATE TABLE conversation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100),
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX(session_id)
);
```

## 📊 性能基准

- **向量模型推理**: ~100-200ms（已优化为单例）
- **Milvus 检索**: ~50-100ms
- **重排模型推理**: ~200-500ms（已批量处理）
- **BM25 计算**: ~10-50ms（已并行化）
- **总耗时**: 300-800ms（取决于数据量和硬件）

## 🔍 故障排查

### 问题1：数据库连接失败
```
解决：检查 MySQL 服务是否启动，配置是否正确
```

### 问题2：摘要生成失败
```
解决：检查 LLM API 配置，查看日志
摘要生成失败不影响基本功能
```

### 问题3：检索速度慢
```
解决：
1. 减少 top_k 参数
2. 使用 GPU 加速
3. 调整 Milvus 索引参数
```

## 📚 相关文档

- [MEMORY_USAGE.md](MEMORY_USAGE.md) - 对话记忆详细使用说明
- [OPTIMIZATION_NOTES.md](OPTIMIZATION_NOTES.md) - 性能优化详细说明
- [README.md](README.md) - 项目总体说明

## 🎯 下一步计划

- [ ] 添加 Web UI（Streamlit/FastAPI）
- [ ] 实现查询缓存机制
- [ ] 支持多模态（图片、表格）
- [ ] 添加用户反馈机制
- [ ] 实现向量索引优化（HNSW）

