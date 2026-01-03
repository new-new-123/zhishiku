# 对话记忆机制使用说明

## 功能特性

### 1. 短期记忆（最近10轮）
- 保持最近10轮对话在内存中
- 用于上下文理解和连续对话
- 支持代词指代、追问等场景

### 2. 长期记忆（MySQL存储）
- 超过10轮的对话自动生成摘要
- 摘要由 LLM 生成，提取核心信息
- 存储在 MySQL 数据库中，支持跨会话查询

### 3. 会话隔离
- 每个会话独立的 session_id
- 不同会话的记忆互不干扰
- 支持多用户并发使用

## 快速开始

### 1. 配置 MySQL 数据库

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE building_standards CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写 MySQL 配置：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=building_standards
```

### 3. 安装依赖

```bash
pip install pymysql
```

### 4. 使用示例

```python
from modules.rag_engine import RAGEngine

# 创建会话
engine = RAGEngine(session_id="user_123")

# 第一轮对话
result1 = engine.query("建筑抗震设防烈度有哪几个等级？")
print(result1['answer'])

# 第二轮对话（可以理解上下文）
result2 = engine.query("那么8度设防的具体要求是什么？")
print(result2['answer'])

# 清空历史
engine.clear_history()
```

## 数据库表结构

```sql
CREATE TABLE conversation_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100),
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX(session_id)
);
```

## 工作流程

1. **用户提问** → 检索相关规范
2. **获取上下文** → 历史摘要 + 最近10轮对话
3. **LLM 生成回答** → 基于检索结果和对话历史
4. **保存对话** → 添加到记忆管理器
5. **自动摘要** → 超过10轮时，旧对话生成摘要存入数据库

## 测试

```bash
# 测试完整流程（包含12轮对话，会触发摘要）
python test_rag_memory.py

# 测试多会话隔离
# 修改 test_rag_memory.py 最后一行，取消注释 test_multi_session()
```

## 性能优化建议

1. **数据库索引**：已在 session_id 上建立索引
2. **摘要生成**：使用较小的 max_tokens (200) 加快生成
3. **批量查询**：如需查询多个会话的历史，可使用 IN 查询

## 扩展功能

### 1. 添加用户反馈

```python
# 在 conversation_history 表中添加字段
ALTER TABLE conversation_history ADD COLUMN user_feedback INT DEFAULT 0;
```

### 2. 导出对话历史

```python
def export_history(session_id: str) -> str:
    """导出会话历史为文本"""
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT summary, created_at FROM conversation_history WHERE session_id=%s",
            (session_id,)
        )
        results = cursor.fetchall()
    conn.close()
    return "\n".join([f"[{r[1]}] {r[0]}" for r in results])
```

### 3. 定期清理旧数据

```python
# 清理30天前的对话记录
DELETE FROM conversation_history WHERE created_at < DATE_SUB(NOW(), INTERVAL 30 DAY);
```

## 注意事项

1. **数据库连接**：确保 MySQL 服务已启动
2. **API 配额**：摘要生成会调用 LLM API，注意配额限制
3. **会话管理**：建议为每个用户生成唯一的 session_id
4. **隐私保护**：敏感对话建议加密存储

## 故障排查

### 问题1：数据库连接失败
```
解决：检查 MySQL 服务是否启动，配置是否正确
```

### 问题2：摘要生成失败
```
解决：检查 LLM API 配置，查看日志中的错误信息
摘要生成失败不影响基本功能，只是不会存储历史摘要
```

### 问题3：记忆未生效
```
解决：确认使用相同的 session_id，检查 recent_messages 是否正确添加
```

