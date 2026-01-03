"""
快速诊断脚本 - 检查 PDF 解析问题
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from modules.parser import PDFParser
from loguru import logger
import re


def diagnose_pdf(pdf_path: str):
    """诊断 PDF 文件"""
    logger.info("=" * 60)
    logger.info(f"诊断 PDF: {pdf_path}")
    logger.info("=" * 60)

    if not Path(pdf_path).exists():
        logger.error(f"文件不存在: {pdf_path}")
        return

    parser = PDFParser()

    # 1. 测试正则表达式
    logger.info("\n1. 测试条文号识别正则表达式")
    test_patterns = [
        "3.2.1 建筑高度",
        "第3.2.1条 建筑高度",
        "3.2.1条 建筑高度",
        "3-2-1 建筑高度",
        "3.2.1.1 详细规定",
        "  3.2.1  建筑高度",
        "4.1.1基本规定",
        "5.2.3  地基承载力",
    ]

    for pattern in test_patterns:
        match = parser.clause_pattern.match(pattern.strip())
        logger.info(f"  '{pattern}' -> {'✅ 匹配' if match else '❌ 不匹配'}")

    # 2. 快速扫描 PDF 内容
    logger.info("\n2. 快速扫描 PDF 内容")
    import fitz
    doc = fitz.open(pdf_path)
    logger.info(f"  总页数: {len(doc)}")

    # 扫描前 3 页找条文号
    found_clauses = []
    for page_num in range(min(3, len(doc))):
        text = doc[page_num].get_text()
        lines = text.split('\n')
        for line in lines[:20]:  # 只看前 20 行
            line = line.strip()
            if parser.clause_pattern.match(line):
                found_clauses.append(line[:50])

    if found_clauses:
        logger.info(f"  ✅ 找到条文号示例:")
        for clause in found_clauses[:5]:
            logger.info(f"    - {clause}")
    else:
        logger.warning(f"  ⚠️  前3页未找到条文号，可能需要调整正则表达式")

    doc.close()

    # 3. 解析 PDF
    logger.info("\n3. 解析 PDF 文件")
    try:
        chunks = parser.parse_pdf(
            pdf_path=pdf_path,
            std_id="TEST-2024",
            std_name="测试规范",
            category="测试",
            level="国标"
        )

        logger.info(f"✅ 解析成功，共生成 {len(chunks)} 个文档块")

        # 4. 显示前几个块
        if chunks:
            logger.info("\n4. 前 5 个文档块预览：")
            for i, chunk in enumerate(chunks[:5], 1):
                logger.info(f"\n块 {i}:")
                logger.info(f"  条文号: {chunk.metadata.get('clause_number', 'N/A')}")
                logger.info(f"  章节: {chunk.metadata.get('chapter_title', 'N/A')}")
                logger.info(f"  页码: {chunk.metadata.get('page_number', 0)}")
                logger.info(f"  强制性: {chunk.metadata.get('is_mandatory', False)}")
                logger.info(f"  内容长度: {len(chunk.text)} 字符")
                logger.info(f"  内容预览: {chunk.text[:100]}...")

        # 5. 检查元数据完整性
        logger.info("\n5. 检查元数据完整性")
        required_fields = [
            "std_id", "std_name", "category", "level", "chapter_title",
            "clause_number", "is_mandatory", "publish_year", "page_number",
            "has_table", "has_figure", "status"
        ]

        for i, chunk in enumerate(chunks[:3], 1):
            missing = [f for f in required_fields if f not in chunk.metadata]
            if missing:
                logger.warning(f"  块 {i} 缺少字段: {missing}")
            else:
                logger.info(f"  块 {i} 元数据完整 ✅")

        # 6. 统计信息
        logger.info("\n6. 统计信息")
        mandatory_count = sum(1 for c in chunks if c.metadata.get('is_mandatory'))
        table_count = sum(1 for c in chunks if c.metadata.get('has_table'))

        logger.info(f"  总块数: {len(chunks)}")
        logger.info(f"  强制性条文: {mandatory_count}")
        logger.info(f"  包含表格: {table_count}")
        logger.info(f"  平均块大小: {sum(len(c.text) for c in chunks) // len(chunks)} 字符")

    except Exception as e:
        logger.error(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # 默认测试文件
        from config import DATA_DIR
        pdf_files = list(DATA_DIR.glob("*.pdf"))
        
        if pdf_files:
            pdf_path = str(pdf_files[0])
            logger.info(f"使用第一个 PDF 文件: {pdf_path}")
        else:
            logger.error("未找到 PDF 文件")
            logger.info("使用方法: python scripts/diagnose.py <pdf_path>")
            sys.exit(1)
    
    diagnose_pdf(pdf_path)

