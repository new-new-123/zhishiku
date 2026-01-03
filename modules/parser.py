import os
import re
import sys
import json
import pdfplumber
import pandas as pd
import camelot
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from loguru import logger
from dotenv import load_dotenv
from openai import OpenAI

parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))
from config import BASE_DIR

load_dotenv()

@dataclass
class DocumentChunk:
    """文档块数据结构"""
    text: str
    metadata: Dict
    enhanced_text: Optional[str] = None
    tables: Optional[List[Dict]] = None

class PDFParser:
    """建筑规范 PDF 深度解析器 - 2.0 优化版"""

    def __init__(self, llm_client=None):
        # 核心：极其鲁棒的条文匹配，允许数字间存在任意空格
        self.clause_pattern = re.compile(r'^\s*(?:第?\s*(\d+(?:\s*\.\s*\d+){2})\s*条?)')
        # 章节匹配
        self.chapter_pattern = re.compile(r'^\s*第?\s*([一二三四五六七八九十]+|[0-9]+)\s*[章节步术语]')
        # 表格编号匹配：用于将表格关联到对应条文
        self.table_id_pattern = re.compile(r'(?:表|附表)\s*(\d+(?:\s*\.\s*\d+){1,2})')
        self.llm_client = llm_client

    def _clean_text(self, text: str, std_id: str) -> str:
        """强化清洗逻辑"""
        if not text: return ""
        
        # 1. 初步清理特殊字符
        text = text.replace('\x00', '')
        
        # 2. 核心：修复汉字间的非法空格（OCR常见错误）
        text = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', text)
        
        # 3. 核心：修复单位符号乱码
        text = text.replace('“', '°').replace('"', '°')
        
        lines = text.split('\n')
        cleaned_lines = []
        std_id_part = std_id.split('-')[0] if '-' in std_id else std_id
        
        for line in lines:
            line = line.strip()
            if not line: continue
            # 过滤页码和页眉
            if re.match(r'^\d+$', line): continue
            if std_id_part.lower() in line.lower(): continue
            cleaned_lines.append(line)
        
        # 4. 智能段落重组：合并被 PDF 硬换行切断的句子
        final_content = []
        for line in cleaned_lines:
            if not final_content:
                final_content.append(line)
            else:
                prev = final_content[-1]
                # 如果上一行不是以结束标点结尾，且当前行以中文开头，则合并
                if not re.search(r'[。！？；：]$', prev) and re.match(r'[\u4e00-\u9fa5]', line):
                    final_content[-1] = prev + line
                else:
                    final_content.append(line)
        
        return "\n".join(final_content)

    def _extract_tables_with_camelot(self, pdf_path: str, page_num: int) -> List[Dict]:
        """提取表格并尝试捕获表格编号"""
        results = []
        try:
            import gc
            tables = camelot.read_pdf(str(pdf_path), pages=str(page_num), flavor='lattice', line_scale=40, suppress_stdout=True)
            if len(tables) == 0:
                tables = camelot.read_pdf(str(pdf_path), pages=str(page_num), flavor='stream', suppress_stdout=True)

            for table in tables:
                df = table.df
                if df.empty or len(df.columns) < 2: continue
                
                # 提取表格上方的文字作为标题，寻找表格编号
                table_context = table.parsing_report
                # 简单处理：将表格转化为 Markdown
                df.columns = df.iloc[0].str.replace('\n', '')
                df = df[1:].copy()
                df = df.map(lambda x: str(x).replace('\n', ' ') if x else "")
                
                # 尝试从表格周围文本识别编号
                table_id = None
                # 注意：这里在实际工程中可结合 pdfplumber 提取表格坐标上方的 text 进一步精修
                
                results.append({
                    "df": df,
                    "table_md": df.to_markdown(index=False),
                    "page": page_num
                })

            # 清理临时文件
            del tables
            gc.collect()
        except Exception as e:
            logger.debug(f"页码 {page_num} 表格解析跳过: {e}")
        return results

    # def _generate_table_description(self, table_info: Dict) -> str:
    #     """LLM 语义增强描述"""
    #     df = table_info['df']
    #     if self.llm_client is None:
    #         return f"\n[表格数据]:\n{table_info['table_md']}"

    #     prompt = (
    #         "你是一个专业的建筑结构工程师。请根据 Markdown 表格提取核心技术要求：\n"
    #         "1. 提取参数限值、适用范围和强制性约束。\n"
    #         "2. 严禁列表，直接输出一段连贯的专业描述文本。\n"
    #         f"表格内容：\n{table_info['table_md']}"
    #     )
        
    #     try:
    #         response = self.llm_client.chat.completions.create(
    #             model="deepseek-chat", 
    #             messages=[{"role": "system", "content": "你擅长建筑规范数据结构化解读。"},
    #                       {"role": "user", "content": prompt}],
    #             temperature=0.1,
    #             timeout=60
    #         )
    #         desc = response.choices[0].message.content.strip()
    #         return f"\n【表格语义增强】: {desc}\n【原始表格预览】:\n{table_info['table_md']}"
    #     except Exception:
    #         return f"\n【原始表格数据】:\n{table_info['table_md']}"

    def parse_pdf(self, pdf_path: str, std_id: str, std_name: str, **kwargs) -> List[DocumentChunk]:
        logger.info(f"开始解析: {std_name}")
        chunks = []

        current_clause = "前言"
        current_chapter = "未分类"
        current_content = []
        current_page_num = 1
        current_tables = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_num = page.page_number
                page_text = self._clean_text(page.extract_text(), std_id)
                if not page_text: continue

                # 处理表格
                table_infos = self._extract_tables_with_camelot(pdf_path, page_num)
                # table_additions = [self._generate_table_description(t) for t in table_infos]

                lines = page_text.split('\n')
                for line in lines:
                    clean_line = line.strip()

                    # 1. 章节识别
                    if self.chapter_pattern.match(clean_line):
                        current_chapter = clean_line
                        continue

                    # 2. 条文识别 (采用你强调的 \s* 匹配)
                    clause_match = self.clause_pattern.match(clean_line)
                    if clause_match:
                        if current_content:
                            chunks.append(self._create_chunk(
                                current_clause, current_chapter, current_content,
                                std_id, std_name, page_num=current_page_num,
                                tables=current_tables, **kwargs
                            ))

                        # 标准化条文号，去除空格
                        current_clause = re.sub(r'\s+', '', clause_match.group(1))
                        current_content = [clean_line]
                        current_page_num = page_num
                        current_tables = []
                    else:
                        current_content.append(clean_line)

                # 将本页表格挂载到当前正在处理的条文中
                if table_infos:
                    current_tables.extend(table_infos)
                # if table_additions:
                #     current_content.extend(table_additions)

        # 闭合最后一个块
        if current_content:
            chunks.append(self._create_chunk(current_clause, current_chapter, current_content, std_id, std_name, page_num=current_page_num, tables=current_tables, **kwargs))

        self.save_to_json(chunks, std_id, std_name)
        return chunks

    def _create_chunk(self, clause_number, chapter_title, content_list, std_id, std_name, tables=None, **kwargs):
        # 区分原文和增强文本
        raw_text = "\n".join([c for c in content_list if "【" not in c])
        enhanced_text = "\n".join(content_list)

        # 强条判定依据：内容含关键词
        is_mandatory = any(kw in raw_text for kw in ["必须", "严禁", "不得", "应为"])

        # 提取表格数据
        table_data = []
        if tables:
            for t in tables:
                table_data.append({
                    "page": t.get("page"),
                    "markdown": t.get("table_md"),
                    "data": t.get("df").to_dict(orient="records") if "df" in t else []
                })

        metadata = {
            "std_id": std_id,
            "std_name": std_name,
            "chapter_title": chapter_title,
            "clause_number": clause_number,
            "is_mandatory": is_mandatory,
            "page_number": kwargs.get("page_num", 0),
            "category": kwargs.get("category", "结构"),
            "level": kwargs.get("level", "国标"),
            "publish_year": kwargs.get("publish_year", 2024),
            "has_table": bool(tables),
            "has_figure": False,
            "status": "active"
        }

        return DocumentChunk(text=raw_text, metadata=metadata, enhanced_text=enhanced_text, tables=table_data if table_data else None)

    def save_to_json(self, chunks: List[DocumentChunk], std_id: str, std_name: str = ""):
        output_dir = BASE_DIR / "chunks"
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{std_id}_{std_name}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in chunks], f, ensure_ascii=False, indent=2)
        logger.info(f"优化版数据已保存至: {output_path}")

if __name__ == "__main__":
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url=os.getenv("DEEPSEEK_BASE_URL"))
    parser = PDFParser(llm_client=client)
    
    # 请确保路径正确
    parser.parse_pdf(
        pdf_path="D:\zhishiku\jianzhuzhishi\data\建筑与市政工程抗震通用规范.pdf",
        std_id="GB55002-2021",
        std_name="建筑与市政工程抗震通用规范",
        category="结构"
    )