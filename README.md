# 建筑规范知识库系统

基于 RAG (检索增强生成) 的建筑规范智能检索系统，支持多专业分类、混合检索和智能问答。

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Milvus 向量数据库
docker-compose up -d

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入模型路径和 API Key
```

### 2. 数据导入

```bash
# 步骤 1: 解析 PDF 生成 JSON
python -c "
from modules.parser import PDFParser
parser = PDFParser()
parser.parse_pdf(
    pdf_path='data/建筑与市政工程抗震通用规范.pdf',
    std_id='GB55002-2021',
    std_name='建筑与市政工程抗震通用规范',
    category='结构',
    level='国标',
    publish_year=2021
)
"

# 步骤 2: 导入到数据库
python scripts/import_data.py chunks/GB55002-2021_optimized.json 结构

# 步骤 3: 检查数据
python scripts/check_db.py
```

### 3. 启动服务

```bash
# Web UI
streamlit run app.py

# 或 API 服务
python main.py
```

访问：
- Web UI: http://localhost:8501
- API 文档: http://localhost:8000/docs

## 📁 项目结构

```
建筑规范知识库/
├── config.py                 # 系统配置
├── docker-compose.yml        # Milvus 部署
├── requirements.txt          # Python 依赖
├── .env.example             # 环境变量示例
│
├── modules/                 # 核心模块
│   ├── parser.py           # PDF 解析
│   ├── embedder.py         # 向量化模型
│   ├── database.py         # Milvus 管理
│   └── retriever.py        # 统一检索（向量+BM25+重排）
│
├── scripts/                # 工具脚本
│   ├── import_data.py      # 数据导入
│   ├── diagnose.py         # PDF 诊断
│   ├── check_db.py         # 数据库检查
│   ├── fix_json_metadata.py # 修复元数据
│   ├── reset_collection.py # 重置集合
│   ├── db_manager.py       # 数据库管理
│   └── disable_rerank.py   # 禁用重排
│
├── app.py                  # Streamlit Web UI
├── main.py                 # FastAPI 后端
│
├── data/                   # 原始 PDF
├── chunks/                 # 解析后 JSON
└── volumes/               # Milvus 数据
```

## 🎯 核心功能

### 1. 多专业分类
- 支持 7 个专业：建筑、结构、给排水、暖通、电气、造价、其他
- 每个专业独立集合，支持跨专业检索

### 2. 混合检索
- **向量检索**: BGE-Large 语义检索
- **BM25 检索**: 关键词全文检索
- **RRF 融合**: 结合向量和关键词
- **重排**: BGE-Reranker 精排（可选）

### 3. PDF 智能解析
- 条文号自动识别
- 表格提取与语义增强
- 强制性条文标记
- 完整元数据提取

## 💻 使用示例

### Python API

```python
from modules.retriever import search_standards

# 单专业检索
results = search_standards(
    query="抗震设防烈度有哪几个等级？",
    category="结构",
    top_k=10
)

# 多专业检索
results = search_standards(
    query="防火要求",
    category=None,
    top_k=10
)

# 仅强制性条文
results = search_standards(
    query="建筑高度",
    category="建筑",
    is_mandatory_only=True,
    top_k=10
)
```

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# 向量模型路径
BGE_MODEL_PATH=D:/RAG/models/bge-large-zh-v1.5

# 重排模型路径（可选）
# RERANK_MODEL_PATH=D:/RAG/models/bge-reranker-v2-m3

# 是否启用重排
ENABLE_RERANK=true

# LLM API（用于智能问答）
DEEPSEEK_API_KEY=your_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

### 元数据字段

每个文档块包含：
- `std_id`: 规范编号
- `std_name`: 规范名称
- `category`: 专业类别
- `level`: 规范等级
- `chapter_title`: 章节标题
- `clause_number`: 条文号
- `is_mandatory`: 是否强制性
- `publish_year`: 发布年份
- `page_number`: 页码
- `has_table`: 是否含表格
- `has_figure`: 是否含图片
- `status`: 状态

## 🛠️ 常用命令

```bash
# 检查数据库
python scripts/check_db.py

# 诊断 PDF
python scripts/diagnose.py data/规范.pdf

# 修复 JSON
python scripts/fix_json_metadata.py

# 批量导入
python scripts/import_data.py

# 重置集合
python scripts/reset_collection.py 结构

# 禁用重排
python scripts/disable_rerank.py

# 测试检索
python modules/retriever.py
```

## 📊 数据库管理

```bash
# 查看所有集合
python scripts/db_manager.py list

# 查看集合详情
python scripts/db_manager.py info 结构

# 删除集合
python scripts/db_manager.py delete 结构

# 清空所有数据
python scripts/db_manager.py clear
```

## 🔧 技术栈

- **向量数据库**: Milvus 2.3+
- **向量模型**: BAAI/bge-large-zh-v1.5
- **重排模型**: BAAI/bge-reranker-v2-m3
- **Web 框架**: Streamlit / FastAPI
- **PDF 解析**: pdfplumber, camelot
- **分词**: jieba
- **BM25**: rank-bm25

## 📝 注意事项

1. **向量模型**: 需要下载 BGE-Large-zh-v1.5（约 1.3GB）
2. **Milvus**: 需要至少 4GB 内存
3. **重排模型**: 可选，下载失败会自动禁用
4. **元数据**: 导入前确保字段名正确

## 📄 许可证

MIT License

