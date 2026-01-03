# 检索性能优化说明

## 已实施的优化

### 1. 并行检索（ThreadPoolExecutor）
- **向量检索 + BM25 检索并行执行**：两种检索方式同时进行，减少总耗时
- **多专业并行检索**：当检索多个专业时，使用线程池并行查询
- **性能提升**：理论上可减少 30-50% 的检索时间

### 2. 模型单例模式
- **Embedder 单例**：避免重复加载向量模型（模型加载耗时 1-2 秒）
- **内存优化**：多次检索共享同一个模型实例

### 3. 批量处理优化
- **重排批量计算**：reranker 使用 batch_size=32 批量计算分数
- **减少推理次数**：提升重排阶段的效率

## 进一步优化建议

### 1. 缓存机制（推荐）
```python
from functools import lru_cache
import hashlib

# 查询结果缓存
@lru_cache(maxsize=1000)
def cached_search(query_hash, top_k):
    # 缓存热门查询结果
    pass
```

### 2. 向量索引优化
- 当前使用 `IVF_FLAT`，可升级为 `HNSW` 索引（更快但占用更多内存）
- 调整 `nprobe` 参数平衡速度和准确率

### 3. 模型量化
```python
# 使用 INT8 量化加速推理
model_kwargs={'device': device, 'model_kwargs': {'torch_dtype': torch.float16}}
```

### 4. 异步 API（适用于 Web 服务）
```python
async def async_search(query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, retriever.search, query)
```

### 5. 预热优化
```python
# 启动时预热模型
retriever.search("测试查询", top_k=1)
```

## 性能基准测试

建议添加性能测试脚本：
```python
import time

queries = ["建筑抗震设防烈度", "消防设计规范", "混凝土强度等级"]
times = []

for query in queries:
    start = time.time()
    results = retriever.search(query, top_k=10)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"{query}: {elapsed:.2f}s")

print(f"平均耗时: {sum(times)/len(times):.2f}s")
```

## 配置调优

在 `config.py` 中调整：
```python
class RetrievalConfig(BaseModel):
    vector_top_k: int = 30  # 减少召回数量
    bm25_top_k: int = 20    # 减少召回数量
    rerank_top_k: int = 10  # 最终返回数量
```

## 瓶颈分析

当前可能的性能瓶颈：
1. **向量模型推理**（~100-200ms）- 已通过单例优化
2. **Milvus 检索**（~50-100ms）- 可通过索引优化
3. **重排模型推理**（~200-500ms）- 已添加批量处理
4. **BM25 计算**（~10-50ms）- 已并行化

总耗时预估：300-800ms（取决于数据量和硬件）

