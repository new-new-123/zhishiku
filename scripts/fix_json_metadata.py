"""
修复 JSON 文件中的元数据字段名
将旧字段名转换为新字段名，并补充缺失字段
"""
import sys
import json
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_json_file(json_path: str):
    """修复单个 JSON 文件"""
    logger.info(f"处理文件: {json_path}")
    
    # 读取文件
    with open(json_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    if not chunks:
        logger.warning(f"文件为空: {json_path}")
        return
    
    # 修复每个 chunk 的 metadata
    fixed_count = 0
    for chunk in chunks:
        metadata = chunk["metadata"]
        modified = False
        
        # 1. 字段名转换
        if "chapter" in metadata and "chapter_title" not in metadata:
            metadata["chapter_title"] = metadata.pop("chapter")
            modified = True
        
        if "clause" in metadata and "clause_number" not in metadata:
            metadata["clause_number"] = metadata.pop("clause")
            modified = True
        
        # 2. 补充缺失字段
        defaults = {
            "level": "国标",
            "publish_year": 2024,
            "has_table": bool(chunk.get("tables")),
            "has_figure": False,
            "status": "active"
        }
        
        for key, default_value in defaults.items():
            if key not in metadata:
                metadata[key] = default_value
                modified = True
        
        # 3. 确保必需字段存在
        required_fields = {
            "std_id": "UNKNOWN",
            "std_name": "未知规范",
            "category": "其他",
            "chapter_title": "",
            "clause_number": "",
            "is_mandatory": False,
            "page_number": 0
        }
        
        for key, default_value in required_fields.items():
            if key not in metadata:
                metadata[key] = default_value
                modified = True
        
        if modified:
            fixed_count += 1
    
    # 保存修复后的文件
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✓ 修复完成: {fixed_count}/{len(chunks)} 个块被修改")

def fix_all_json_files():
    """批量修复所有 JSON 文件"""
    chunks_dir = Path("chunks")
    
    if not chunks_dir.exists():
        logger.error(f"目录不存在: {chunks_dir}")
        return
    
    json_files = list(chunks_dir.glob("*.json"))
    
    if not json_files:
        logger.warning(f"未找到 JSON 文件: {chunks_dir}")
        return
    
    logger.info(f"找到 {len(json_files)} 个文件")
    
    for json_file in json_files:
        try:
            fix_json_file(str(json_file))
        except Exception as e:
            logger.error(f"处理失败 {json_file}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 修复指定文件
        fix_json_file(sys.argv[1])
    else:
        # 批量修复
        fix_all_json_files()

